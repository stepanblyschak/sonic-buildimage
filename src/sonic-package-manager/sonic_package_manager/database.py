#!/usr/bin/env python

import os
import yaml

from sonic_package_manager.package import Package
from sonic_package_manager.errors import PackageManagerError, PackageNotFoundError


class PackageDatabase:
    ''' An interface to SONiC packages database '''

    SPM_PATH = '/var/lib/sonic-package-manager/'

    def __init__(self):
        ''' Initialize PackageDatabase. Reads the content of packages.yml and loads
        the database.
        '''

        self._package_database = {}

        try:
            with open(self.get_sonic_packages_file()) as database:
                self._package_database = yaml.safe_load(database)
        except OSError as err:
            raise PackageManagerError(
                    "Failed to read {}: {}".format(self.get_sonic_packages_file(), err)
                  )

    def __iter__(self):
        ''' Iterates over packages in the database. '''

        for name, _ in self._package_database.items():
            yield self.get_package(name)

    def get_package(self, name):
        ''' Return a packages called name.
        If the packages wan't found  PackageNotFoundError is thrown.
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
        '''

        try:
            self.get_package(name)
            return True
        except PackageNotFoundError:
            return False

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

