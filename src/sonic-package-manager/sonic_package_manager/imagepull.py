#!/usr/bin/env python

''' This module implements Docker Image pulling. '''

import docker

from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger


def install_docker_image(docker_client, repository, version):
    ''' Pull the docker image associated with this repository.

    Args:
        docker_client (docker.client.DockerClient(): Docker client.
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    Raises:
        PackageInstallationError: If the operation fails to download the image.
    '''

    images  = docker_client.images
    repourl = repository.get_repository()
    tag     = str(version)

    get_logger().info('Pulling image {}'.format(repourl))

    try:
        image = images.pull(repourl, tag)
        image.tag(repourl, 'latest')
    except docker.errors.APIError as err:
        uninstall_docker_image(docker_client, repository, version)
        raise PackageInstallationError('Failed to download {}: {}'.format(repourl, err))

    get_logger().info('Image pulled successfully')


def uninstall_docker_image(docker_client, repository, version):
    ''' Revert the image pull operation.

    Args:
        docker_client (docker.client.DockerClient(): Docker client.
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    '''

    repourl = repository.get_repository()
    tag     = str(version)

    _remove_runnnig_instances(docker_client, repourl, tag)
    _remove_installed_images(docker_client, repourl, tag)


def _get_image_name(repo, tag):
    ''' Returns the image reference as <repository>:<tag>.

    Args:
        repo (str): Repository string.
        tag (str): An image tag.

    Returns:
        str: image reference as <repository>:<tag>.
    '''

    return '{}:{}'.format(repo, tag)


def _remove_runnnig_instances(docker_client, repo, tag):
    ''' Remove all running containers created
        from the package image. '''

    containers = docker_client.containers
    for container in containers.list(all=True):
        container_image = container.attrs['Config']['Image']
        if (container_image == _get_image_name(repo, 'latest') or
            container_image == _get_image_name(repo, tag)):
            container.remove(force=True)


def _remove_installed_images(docker_client, repo, tag):
    ''' Removes all installed repository tags of a package. '''

    images = docker_client.images
    for image in images.list(all=True):
        repotags = image.attrs['RepoTags']
        for repotag in repotags:
            if (repotag == _get_image_name(repo, tag) or
                repotag == _get_image_name(repo, 'latest')):
                get_logger().info('Removing {}'.format(repotag))
                images.remove(image=repotag, force=True)

