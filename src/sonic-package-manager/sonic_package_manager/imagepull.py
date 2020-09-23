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
            package (Package): SONiC package object.
            version (str): SONiC package version to install.
        Returns:
            None.
        '''

        self._client = docker.from_env()
        self._package = package
        self._version = version

    def execute(self):
        ''' Execute the operation, pull the docker image associated
            with this package from Docker registry.'''

        images = self._client.images
        try:
            get_logger().info('Downloading image {}'.format(self._package.get_repository()))
            image = images.pull(self._package.get_repository(), self._version)
            image.tag(self._package.get_repository(), 'latest')
        except docker.errors.APIError as err:
            self.restore()
            raise err

    def restore(self):
        ''' Restore the image pull operation. '''

        self._remove_runnnig_instances()
        self._remove_installed_images()

    def _get_image_name(self, tag):
        ''' Returns the image reference as <repository>:<tag>.

        Args:
            tag (str): An image tag.

        Returns:
            None.
        '''

        return '{}:{}'.format(self._package.get_repository(), tag)

    def _remove_runnnig_instances(self):
        ''' Remove all running containers created
            from the package image. '''

        containers = self._client.containers
        for container in containers.list(all=True):
            container_image = container.attrs['Config']['Image']
            if container_image == self._get_image_name('latest'):
                container.remove(force=True)

    def _remove_installed_images(self):
        ''' Removes all installed repository tags of a package. '''

        images = self._client.images
        for image in images.list(all=True):
            repotags = image.attrs['RepoTags']
            for tag in repotags:
                if (tag == self._get_image_name(self._version) or
                    tag == self._get_image_name('latest')):
                    get_logger().info('Removing {}'.format(tag))
                    images.remove(image=tag, force=True)

