#!/usr/bin/env python
from dataclasses import dataclass

from sonic_package_manager.database import PackageEntry
from sonic_package_manager.manifest import Manifest


@dataclass
class Package:
    entry: PackageEntry
    reference: str
    manifest: Manifest

    @property
    def name(self): return self.entry.name

    @property
    def repository(self): return self.entry.repository

    @property
    def installed(self): return self.entry.installed

    @property
    def built_in(self): return self.entry.built_in

    @property
    def version(self): return self.entry.version
