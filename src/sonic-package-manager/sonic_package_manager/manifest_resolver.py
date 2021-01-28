#!/usr/bin/env python
import json
import tarfile
from typing import Dict

from sonic_package_manager.errors import ManifestError
from sonic_package_manager.manifest import Manifest


class ManifestResolver:
    """ Resolve manifest for package from different sources. """

    LABEL_NAME = 'com.azure.sonic.manifest'

    def __init__(self, docker, registry_resolver):
        self.docker = docker
        self.registry_resolver = registry_resolver

    def from_local(self, image: str) -> Manifest:
        """ Reads manifest from locally installed docker image.

        Args:
            image: Docker image ID
        Returns:
            Manifest
        Raises:
            ManifestError
        """

        labels = self.docker.labels(image)
        return self.from_labels(labels)

    def from_registry(self,
                      repository: str,
                      reference: str) -> Manifest:
        """ Reads manifest from remote registry.

        Args:
            repository: Repository to pull image from
            reference: Reference, either tag or digest
        Returns:
            Manifest
        Raises:
            ManifestError
        """

        registry = self.registry_resolver.get_registry_for(repository)

        manifest = registry.manifest(repository, reference)
        digest = manifest['config']['digest']

        blob = registry.blobs(repository, digest)
        labels = blob['config']['Labels']

        return self.from_labels(labels)

    def from_tarball(self, image_path: str) -> Manifest:
        """ Reads manifest image tarball.
        Args:
            image_path: Path to image tarball.
        Returns:
            Manifest
        Raises:
            ManifestError
        """

        with tarfile.open(image_path) as image:
            manifest = json.loads(image.extractfile('manifest.json').read())

            blob = manifest[0]['Config']
            image_config = json.loads(image.extractfile(blob).read())
            labels = image_config['config']['Labels']

            return self.from_labels(labels)

    @classmethod
    def from_labels(cls, labels: Dict[str, str]) -> Manifest:
        """ Get manifest from image labels.

        Args:
            labels: key, value string pairs
        Returns:
            Manifest
        Raises:
            ManifestError
        """

        if labels is None:
            raise ManifestError('No manifest found in image labels')

        try:
            manifest_string = labels[cls.LABEL_NAME]
        except KeyError:
            raise ManifestError('No manifest found in image labels')

        try:
            manifest_dict = json.loads(manifest_string)
        except (ValueError, TypeError) as err:
            raise ManifestError(f'Failed to parse manifest JSON: {err}')

        return Manifest.marshal(manifest_dict)
