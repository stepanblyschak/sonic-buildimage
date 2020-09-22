#!/usr/bin/env python3

import os
import shutil
import docker

import swsssdk

from sonic_package_manager.imagepull import ImagePull
from sonic_package_manager.metadatainstall import MetadataInstall
from sonic_package_manager.feature import FeatureTableUpdater
from sonic_package_manager.systemd import SystemdGenerator

from sonic_package_manager.database import PackageDatabase
from sonic_package_manager.errors import PackageInstallationError, PackageManagerError

class PackageInstallation:
    ''' Package installation process '''

    def __init__(self, name, version=None):
        database = PackageDatabase()
        connector = swsssdk.ConfigDBConnector()
        package = database.get_package(name)
        if version is None:
            version = package.get_default_version()

        image_pull = ImagePull(package, version)
        metadata_install = MetadataInstall(package)
        feature_updater = FeatureTableUpdater(connector, package)
        systemd_gen = SystemdGenerator(database, package)

        self._operations = [
            image_pull,
            metadata_install,
            systemd_gen,
            feature_updater,
        ]

        self._package = package

    def install_package(self):
        ''' Install SONiC package and integrate in system. '''

        if self._package.is_installed():
            raise PackageInstallationError("Package {} is already installed. "
                    "Uninstall the package first if you are trying to "
                    "re-install or upgrade".format(self._package.get_name()))

        done_operations = []

        try:
            while self._operations:
                operation = self._operations.pop(0)
                operation.execute()
                done_operations.append(operation)
        except PackageInstallationError as err:
            # restore
            while done_operations:
                operation = done_operations.pop(0)
                try:
                    operation.restore()
                except PackageManagerError:
                    pass # continue restoring
            # re-raise exception
            raise err


    def uninstall_package(self):
        ''' Uninstall SONiC package from the system '''

        # Not installed, then skip
        if not self._package.is_installed():
            return

        # Built-in packages cannot be removed, they are must for SONiC to run properly
        if self._package.is_builtin():
            raise PackageInstallationError("Cannot remove {} since it "
                    "is an essential package".format(self._package.get_name()))

        self._operations = list(reversed(self._operations))

        while self._operations:
            operation = self._operations.pop(0)
            operation.restore()

