#!/usr/bin/env python

''' This module implements Docker Image pulling. '''

import docker
import click

from sonic_package_manager.operation import Operation
from sonic_package_manager.logger import get_logger

class ImagePull(Operation):
    ''' Pull SONiC Package Docker Image from Docker registry. '''

    def __init__(self, package, version):
        ''' Initialize ImagePull instance.

        Args:
            self (ImagePull): ImagePull instance.
            package (Package): SONiC package object.
            version (str): SONiC package version to install.
        Returns:
            None.
        '''

        self._client = docker.APIClient()
        self._sdk_client = docker.from_env()
        self._package = package
        self._version = version

    def execute(self):
        ''' Execute the operation, pull the docker image associated
            with this package from Docker registry.

        Args:
            self (ImagePull): ImagePull instance.
        Returns:
            None.
        '''

        try:
            with click.progressbar(length=100) as bar:
                stream = self._client.pull(self._package.get_repository(),
                        tag=self._version, stream=True, decode=True)
                get_logger().info('Downloading image from {}'.format(self._package.get_repository()))
                for line in stream:
                    if 'progressDetail' in line and 'current' in line['progressDetail']:
                        bar.update(int(line['progressDetail']['current']) * 100 / int(line['progressDetail']['total']))
                bar.update(100)

            # Tag as latest
            self._client.tag('{}'.format(self._get_image_name(self._version)),
                    self._package.get_repository(), tag='latest')
        except docker.errors.APIError as err:
            self.restore()
            raise err

    def restore(self):
        ''' Restore the image pull operation. '''

        self._remove_runnnig_instances()

        for tag in ('latest', self._version):
            get_logger().info('Removing {}'.format(self._get_image_name(tag)))
            self._client.remove_image('{}'.format(self._get_image_name(tag)), True)

    def _get_image_name(self, tag):
        ''' Returns the image name. '''

        return '{}:{}'.format(self._package.get_repository(), tag)

    def _remove_runnnig_instances(self):
        ''' Remove all running containers created from the package image. '''

        for container in self._sdk_client.containers.list(all=True):
            if container.attrs['Config']['Image'] == self._get_image_name('latest'):
                container.remove(force=True)

