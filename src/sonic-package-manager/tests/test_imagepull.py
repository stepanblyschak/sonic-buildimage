#!/usr/bin/env python

import docker
import mock
import pytest
import semver
from sonic_package_manager.errors import *
from sonic_package_manager.imagepull import *
from sonic_package_manager.package import *
from sonic_package_manager.repository import *


def test_imagepull_installation():
    ''' Test ImagePull installation. '''

    docker_client = mock.Mock(docker.client.AutoVersionClient)
    repo          = mock.Mock(Repository)
    package       = mock.Mock(Package)
    version       = semver.Version.parse('1.0.0')

    repo.get_name       = mock.Mock(return_value='test')
    repo.get_repository = mock.Mock(return_value='host:port/image')

    image = mock.Mock()
    image.tag = mock.Mock()
    docker_client.images.pull = mock.Mock(return_value=image)

    imagepull = ImagePull(docker_client)

    imagepull.install(repo, version)

    docker_client.images.pull.assert_called_once_with('host:port/image', '1.0.0')
    image.tag.assert_called_once_with('host:port/image', 'latest')

def test_imagepull_uninstallation():
    ''' Test ImagePull uninstallation. '''

    docker_client = mock.Mock(docker.client.AutoVersionClient)
    repo          = mock.Mock(Repository)
    package       = mock.Mock(Package)
    version       = semver.Version.parse('1.0.0')

    repo.get_name       = mock.Mock(return_value='test')
    repo.get_repository = mock.Mock(return_value='host:port/image')

    docker_client.containers.list = mock.MagicMock()
    docker_client.images.list = mock.MagicMock()

    imagepull = ImagePull(docker_client)

    imagepull.uninstall(repo, version)

