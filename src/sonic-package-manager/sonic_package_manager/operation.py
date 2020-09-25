#!/usr/bin/env python

from collections import defaultdict

class Operation:
    ''' Package installation operation interface. '''

    def execute(self):
        ''' Execute the operation. If the operation fails, raises a PackageManagerError.
            This method is required to cleanup on failure.

            Args:
                self (Operation): Operation instance.
            Returns:
                None.
        '''

        raise NotImplementedError

    def restore(self):
        ''' Restore the system from operation done in execute().
            This operation restore should not fail normally, but it is required to leave
            the system in a clean state.

            Args:
                self (Operation): Operation instance.
            Returns:
                None.
        '''

        raise NotImplementedError



from sonic_package_manager.errors import *

class ReqCheck:
    def __init__(self, package, database):
        self._package = package
        self._database = database
    def execute():
        dependencies = self._package.get_dependencies()
        for dependency in dependencies:
            if not self._database.has_package(dependency.packagename):
                raise PackageMissingDependecyError(dependency)
            package = self._database.get_package(dependency.pkgname)
            version = package.get_installed_version()
            if not dependency.versionrange.allows_all(version):
                raise PackageDependecyVersionError(dependency)



