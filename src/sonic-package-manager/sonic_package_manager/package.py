#!/usr/bin/env python

from sonic_package_manager.errors import PackageManagerError
from sonic_package_manager.manifest import get_manifest
from sonic_package_manager.constraint import (
    parse_version_constraint,
    parse_package_constraint,
)


class Package:
    ''' SONiC Package. '''

    def __init__(self, repository, manifest):
        ''' Create an instance of Package.

        Args:
            manifest (dict) : Manifest of this package.
        '''

        self._repository = repository
        self._manifest = manifest

    def get_repository(self):
        ''' Returns the Repository object for this package.

        Returns:
            Repository: Repository object.
        '''

        return self._repository

    def get_manifest(self):
        ''' Returns the manifest content.

        Returns:
            dict: Manifest content.
        '''

        return self._manifest

    def get_sonic_version_constraint(self):
        ''' Returns SONiC version constraint.

        Returns:
            VersionConstraint: SONiC version constraint.
        '''

        manifest = self.get_manifest()
        package_props = manifest.get('package', dict())
        # Allow any SONiC version if not defined
        return parse_version_constraint(package_props.get('sonic-version', '*'))

    def get_dependencies(self):
        ''' Returns the dependencies.

        Returns:
            List[PackageConstraint]: list of dependencies.
        '''

        dependencies = []
        manifest = self.get_manifest()
        package_props = manifest.get('package')
        if package_props is None:
            return []
        for depstring in package_props.get('depends', list()):
            dependencies.append(parse_package_constraint(depstring))

        return dependencies

    def get_conflicts(self):
        ''' Returns the list of packages this package breaks.

        Returns:
            List[PackageConstraint]: list of conflicts.
        '''

        breaks = []
        manifest = self.get_manifest()
        package_props = manifest.get('package')
        if package_props is None:
            return []
        for constraint_expr in package_props.get('breaks', list()):
            breaks.append(parse_package_constraint(constraint_expr))

        return breaks

    def get_feature_name(self):
        ''' Returns feature name.

        Returns:
            str: feature name
        '''

        return self._manifest['service']['name']

