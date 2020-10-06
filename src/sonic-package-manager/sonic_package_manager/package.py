#!/usr/bin/env python

import collections
import json
import os
import typing

from sonic_package_manager import constraint, common


class Package:
    """ SONiC Package. """

    def __init__(self, manifest: typing.Dict):
        """ Create an instance of Package.

        Args:
            manifest: Dictionary representing manifest file.
        """

        self._manifest = manifest

    def get_manifest(self) -> typing.Dict:
        """ Returns the manifest content.

        Returns:
            Manifest content.
        """

        return self._manifest

    def get_sonic_version_constraint(self) -> constraint.VersionConstraint:
        """ Returns SONiC version constraint.

        Returns:
            SONiC version constraint.
        """

        manifest = self.get_manifest()
        package_props = manifest.get('package', dict())
        # Allow any SONiC version if not defined
        version_constraint_str = package_props.get('sonic-version', '*')
        return constraint.parse_version_constraint(version_constraint_str)

    def get_dependencies(self) -> typing.List[constraint.PackageConstraint]:
        """ Returns the dependencies list.

        Returns:
            List of dependencies constraints.
        """

        dependencies = []
        manifest = self.get_manifest()
        package_props = manifest.get('package')
        if package_props is None:
            return []
        for depstring in package_props.get('depends', list()):
            dependencies.append(constraint.parse_package_constraint(depstring))

        return dependencies

    def get_conflicts(self) -> typing.List[constraint.PackageConstraint]:
        """ Returns the list of packages this package breaks.

        Returns:
            List of conflicts constraints.
        """

        breaks = []
        manifest = self.get_manifest()
        package_props = manifest.get('package')
        if package_props is None:
            return []
        for constraint_expr in package_props.get('breaks', list()):
            breaks.append(constraint.parse_package_constraint(constraint_expr))

        return breaks

    def get_feature_name(self) -> str:
        """ Returns feature name.

        Returns:
            Feature name.
        """

        return self._manifest['service']['name']

    def is_asic_service(self) -> bool:
        """ Check if the package provides an ASIC service.

        Returns:
            True if a service is an ASIC service, False otherwise.
        """

        manifest = self.get_manifest()
        return manifest['service'].get('asic-service', False)

    def is_host_service(self) -> bool:
        """ Check if the package provides a host service.

        Returns:
            True if a service is a host service, False otherwise.
        """

        manifest = self.get_manifest()
        return manifest['service'].get('host-service', True)

    def get_changelog(self) -> typing.Dict[constraint.Version, typing.List[str]]:
        """ Returns:
            A changelog formatted as an dictionary.
            e.g.:
                1.0.0:
                    - initial release
                1.2.0:
                    - bug fixes
                    - added functionality
        """

        package_props = self.get_manifest().get('package', dict())
        changelog = package_props.get('changelog')
        return changelog

    def get_initial_config(self) -> typing.Optional[typing.Dict[str, typing.Dict[str, str]]]:
        """
        Returns:
            Initial configuration for this package. It may return None if
            package does not provide initial configuration.
        """

        package_props = self.get_manifest().get('package', dict())
        init_cfg = package_props.get('initial-config')
        return init_cfg

