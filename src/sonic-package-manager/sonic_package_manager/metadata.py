#!/usr/bin/env python

""" MetadataInstall implements copying SONiC package metadata to host filesystem. """

import io
import os
import shutil
import tarfile
import typing

import docker

from sonic_package_manager import repository
from sonic_package_manager.common import (get_package_image_metadata_folder,
                                          get_package_metadata_folder)
from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger


def install_metadata(docker_client: docker.api.APIClient,
                     repo: repository.Repository):
    """ Copy SONiC package metadata folder.

    Args:
        docker_client: Docker client
        repository: Repository object.
    Raises:
        PackageInstallationError: If the operation fails.
    """

    get_logger().info('Copying package metadata...')

    # cleanup left overs first
    _remove_package_folder(repo)

    _create_package_folder(repo)
    tar = _get_package_metadata_tar(docker_client, repo)
    _save_package_metadata(repo, tar)


def uninstall_metadata(repository: repository.Repository):
    """ Remove SONiC package metadata folder.

    Args:
        repository: Repository object.
    Raises:
        PackageInstallationError: If the operation fails.
    """

    _remove_package_folder(repository)
    get_logger().info('Removed package metadata...')


def _create_package_folder(repo: repository.Repository):
    """ Creates a dedicated folder for package metadata.

    Args:
        repo: Repository object.
    """

    try:
        os.makedirs(get_package_metadata_folder(repo.get_name()))
    except OSError as err:
        raise PackageInstallationError(f'Failed to create a package metadata folder: {err}')


def _remove_package_folder(repository: repository.Repository):
    """ Removes the folder with package metadata.

    Args:
        repository: Repository object.
    """

    metadatafolder = get_package_metadata_folder(repository.get_name())

    if not os.path.exists(metadatafolder):
        return

    try:
        shutil.rmtree(metadatafolder)
    except OSError as err:
        raise PackageInstallationError(f'Failed to remove package metadata: {err}')


def _get_package_metadata_tar(docker_client: docker.api.APIClient,
                              repo: repository.Repository) -> typing.BinaryIO:
    """ Returns a file object of a tar archive with package metadata.

    Args:
        docker_client: Docker API client.
        repo: Repository object.
    Returns:
        file-like object of tar archive content.
    """

    image = '{}:{}'.format(repo.get_repository(), 'latest')
    buf = bytes()

    try:
        container = docker_client.containers.run(image, entrypoint='/bin/bash -c "sleep inf"', detach=True)
    except docker.errors.APIError as err:
        raise PackageInstallationError('Failed to start container: {}'.format(err))

    try:
        bits, _ = container.get_archive(get_package_image_metadata_folder())
        for chunk in bits:
            buf += chunk
    except docker.errors.APIError as err:
        raise PackageInstallationError('Failed to copy package metadata. '
                                       'Is this image an SONiC package?: {}'.format(err))
    finally:
        container.remove(force=True)

    return io.BytesIO(buf)


def _save_package_metadata(repo: repository.Repository, tar: typing.BinaryIO):
    """ Save package metadata object on host OS filesystem.

    Args:
        repo: Repository object.
        tar: Tar archive.
    """

    with tarfile.open(fileobj=tar) as tar:
        for member in tar:
            relativepath = os.path.relpath(member.name,
                                           os.path.basename(get_package_image_metadata_folder()))
            # omit the folder itself, copy all the content of the folder
            if relativepath == os.curdir:
                continue
            get_logger().info(f'Copying package metadata: {relativepath}')
            member.name = relativepath
            tar.extract(member, get_package_metadata_folder(repo.get_name()))
