#!/usr/bin/env python

import os
import yaml

from sonic_package_manager.package import Package
from sonic_package_manager.errors import PackageManagerError, PackageNotFoundError


class PackageDatabase:
    ''' An interface to SONiC packages database '''

    SPM_PATH = '/var/lib/sonic-package-manager/'

    @staticmethod
    def get_library_dir():
        ''' Return sonic-package-manager directory. '''

        return PackageDatabase.SPM_PATH

    @staticmethod
    def get_sonic_packages_file():
        ''' Return packages.yml path in SONiC OS. '''

        return os.path.join(PackageDatabase.SPM_PATH, 'packages.yml')

    @staticmethod
    def get_sonic_package_base_dir(name):
        ''' Return a base path for package called name. '''

        return os.path.join(PackageDatabase.SPM_PATH, name)

    @staticmethod
    def get_package_metadata_folder(package):
        ''' Return a base path for package. '''

        return PackageDatabase.get_sonic_package_base_dir(package.get_name())

    def __init__(self):
        ''' Initialize PackageDatabase.
        Reads the content of packages.yml and loads the database.
        '''

        self._package_database = self._read_db()


    def add_package(self, name, repository, description=None, default_version=None):
        ''' Add a new package entry in database.

        Args:
            name (str): package name.
            repository (str): package repository.
            description (str): description field.
            default_version (str): default installation version.
        '''

        if self.has_package(name):
            raise PackageManagerError("Package {} already exists in database".format(name))

        self._package_database[name] = {
            'repository': repository,
            'description': description,
            'default-version': default_version,
        }

        self._commit_db(self._package_database)

    def remove_package(self, name):
        ''' Remove a package entry from database.

        Args:
            name (str): package name.
        '''

        if not self.has_package(name):
            raise PackageManagerError("Package {} does not exist in database".format(name))

        package = self.get_package(name)

        if package.is_installed():
            raise PackageManagerError("Package {} is installed, uninstall the package first".format(name))

        self._package_database.pop(name)

        self._commit_db(self._package_database)

    def get_package(self, name):
        ''' Return a packages called name.
        If the packages wan't found  PackageNotFoundError is thrown.

        Args:
            name (str): SONiC package name
        Returns:
            (Package): SONiC Package object
        '''

        try:
            package_info = self._package_database[name]
        except KeyError:
            raise PackageNotFoundError(name)

        package_path = self.get_sonic_package_base_dir(name)
        return Package(name, package_info, package_path)

    def has_package(self, name):
        ''' Checks if the database contains an entry for a package
        called name. Returns True if the package exists, otherwise False.

        Args:
            name (str): SONiC package name
        Returns:
            (bool): True of the package exists, otherwise False.
        '''

        try:
            self.get_package(name)
            return True
        except PackageNotFoundError:
            return False

    def update_package_status(self, name, status):
        ''' Updates package instllation status.

        Args:
            name (str): SONiC package name
            status (str): Installation status (installed, not-installed)
        Returns:
            None.
        '''

        if not self.has_package(name):
            raise PackageNotFoundError(name)

        pkg = self._package_database[name]
        pkg['status'] = status

        self._commit_db(self._package_database)

    def update_package_version(self, name, version):
        ''' Updates package instllation status.

        Args:
            name (str): SONiC package name
            version (str): Version that is installed.
        Returns:
            None.
        '''

        if not self.has_package(name):
            raise PackageNotFoundError(name)

        pkg = self._package_database[name]
        pkg['version'] = version

        self._commit_db(self._package_database)

    def _read_db(self):
        ''' Read the database file.

        Returns:
            (dict): Package database content.
        '''

        dbfile = self.get_sonic_packages_file()
        try:
            with open(dbfile) as database:
                return yaml.safe_load(database)
        except OSError as err:
            raise PackageManagerError("Failed to read {}: {}".format(dbfile, err))

    def _commit_db(self, content):
        ''' Save the database to persistent file.

        Args:
            content (dict): Database content.
        '''

        dbfile = self.get_sonic_packages_file()
        try:
            with open(dbfile, 'w') as database:
                return yaml.safe_dump(content, database)
        except OSError as err:
            raise PackageManagerError("Failed to write to {}: {}".format(dbfile, err))

    def __iter__(self):
        ''' Iterates over packages in the database.

        Yields:
            package (Package): SONiC Package object

        '''

        for name, _ in self._package_database.items():
            yield self.get_package(name)

