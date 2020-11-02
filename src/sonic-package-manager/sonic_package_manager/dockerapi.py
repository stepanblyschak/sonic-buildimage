#!/usr/bin/evn python

""" Module provides Docker interface. """

import contextlib
from typing import Optional

from sonic_package_manager.logger import log
from sonic_package_manager.progress import ProgressManager


def is_digest(ref: str):
    return ref.startswith('sha256:')


def bytes_to_mb(bytes):
    return bytes / 1024 / 1024


def get_id(line):
    return line['id']


def get_status(line):
    return line['status']


def get_progress(line):
    progress = line['progressDetail']
    current = bytes_to_mb(progress['current'])
    total = bytes_to_mb(progress['total'])
    return current, total


class DockerApi:
    """ DockerApi provides a set of methods -
     wrappers around docker client methods """

    def __init__(self, client):
        self.client = client

    def pull(self, repository: str,
             reference: str,
             tag: Optional[str] = None,
             progress_manager: Optional[ProgressManager] = None):
        """ Docker 'pull' command.
        Args:
            repository: repository to pull
            reference: tag or digest
            tag: tag the image right after pull with this tag
            progress_manager: ProgressManager instance
        """

        if is_digest(reference):
            image = f'{repository}@{reference}'
        else:
            image = f'{repository}:{reference}'

        log.debug(f'pulling image by digest {image}')

        api = self.client.api
        digest = None

        with progress_manager or contextlib.nullcontext():
            for line in api.pull(repository,
                                 reference,
                                 stream=True,
                                 decode=True):
                log.debug(f'pull status: {line}')
                if progress_manager is None:
                    continue
                try:
                    id = get_id(line)
                    status = get_status(line)
                    if id not in progress_manager:
                        _, total = get_progress(line)
                        progress_manager.new(id,
                                             total=total,
                                             unit='Mb',
                                             desc=f'{status} {id}')
                    pbar = progress_manager.get(id)

                    # Complete status
                    if 'complete' in status:
                        pbar.desc = f'{status} {id}'
                        pbar.update(pbar.total)
                        log.info(f'{status} {id}')
                        continue

                    current, total = get_progress(line)
                    # Status changed
                    if status not in pbar.desc:
                        pbar.desc = f'{status} {id}'
                        pbar.total = total
                        pbar.count = 0

                    pbar.update(current - pbar.count)
                except KeyError:
                    # not a progress line
                    pass

                # after pull, the digest is printed in status message
                # record it for below use
                if 'status' in line and 'Digest' in line['status']:
                    _, digest = line['status'].split(': ')

        log.debug(f'image {image} pulled successfully')

        # Reference might be provided as a digest. In this case
        # Docker will create a dangling image without any tag.
        # This is not desired and may leave garbage Dockers.
        # We are tagging it with a tag provided by the user.
        if tag and digest:
            log.debug(f'tagging {image} with {repository}:{tag}')
            api.tag(f'{image}', repository, tag)

    def rmi(self, repository: str, tag: str):
        """ Docker 'rmi -f' command. """

        image = f'{repository}:{tag}'
        log.debug(f'removing image {image}')

        self.client.images.remove(f'{image}', force=True)

        log.debug(f'image {image} removed successfully')

    def rm(self, repository: str, tag: str):
        """ Docker 'rm' command but removes by image and tag. """

        for container in self.client.containers.list(all=True):
            container_image = container.attrs['Config']['Image']
            if container_image == f'{repository}:{tag}':
                container.remove(force=True)
                log.debug(f'removed container {container.name}')

    def tag(self, src_img: str,
            src_tag: str,
            target_img: str,
            target_tag: str):
        """ Docker 'tag' command """

        src = f'{src_img}:{src_tag}'
        dst = f'{target_img}:{target_tag}'

        log.debug(f'tagging image {src} to {dst}')

        image = self.client.images.get(src)
        image.tag(target_img, target_tag, force=True)

        log.debug(f'image {src} to {dst} tagged successfully')

    def labels(self, repository: str, tag: str):
        """ Returns a list of labels associated with repository. """

        image = f'{repository}:{tag}'
        log.debug(f'inspecting image labels {image}')

        labels = self.client.images.get(image).labels

        log.debug(f'image {image} labels successfully: {labels}')
        return labels
