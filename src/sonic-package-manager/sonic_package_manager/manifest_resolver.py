#!/usr/bin/env python
import json
import tarfile
from typing import Optional

from sonic_package_manager.database import PackageEntry
from sonic_package_manager.errors import ManifestError
from sonic_package_manager.logger import log
from sonic_package_manager.manifest import Manifest


class ManifestResolver:
    """ Resolve manifest for package. It might resolve the package
    manifest from local docker image in case package is installed or
    access Docker Registry if package is not installed."""

    def __init__(self, docker, registry_resolver):
        self.docker = docker
        self.registry_resolver = registry_resolver

    def get_manifest(self, package: PackageEntry, ref: Optional[str] = None) -> Manifest:
        """ Gets the package manifest.
        Args:
            package: PackageEntry object
            ref: Reference to resolve, either tag or digest
        Returns:
            Manifest object.
        """

        if package.installed:
            log.debug(f'requesting manifest from local for {package.name}')
            manifest = self.get_manifest_local(package)
        else:
            log.debug(f'requesting manifest from remote for {package.name} {ref}')
            manifest = self.get_manifest_remote(package, ref)

        log.debug(f'manifest for package {package.name} {ref}: {manifest}')

        return manifest

    def get_manifest_local(self, package: PackageEntry) -> Manifest:
        """ Gets the package manifest from locally installed docker image.
        Args:
            package: PackageEntry object
        Returns:
            Package manifest
        Raises:
            ManifestError
        """

        repotag = f'{package.repository}:latest'
        labels = self.docker.labels(repotag)

        return self.get_manifest_from_labels(labels)

    def get_manifest_remote(self, package: PackageEntry, ref: str) -> Manifest:
        """ Gets the package manifest from remote registry.
        Args:
            package: PackageEntry object
            ref: Reference to resolve, either tag or digest
        Returns:
            Package manifest
        Raises:
            ManifestError
        """

        repo = package.repository
        registry = self.registry_resolver.get_registry_for(repo)

        manifest = registry.manifest(repo, ref)
        digest = manifest['config']['digest']

        blob = registry.blobs(repo, digest)
        labels = blob['config']['Labels']

        return self.get_manifest_from_labels(labels)

    def get_manifest_from_image_tarball(self, image_path: str) -> Manifest:
        with tarfile.open(image_path) as image:
            manifest = json.loads(image.extractfile('manifest.json').read())

            blob = manifest[0]['Config']
            image_config = json.loads(image.extractfile(blob).read())
            labels = image_config['config']['Labels']

            return self.get_manifest_from_labels(labels)

    @staticmethod
    def get_manifest_from_labels(labels) -> Manifest:
        if labels is None:
            raise ManifestError('No manifest found in image labels')

        try:
            manifest_string = labels[Manifest.LABEL_NAME]
        except KeyError:
            raise ManifestError('No manifest found in image labels')

        try:
            manifest_dict = json.loads(manifest_string)
        except (ValueError, TypeError) as err:
            raise ManifestError(f'Failed to parse manifest JSON: {err}')

        return Manifest.marshal(manifest_dict)
