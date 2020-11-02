#!/usr/bin/env python
import contextlib
from unittest.mock import Mock, MagicMock

from sonic_package_manager.database import PackageEntry
from sonic_package_manager.errors import ManifestError
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.version import Version


def test_manifest_resolver_local(mock_registry_resolver, mock_docker_api):
    manifest_resolver = ManifestResolver(mock_docker_api, mock_registry_resolver)
    package_entry = PackageEntry(name='test',
                                 repository='test-repository',
                                 installed=True,
                                 version=Version(1, 2, 0))
    # it raises exception because mock manifest is not a valid manifest
    # but this is not a test objective, so just suppress the error.
    with contextlib.suppress(ManifestError):
        manifest_resolver.get_manifest(package_entry, '1.2.0')
    mock_docker_api.labels.assert_called_once_with('test-repository', '1.2.0')


def test_manifest_resolver_remote(mock_registry_resolver, mock_docker_api):
    manifest_resolver = ManifestResolver(mock_docker_api, mock_registry_resolver)
    mock_registry = MagicMock()
    mock_registry.manifest = MagicMock(return_value={'config': {'digest': 'some-digest'}})
    package_entry = PackageEntry(name='test',
                                 repository='test-repository',
                                 installed=False)

    def return_mock_registry(repository):
        return mock_registry

    mock_registry_resolver.get_registry_for = Mock(side_effect=return_mock_registry)
    # it raises exception because mock manifest is not a valid manifest
    # but this is not a test objective, so just suppress the error.
    with contextlib.suppress(ManifestError):
        manifest_resolver.get_manifest(package_entry, '1.2.0')
    mock_registry_resolver.get_registry_for.assert_called_once_with('test-repository')
    mock_registry.manifest.assert_called_once_with('test-repository', '1.2.0')
    mock_registry.blobs.assert_called_once_with('test-repository', 'some-digest')
    mock_docker_api.labels.assert_not_called()


def test_manifest_resolver_remote_different_tag(mock_registry_resolver, mock_docker_api):
    manifest_resolver = ManifestResolver(mock_docker_api, mock_registry_resolver)
    mock_registry = MagicMock()
    mock_registry.manifest = MagicMock(return_value={'config': {'digest': 'some-digest'}})
    package_entry = PackageEntry(name='test',
                                 repository='test-repository',
                                 installed=True,
                                 version=Version(1, 5, 0))

    def return_mock_registry(repository):
        return mock_registry

    mock_registry_resolver.get_registry_for = Mock(side_effect=return_mock_registry)
    # it raises exception because mock manifest is not a valid manifest
    # but this is not a test objective, so just suppress the error.
    with contextlib.suppress(ManifestError):
        manifest_resolver.get_manifest(package_entry, '1.2.0')
    mock_registry_resolver.get_registry_for.assert_called_once_with('test-repository')
    mock_registry.manifest.assert_called_once_with('test-repository', '1.2.0')
    mock_registry.blobs.assert_called_once_with('test-repository', 'some-digest')
    mock_docker_api.labels.assert_not_called()
