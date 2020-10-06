#!/usr/bin/env python
import json
import os
import typing

import yaml

from sonic_package_manager import constraint, common
from sonic_package_manager import package
from sonic_package_manager.logger import get_logger


class Repository:
    """ Repository entry. """

    def __init__(self, name: str, metadata: typing.Dict):
        """ Create an instance of Repository.

        Args:
            name: Repository name.
            metadata: Database information about this repository.
        """

        self._name = name
        self._metadata = metadata

    def get_name(self) -> str:
        """ Returns package name.

        Returns:
            Repository name string.
        """

        return self._name

    def get_repository(self) -> str:
        """ Returns repository url.

        Returns:
            Repository url string.
        """

        return self._metadata['repository']

    def get_default_version(self) -> typing.Optional[constraint.VersionConstraint]:
        """ Returns repository default installation candidate.

        Returns:
            Default repository installation candidate.
        """

        default_version_string = self._metadata.get('default-version')
        if default_version_string is None:
            return default_version_string
        return constraint.parse_version_constraint(default_version_string)

    def get_description(self) -> str:
        """ Returns repository description string.

        Returns:
            Repository description string. May return None.
            if package entry does not have description field.
        """

        return self._metadata.get('description')

    def get_installed_version(self) -> typing.Optional[constraint.Version]:
        """ Returns an installed version as string.

        Returns:
            Installed package version.
        """

        try:
            ver = self._metadata['version']
        except KeyError:
            return None

        return constraint.Version.parse(ver)

    def get_status(self) -> str:
        """ Tells the repository status - Installed/Not Installed/Built-In.

        Returns:
            Repository installation status string.
        """

        if self.is_builtin():
            return "Built-In"
        elif self.is_installed():
            return "Installed"
        else:
            return "Not Installed"

    def get_metadata(self) -> typing.Dict:
        """ Returns repository metadata it was initialized with.

        Returns:
            repository metadata.
        """

        return self._metadata

    def is_builtin(self) -> bool:
        """ Tells if a repository is essential.

        Returns:
            True if the repository is essential, False otherwise.
        """

        return self._metadata.get("essential", False)

    def is_installed(self) -> bool:
        """ Tells if a repository is installed.

        Returns:
            True if the repository is installed, False otherwise.
        """

        return self._metadata.get('status') == 'installed'

    def get_package(self) -> package.Package:
        """ Return an instance of Package.

        Returns:
            Package object corresponding to this package entry.

        Raises:
            PackageManagerError: If the package manifest is not found.
        """

        manifest_content = self.get_manifest()
        return package.Package(manifest_content)

    def update_installation_status(self, status: str,
                                   version: typing.Optional[constraint.Version] = None):
        """ Updates status of the Repository.

        Args:
            status: 'installed' or 'not-installed' string.
            version: version of installed package.
        """

        self._metadata['status'] = status
        self._metadata['version'] = str(version)

    def get_manifest(self) -> typing.Dict:
        """ Reads the content of package manifest. If no manifest file
        found in Docker Image returns a default one.

        Returns:
            manifest content as a dictionary.
        """

        name = self.get_name()
        package_path = common.get_package_metadata_folder(name)

        manifests_locations = [
            os.path.join(package_path, 'manifest.json'),
            os.path.join(package_path, 'manifest.yml'),
            os.path.join(package_path, 'manifest.yaml'),
        ]

        for manifest in manifests_locations:
            try:
                with open(manifest) as stream:
                    if manifest.endswith('.json'):
                        return json.load(stream)
                    else:
                        return yaml.safe_load(stream)
            except IOError:
                continue

        get_logger().warning(f'Failed to locate manifest file for {name}, using default manifest')

        # Return a default one, which service name is the package name
        # and host-only service flag is set. If there is no manifest it
        # is assumed we are installing an arbitrary Docker image that can
        # run on Linux host so it most probably has nothing to do with ASIC.
        return {
            'version': '1.0.0',
            'service': {
                'name': f'{name}',
                'host-service': True,
                'asic-service': False,
            }
        }

    def __lt__(self, other):
        return self.get_name() < other.get_name()
