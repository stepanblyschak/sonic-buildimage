#!/usr/bin/env python
from unittest.mock import Mock, call

import pytest

from sonic_package_manager.errors import *
from sonic_package_manager.version import Version


def test_installation_not_installed(package_manager):
    package_manager.install('test-package')


def test_installation_already_installed(package_manager):
    with pytest.raises(PackageInstallationError,
                       match='swss is already installed'):
        package_manager.install('swss')


def test_installation_dependencies(package_manager, fake_manifest_resolver, mock_docker_api):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['depends'] = ['swss^2.0.0']
    with pytest.raises(PackageInstallationError,
                       match='Package test-package requires '
                             'swss>=2.0.0,<3.0.0 but version 1.0.0 is installed'):
        package_manager.install('test-package')


def test_installation_dependencies_missing_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['depends'] = ['missing-package>=1.0.0']
    with pytest.raises(PackageInstallationError,
                       match='Package test-package requires '
                             'missing-package>=1.0.0 but it is not installed'):
        package_manager.install('test-package')


def test_installation_dependencies_satisfied(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['depends'] = ['database>=1.0.0', 'swss>=1.0.0']
    package_manager.install('test-package')


def test_installation_breaks(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['breaks'] = ['swss^1.0.0']
    with pytest.raises(PackageInstallationError,
                       match='Package test-package conflicts with '
                             'swss>=1.0.0,<2.0.0 but version 1.0.0 is installed'):
        package_manager.install('test-package')


def test_installation_breaks_missing_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['breaks'] = ['missing-package^1.0.0']
    package_manager.install('test-package')


def test_installation_breaks_not_installed_package(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['breaks'] = ['test-package-2^1.0.0']
    package_manager.install('test-package')


def test_installation_base_os_constraint(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['base-os-constraint'] = '>=2.0.0'
    with pytest.raises(PackageSonicRequirementError,
                       match='Package test-package requires '
                             'base OS compatibility version >=2.0.0 '
                             'while the installed version is 1.0.0'):
        package_manager.install('test-package')


def test_installation_base_os_constraint_satisfied(package_manager, fake_manifest_resolver):
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    manifest['package']['base-os-constraint'] = '^1.0.0'
    package_manager.install('test-package')


def test_installation(package_manager, mock_docker_api, anything):
    package_manager.install('test-package')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test', '1.6.0')


def test_installation_using_reference(package_manager,
                                      fake_manifest_resolver,
                                      mock_docker_api,
                                      anything):
    ref = 'sha256:9780f6d83e45878749497a6297ed9906c19ee0cc48cc88dc63827564bb8768fd'
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    fake_manifest_resolver.manifests['Azure/docker-test'][ref] = {'manifest': manifest}

    package_manager.install(f'test-package@{ref}')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test', f'{ref}')


def test_manager_installation_tag(package_manager,
                                  mock_docker_api,
                                  anything):
    package_manager.install(f'test-package==1.6.0')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test', '1.6.0')


def test_installation_from_file(package_manager, mock_docker_api, sonic_fs):
    sonic_fs.create_file('Azure/docker-test:1.6.0')
    package_manager.install(tarball='Azure/docker-test:1.6.0')
    mock_docker_api.load.assert_called_once_with('Azure/docker-test:1.6.0')


def test_installation_from_registry(package_manager, mock_docker_api):
    package_manager.install(repotag='Azure/docker-test:1.6.0')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test', '1.6.0')


def test_installation_from_registry_using_digest(package_manager, mock_docker_api, fake_manifest_resolver):
    ref = 'sha256:9780f6d83e45878749497a6297ed9906c19ee0cc48cc88dc63827564bb8768fd'
    manifest = fake_manifest_resolver.manifests['Azure/docker-test']['1.6.0']['manifest']
    fake_manifest_resolver.manifests['Azure/docker-test'][ref] = {'manifest': manifest}

    ref = 'sha256:9780f6d83e45878749497a6297ed9906c19ee0cc48cc88dc63827564bb8768fd'
    package_manager.install(repotag=f'Azure/docker-test@{ref}')
    mock_docker_api.pull.assert_called_once_with('Azure/docker-test', ref)


def test_installation_from_file_known_package(package_manager, fake_db, sonic_fs):
    repository = fake_db.get_package('test-package').repository
    sonic_fs.create_file('Azure/docker-test:1.6.0')
    package_manager.install(tarball='Azure/docker-test:1.6.0')
    # locally installed package does not override already known package repository
    assert repository == fake_db.get_package('test-package').repository


def test_installation_from_file_unknown_package(package_manager, fake_db, sonic_fs):
    assert not fake_db.has_package('test-package-4')
    sonic_fs.create_file('Azure/docker-test-4:1.5.0')
    package_manager.install(tarball='Azure/docker-test-4:1.5.0')
    assert fake_db.has_package('test-package-4')


def test_upgrade_from_file_known_package(package_manager, fake_db, sonic_fs):
    repository = fake_db.get_package('test-package-6').repository
    # install older version from repository
    package_manager.install('test-package-6==1.5.0')
    # upgrade from file
    sonic_fs.create_file('Azure/docker-test-6:2.0.0')
    package_manager.upgrade(tarball='Azure/docker-test-6:2.0.0')
    # locally installed package does not override already known package repository
    assert repository == fake_db.get_package('test-package-6').repository


def test_installation_non_default_owner(package_manager, anything, mock_service_creator):
    package_manager.install('test-package', default_owner='kube')
    mock_service_creator.create.assert_called_once_with(anything, state='disabled', owner='kube')


def test_installation_enabled(package_manager, anything, mock_service_creator):
    package_manager.install('test-package', enable=True)
    mock_service_creator.create.assert_called_once_with(anything, state='enabled', owner='local')


def test_installation_fault(package_manager, mock_docker_api, mock_service_creator):
    # make 'tag' to fail
    mock_service_creator.create = Mock(side_effect=Exception('Failed to create service'))
    # 'rmi' is called on rollback
    mock_docker_api.rmi = Mock(side_effect=Exception('Failed to remove image'))
    # assert that the rollback does not hide the original failure.
    with pytest.raises(Exception, match='Failed to create service'):
        package_manager.install('test-package')
    mock_docker_api.rmi.assert_called_once()


def test_installation_package_with_description(package_manager, fake_manifest_resolver):
    package_entry = package_manager.database.get_package('test-package')
    description = package_entry.description
    references = fake_manifest_resolver.manifests[package_entry.repository]
    manifest = references[package_entry.default_reference]['manifest']
    new_description = description + ' changed description '
    manifest['package']['description'] = new_description
    package_manager.install('test-package')
    package_entry = package_manager.database.get_package('test-package')
    description = package_entry.description
    assert description == new_description


def test_manager_installation_version_range(package_manager):
    with pytest.raises(PackageManagerError,
                       match='Can only install specific version. '
                             'Use only following expression "test-package==<version>" '
                             'to install specific version'):
        package_manager.install(f'test-package>=1.6.0')


def test_manager_upgrade(package_manager, sonic_fs):
    package_manager.install('test-package-6==1.5.0')
    package_manager.upgrade('test-package-6==2.0.0')

    upgraded_package = package_manager.get_installed_package('test-package-6')
    assert upgraded_package.entry.version == Version(2, 0, 0)


def test_manager_migration(package_manager, fake_db_for_migration):
    package_manager.install = Mock()
    package_manager.upgrade = Mock()
    package_manager.migrate_packages(fake_db_for_migration)

    # test-package-3 was installed but there is a newer version installed
    # in fake_db_for_migration, asserting for upgrade
    package_manager.upgrade.assert_has_calls([call('test-package-3==1.6.0')], any_order=True)

    package_manager.install.assert_has_calls([
        # test-package-4 was not present in DB at all, but it is present and installed in
        # fake_db_for_migration, thus asserting that it is going to be installed.
        call('test-package-4==1.5.0'),
        # test-package-5 1.5.0 was installed in fake_db_for_migration but the default
        # in current db is 1.9.0, assert that migration will install the newer version.
        call('test-package-5==1.9.0'),
        # test-package-6 2.0.0 was installed in fake_db_for_migration but the default
        # in current db is 1.5.0, assert that migration will install the newer version.
        call('test-package-6==2.0.0')],
        any_order=True
    )
