#!/usr/bin/env python

import docker
from unittest import mock
import semver

from sonic_package_manager import image
from sonic_package_manager.package import Package
from sonic_package_manager.repository import Repository


def test_imagepull_installation():
    """ Test Image installation. """

    docker_client = mock.Mock(docker.client.APIClient)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    version = semver.Version.parse('1.0.0')

    repo.get_name = mock.Mock(return_value='test')
    repo.get_repository = mock.Mock(return_value='host:port/image')

    docker_image = mock.Mock()
    docker_image.tag = mock.Mock()
    docker_client.images.pull = mock.Mock(return_value=docker_image)

    image.pull(docker_client, repo, version)

    docker_client.images.pull.assert_called_once_with('host:port/image', '1.0.0')
    docker_image.tag.assert_called_once_with('host:port/image', 'latest')


def test_imagepull_uninstallation():
    """ Test Image uninstallation. """

    docker_client = mock.Mock(docker.client.APIClient)
    repo = mock.Mock(Repository)
    version = semver.Version.parse('1.0.0')

    repo.get_name = mock.Mock(return_value='test')
    repo.get_repository = mock.Mock(return_value='host:port/image')

    docker_client.containers.list = mock.MagicMock()
    docker_client.images.list = mock.MagicMock()

    image.remove(docker_client, repo, version)
