#!/usr/bin/env python

from dataclasses import dataclass

from sonic_package_manager.database import PackageEntry
from sonic_package_manager.manifest import Manifest


@dataclass
class Package:
    """ Package class is a representation of Package.

    Attributes:
        entry: Package entry in package database
        manifest: Manifest for this package
        name: Name of the package from package database
        repository: Default repository to pull this package from
        image_id: Docker image ID of the installed package;
                  It is set to None if package is not installed.
        installed: Boolean flag whether package is installed or not.
        build_in: Boolean flag whether package is built in or not.

    """

    entry: PackageEntry
    manifest: Manifest

    @property
    def name(self): return self.entry.name

    @property
    def repository(self): return self.entry.repository

    @property
    def image_id(self): return self.entry.image_id

    @property
    def installed(self): return self.entry.installed

    @property
    def built_in(self): return self.entry.built_in

    @property
    def version(self): return self.entry.version
