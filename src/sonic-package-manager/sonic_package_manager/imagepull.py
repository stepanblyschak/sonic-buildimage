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

            self._client.tag('{}:{}'.format(self._package.get_repository(), self._version),
                    self._package.get_repository(), tag='latest')
        except docker.errors.APIError as err:
            self.restore()
            raise err

    def restore(self):
        ''' Restore the image pull operation. '''

        for tag in ('latest', self._version):
            get_logger().info('Untagging {}:{}'.format(self._package.get_repository(), tag))
            self._client.remove_image('{}:{}'.format(self._package.get_repository(), tag), True)


