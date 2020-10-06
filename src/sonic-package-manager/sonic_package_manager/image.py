#!/usr/bin/env python

""" This module implements Docker Image pulling. """

import docker

from sonic_package_manager import errors
from sonic_package_manager.logger import get_logger

from sonic_package_manager import repository


def pull(docker_client: docker.api.APIClient,
         repo: repository.Repository,
         version: str):
    """ Pull the docker image associated with this repository.

    Args:
        docker_client: Docker client.
        repo: Repository object.
        version: SONiC package version to install.
    Raises:
        PackageInstallationError: If the operation fails to download the image.
    """

    images = docker_client.images
    repourl = repo.get_repository()
    tag = str(version)

    get_logger().info(f'Pulling image {repourl}')
    try:
        image = images.pull(repourl, tag)
        image.tag(repourl, 'latest')
    except docker.errors.APIError as err:
        remove(docker_client, repo, version)
        raise errors.PackageInstallationError(f'Failed to download {repourl}: {err}')

    get_logger().info('Image pulled successfully')


def remove(docker_client: docker.api.APIClient,
           repo: repository.Repository,
           version: str):
    """ Revert the image pull operation.

    Args:
        docker_client: Docker client.
        repo: Repository object.
        version: SONiC package version to install.
    """

    repourl = repo.get_repository()
    tag = str(version)

    _remove_runnnig_instances(docker_client, repourl, tag)
    _remove_installed_images(docker_client, repourl, tag)


def _get_image_name(repo: str, tag: str) -> str:
    """ Returns the image reference as <repository>:<tag>.

    Args:
        repo: Repository string.
        tag: An image tag.

    Returns:
        image reference as <repository>:<tag>.
    """

    return f'{repo}:{tag}'


def _remove_runnnig_instances(docker_client, repo, tag):
    """ Remove all running containers created
        from the package image. """

    containers = docker_client.containers
    for container in containers.list(all=True):
        container_image = container.attrs['Config']['Image']
        if (container_image == _get_image_name(repo, 'latest') or
                container_image == _get_image_name(repo, tag)):
            container.remove(force=True)


def _remove_installed_images(docker_client, repo, tag):
    """ Removes all installed repository tags of a package. """

    images = docker_client.images
    for image in images.list(all=True):
        repotags = image.attrs['RepoTags']
        for repotag in repotags:
            if (repotag == _get_image_name(repo, tag) or
                    repotag == _get_image_name(repo, 'latest')):
                get_logger().info(f'Removing {repotag}')
                images.remove(image=repotag, force=True)
