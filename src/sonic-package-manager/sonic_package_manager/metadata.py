#!/usr/bin/env python

''' MetadataInstall implements copying SONiC package metadata to host filesystem. '''

import io
import os
import shutil
import tarfile

import docker

from sonic_package_manager.common import (get_package_image_metadata_folder,
                                          get_package_metadata_folder)
from sonic_package_manager.database import RepositoryDatabase
from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger



def install_metadata(docker_client, repository, version):
    ''' Copy SONiC package metadata folder.

    Args:
        docker_client (docker.client.DockerClient): Docker client
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    Raises:
        PackageInstallationError: If the operation fails.
    '''

    get_logger().info('Copying package metadata...')

    # cleanup left overs first
    _remove_package_folder(repository)

    _create_package_folder(repository)
    tar = _get_package_metadata_tar(docker_client, repository)
    _save_package_metadata(repository, tar)


def uninstall_metadata(repository, version):
    ''' Remove SONiC package metadata folder.

    Args:
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    Raises:
        PackageInstallationError: If the operation fails.
    '''

    _remove_package_folder(repository)
    get_logger().info('Removed package metadata...')


def _create_package_folder(repo):
    ''' Creates a dedicated folder for package metadata.

    Args:
        repo (Repository): Repository object.
    '''

    try:
        os.makedirs(get_package_metadata_folder(repo))
    except OSError as err:
        raise PackageInstallationError('Failed to create a package metadata folder: {}'.format(err))


def _remove_package_folder(repository):
    ''' Removes the folder with package metadata.

    Args:
        repo (Repository): Repository object.
    '''


    metadatafolder = get_package_metadata_folder(repository)

    if not os.path.exists(metadatafolder):
        return

    try:
        shutil.rmtree(metadatafolder)
    except OSError as err:
        raise PackageInstallationError('Failed to remove package metadata: {}'.format(err))


def _get_package_metadata_tar(docker_client, repo):
    ''' Returns a file object of a tar archive with package metadata.

    Args:
        repo (Repository): Repository object.
    Returns:
        file: file-like object of tar archive content.
    '''

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


def _save_package_metadata(repo, tar):
    ''' Save package metadata object on host OS filesystem.

    Args:
        repo (Repository): Repository object.
        tar (file): Tar archive.
    '''

    with tarfile.open(fileobj=tar) as tar:
        for member in tar:
            relativepath = os.path.relpath(member.name,
                os.path.basename(get_package_image_metadata_folder()))
            # omit the folder itself, copy all the content of the folder
            if relativepath == os.curdir:
                continue
            get_logger().info('Copying package metadata: {}'.format(relativepath))
            member.name = relativepath
            tar.extract(member, get_package_metadata_folder(repo))


