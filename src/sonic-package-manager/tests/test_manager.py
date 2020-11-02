#!/usr/bin/env python

import pytest

from sonic_package_manager.constraint import PackageConstraint
from sonic_package_manager.errors import (
    PackageInstallationError,
    PackageSonicRequirementError,
    PackageManagerError
)
from sonic_package_manager.version import Version, VersionRange


def test_installation_not_installed(package_manager):
    package_manager.install('test-package')


def test_installation_already_installed(package_manager):
    with pytest.raises(PackageInstallationError,
                       match='swss is already installed'):
        package_manager.install('swss')


def test_installation_dependencies(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['depends'] = [PackageConstraint.parse('swss^2.0.0')]
    with pytest.raises(PackageInstallationError,
                       match='Package test-package requires '
                             'swss >=2.0.0,<3.0.0 but version 1.0.0 is installed'):
        package_manager.install('test-package')


def test_installation_dependencies_missing_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['depends'] = [PackageConstraint.parse('missing-package>=1.0.0')]
    with pytest.raises(PackageInstallationError,
                       match='Package test-package requires '
                             'missing-package >=1.0.0 but it is not installed'):
        package_manager.install('test-package')


def test_installation_dependencies_satisfied(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['depends'] = [
        PackageConstraint.parse('database>=1.0.0'),
        PackageConstraint.parse('swss>=1.0.0'),
    ]
    package_manager.install('test-package')


def test_installation_breaks(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['breaks'] = [PackageConstraint.parse('swss^1.0.0')]
    with pytest.raises(PackageInstallationError,
                       match='Package test-package conflicts with '
                             'swss >=1.0.0,<2.0.0 but version 1.0.0 is installed'):
        package_manager.install('test-package')


def test_installation_breaks_missing_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['breaks'] = [PackageConstraint.parse('missing-package^1.0.0')]
    package_manager.install('test-package')


def test_installation_breaks_not_installed_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['breaks'] = [PackageConstraint.parse('test-package-2^1.0.0')]
    package_manager.install('test-package')


def test_installation_base_os_constraint(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['base-os-constraint'] = VersionRange(min=Version(2, 0, 0), include_min=True)
    with pytest.raises(PackageSonicRequirementError,
                       match='Package test-package requires '
                             'base OS compatibility version >=2.0.0 '
                             'while the installed version is 1.0.0'):
        package_manager.install('test-package')


def test_installation_base_os_constraint_satisfied(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    manifest['package']['base-os-constraint'] = VersionRange(min=Version(1, 0, 0),
                                                             max=Version(2, 0, 0),
                                                             include_min=True)
    package_manager.install('test-package')


def test_installation(package_manager, mock_docker_api, anything):
    package_manager.install('test-package')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test',
                                                 '1.6.0',
                                                 Version.parse('1.6.0'),
                                                 anything)
    mock_docker_api.tag.assert_called_once_with('Azure/docker-test',
                                                Version.parse('1.6.0'),
                                                'Azure/docker-test',
                                                'latest')


def test_installation_using_reference(package_manager,
                                      fake_manifest_resolver,
                                      mock_docker_api,
                                      anything):
    ref = 'sha256:9780f6d83e45878749497a6297ed9906c19ee0cc48cc88dc63827564bb8768fd'
    manifest = fake_manifest_resolver.manifests[('test-package', '1.6.0')]
    fake_manifest_resolver.manifests[('test-package', ref)] = manifest

    package_manager.install(f'test-package@{ref}')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test',
                                                 f'{ref}',
                                                 Version.parse('1.6.0'),
                                                 anything)
    mock_docker_api.tag.assert_called_once_with('Azure/docker-test',
                                                Version.parse('1.6.0'),
                                                'Azure/docker-test',
                                                'latest')


def test_manager_installation_tag(package_manager,
                                  mock_docker_api,
                                  anything):
    package_manager.install(f'test-package==1.6.0')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test',
                                                 '1.6.0',
                                                 Version.parse('1.6.0'),
                                                 anything)
    mock_docker_api.tag.assert_called_once_with('Azure/docker-test',
                                                Version.parse('1.6.0'),
                                                'Azure/docker-test',
                                                'latest')


def test_manager_installation_version_range(package_manager):
    with pytest.raises(PackageManagerError,
                       match='Can only install specific version. '
                             'Use only following expression "test-package==<version>" '
                             'to install specific version'):
        package_manager.install(f'test-package>=1.6.0')