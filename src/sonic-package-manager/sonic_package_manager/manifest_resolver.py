#!/usr/bin/env python
import json

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

    def get_manifest(self, package_info: PackageEntry, ref: str) -> Manifest:
        """ Gets the package manifest.
        Args:
            package_info: PackageEntry object
            ref: Reference to resolve, either tag or digest
        Returns:
            Manifest object.
        """
        name = package_info.name
        version = package_info.version
        installed = package_info.installed

        # If the package is installed or the requested
        # reference is not None read it from remote.
        if installed and str(version) == ref:
            log.debug(f'requesting manifest from local for {name} {ref}')
            manifest = self.get_manifest_local(package_info)
        else:
            log.debug(f'requesting manifest from remote for {name} {ref}')
            manifest = self.get_manifest_remote(package_info, ref)

        log.debug(f'manifest for package {name} {ref}: {manifest}')

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

        repo = package.repository
        version = str(package.version)

        labels = self.docker.labels(repo, version)

        try:
            return self.get_manifest_from_labels(labels)
        except (KeyError, TypeError, ValueError):
            raise ManifestError(f'No manifest defined for {repo}:{version}')

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

        try:
            return self.get_manifest_from_labels(labels)
        except (KeyError, TypeError, ValueError):
            raise ManifestError(f'No manifest defined for {repo}:{ref}')

    def get_manifest_from_labels(self, labels) -> Manifest:
        manifest_dict = labels[Manifest.LABEL_NAME]
        return Manifest.marshal(json.loads(manifest_dict))
