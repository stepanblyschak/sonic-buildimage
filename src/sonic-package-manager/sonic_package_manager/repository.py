#!/usr/bin/env python

from sonic_package_manager.errors import PackageManagerError
from sonic_package_manager.package import Package
from sonic_package_manager.manifest import get_manifest
from sonic_package_manager.constraint import (
    parse_version_constraint,
    parse_package_constraint,
)


class Repository:
    ''' Repository entry. '''

    def __init__(self, name, metadata):
        ''' Create an instance of Repository.

        Args:
            name     (str)  : Repository name.
            metadata (dict) : Database information about this repository.
        '''

        self._name     = name
        self._metadata = metadata

    def get_name(self):
        ''' Returns package name.

        Returns:
            str: Repository name string.
        '''

        return self._name

    def get_repository(self):
        ''' Returns repository url.

        Returns:
            str: Repository url string.
        '''

        return self._metadata['repository']

    def get_default_version(self):
        ''' Returns repository default installation candidate.

        Returns:
            (VersionConstraint): Default repositiry installation candidate.
        '''

        return parse_version_constraint(self._metadata['default-version'])

    def get_description(self):
        ''' Returns repository description.

        Returns:
            str: Repository description string. May return None.
                 if package entry does not have description field.
        '''

        return self._metadata.get('description')

    def get_installed_version(self):
        ''' Returns an installed version as string.
        Returns None if the package is not installed.

        Returns:
            (semver.Version): Installed package version.
        '''

        return parse_version_constraint(self._metadata['version'])

    def get_status(self):
        ''' Tells the respository status - Installed/Not Installed/Built-In.

        Returns:
            str: repository installation status string.
        '''

        if self.is_builtin():
            return "Built-In"
        elif self.is_installed():
            return "Installed"
        else:
            return "Not Installed"

    def get_metadata(self):
        ''' Returns repository metadata it was initialized with.

        Returns:
            dict: repository metadata.
        '''

        return self._metadata

    def is_builtin(self):
        ''' Tells if a repository is essential.

        Returns:
            bool: True if the repository is essential, False otherwise.
        '''

        return self._metadata.get("essential", False)

    def is_installed(self):
        ''' Tells if a repository is installed.

        Returns:
            bool: True if the repository is installed, False otherwise.
        '''

        return self._metadata.get('status') == 'installed'

    def get_package(self):
        ''' Return an instance of Package.

        Returns:
            Package: Package object corresponding to this package entry.

        Raises:
            PackageManagerError: If the package manifest is not found.
        '''

        return Package(self, get_manifest(self))

    def update_installation_status(self, status, version=None):
        ''' Updates status of the Repository.

        Args:
            status (str): 'installed' or 'not-installed' string.
            version (str): version of installed package.
        '''

        self._metadata['status'] = status
        self._metadata['version'] = str(version)

