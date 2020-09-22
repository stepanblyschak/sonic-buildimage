#!/usr/bin/env python

import os
import io
import tarfile
import shutil
import docker

from sonic_package_manager.logger import get_logger
from sonic_package_manager.operation import Operation
from sonic_package_manager.database import PackageDatabase
from sonic_package_manager.errors import PackageInstallationError


class MetadataInstall(Operation):
    ''' MetadataInstall implements copying SONiC package metadata
    to host filesystem.
    '''

    SONIC_PACKAGE_METADATA_FOLDER = '/var/lib/sonic-package'

    def __init__(self, package):
        ''' Initialize MetadataInstall instance. '''

        self._client  = docker.from_env()
        self._package = package

    def execute(self):
        ''' Execute the operation. '''

        get_logger().info('Copying package metadata...')

        container = self._client.containers.run(
                '{}:{}'.format(self._package.get_repository(), 'latest'),
                entrypoint='/bin/bash -c "sleep inf"', detach=True)
        try:
            buf = bytes()

            try:
                bits, _ = container.get_archive(self.SONIC_PACKAGE_METADATA_FOLDER)
            except docker.errors.APIError as err:
                raise PackageInstallationError('Failed to copy package metadata. '
                        'Is this image an SONiC package?: {}'.format(err))

            for chunk in bits:
                buf += chunk

            try:
                os.makedirs(PackageDatabase.get_package_metadata_folder(self._package))
            except OSError as err:
                raise PackageInstallationError('Failed to create a package metadata folder: {}'.format(err))

            with tarfile.open(fileobj=io.BytesIO(buf)) as tar:
                for member in tar:
                    relativepath = os.path.relpath(member.name,
                        os.path.basename(self.SONIC_PACKAGE_METADATA_FOLDER))
                    # omit the folder itself, copy all the content of the folder
                    if relativepath == os.curdir:
                        continue
                    get_logger().info('Copying package metadata: {}'.format(relativepath))
                    member.name = relativepath
                    tar.extract(member, PackageDatabase.get_package_metadata_folder(self._package))
        finally:
            container.remove(force=True)

    def restore(self):
        ''' Execute restore operation for this operation. '''

        try:
            shutil.rmtree(PackageDatabase.get_package_metadata_folder(self._package))
        except FileNotFoundError:
            pass
        except OSError as err:
            raise PackageInstallationError('Failed to remove package metadat: {}'.format(err))

        get_logger().info('Removed package metadata...')

