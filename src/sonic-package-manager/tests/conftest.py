#!/usr/bin/env python
import os
from unittest import mock
from unittest.mock import Mock, MagicMock

import pytest

from sonic_package_manager.database import PackageDatabase, PackageEntry
from sonic_package_manager.manager import DockerApi, PackageManager
from sonic_package_manager.manifest import Manifest
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.registry import RegistryResolver
from sonic_package_manager.service_creator.creator import (
    TEMPLATES_PATH, SERVICE_FILE_TEMPLATE, TIMER_UNIT_TEMPLATE,
    SERVICE_MGMT_SCRIPT_TEMPLATE, DOCKER_CTL_SCRIPT_TEMPLATE, MONIT_CONF_TEMPLATE, SERVICE_MGMT_SCRIPT_LOCATION,
    SYSTEMD_LOCATION, ETC_SONIC_PATH, MONIT_CONF_LOCATION, DOCKER_CTL_SCRIPT_LOCATION, DEBUG_DUMP_SCRIPT_TEMPLATE
)
from sonic_package_manager.version import Version


@pytest.fixture
def mock_docker_api():
    yield MagicMock(DockerApi)


@pytest.fixture
def mock_registry_resolver():
    yield Mock(RegistryResolver)


@pytest.fixture
def mock_manifest_resolver():
    yield Mock(ManifestResolver)


@pytest.fixture
def mock_feature_registry():
    yield MagicMock()


@pytest.fixture
def mock_service_creator():
    yield Mock()


@pytest.fixture
def mock_sonic_db():
    yield Mock()


@pytest.fixture
def fake_manifest_resolver():
    class FakeManifestResolver:
        def __init__(self):
            self.manifests = {
                ('database', 'latest'): Manifest.marshal({
                    'package': {
                        'version': '1.0.0',
                        'name': 'database',
                    },
                    'service': {
                        'name': 'database',
                    },
                }),
                ('swss', 'latest'): Manifest.marshal({
                    'package': {
                        'version': '1.0.0',
                        'name': 'swss',
                    },
                    'service': {
                        'name': 'swss',
                    },
                }),
                ('swss', '1.0.0'): Manifest.marshal({
                    'package': {
                        'version': '1.0.0',
                        'name': 'swss',
                    },
                    'service': {
                        'name': 'swss',
                    },
                }),
                ('test-package', '1.6.0'): Manifest.marshal({
                    'package': {
                        'version': '1.6.0',
                        'name': 'test-package',
                    },
                    'service': {
                        'name': 'test-package',
                    },
                }),
                ('test-package-2', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-2',
                    },
                    'service': {
                        'name': 'test-package-2',
                    },
                }),
                ('test-package-3', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-3',
                    },
                    'service': {
                        'name': 'test-package-3',
                    },
                }),
                ('test-package-3', 'latest'): Manifest.marshal({
                    'package': {
                        'version': '1.6.0',
                        'name': 'test-package-3',
                    },
                    'service': {
                        'name': 'test-package-3',
                    },
                }),
                ('test-package-4', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-4',
                    },
                    'service': {
                        'name': 'test-package-4',
                    },
                }),
                ('test-package-5', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-5',
                    },
                    'service': {
                        'name': 'test-package-5',
                    },
                }),
                ('test-package-5', '1.9.0'): Manifest.marshal({
                    'package': {
                        'version': '1.9.0',
                        'name': 'test-package-5',
                    },
                    'service': {
                        'name': 'test-package-5',
                    },
                }),
                ('test-package-6', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-6',
                    },
                    'service': {
                        'name': 'test-package-6',
                    },
                }),
                ('test-package-6', 'latest'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                        'name': 'test-package-6',
                    },
                    'service': {
                        'name': 'test-package-6',
                    },
                }),
                ('test-package-6', '2.0.0'): Manifest.marshal({
                    'package': {
                        'version': '2.0.0',
                        'name': 'test-package-6',
                    },
                    'service': {
                        'name': 'test-package-6',
                    },
                }),
            }

        def get_manifest(self, package_info: PackageEntry, ref: str = None) -> Manifest:
            if ref is None:
                ref = 'latest'
            return self.manifests[(package_info.name, ref)]

        def get_manifest_from_image_tarball(self, filepath: str) -> Manifest:
            name, ref = os.path.basename(filepath).split(':')
            return self.manifests[(name, ref)]

    yield FakeManifestResolver()


@pytest.fixture
def fake_device_info():
    class FakeDeviceInfo:
        def is_multi_npu(self):
            return False

        def get_num_npus(self):
            return 1

        def get_sonic_version_info(self):
            return {
                'base_os_compatibility_version': '1.0.0'
            }

    yield FakeDeviceInfo()


@pytest.fixture
def fake_db(mock_docker_api, mock_registry_resolver):
    content = {
        'database': PackageEntry(name='database',
                                 repository='docker-database',
                                 description='SONiC database service',
                                 default_reference='1.0.0',
                                 version=Version(1, 0, 0),
                                 installed=True, built_in=True),
        'swss': PackageEntry(name='swss',
                             repository='docker-orchagent',
                             description='SONiC switch state service',
                             default_reference='1.0.0',
                             version=Version(1, 0, 0),
                             installed=True, built_in=True),
        'test-package': PackageEntry(name='test-package',
                                     repository='Azure/docker-test',
                                     description='SONiC Package Manager Test Package',
                                     default_reference='1.6.0',
                                     installed=False, built_in=False),
        'test-package-2': PackageEntry(name='test-package-2',
                                       repository='Azure/docker-test-2',
                                       description='SONiC Package Manager Test Package #2',
                                       default_reference='1.5.0',
                                       installed=False, built_in=False),
        'test-package-3': PackageEntry(name='test-package-3',
                                       repository='Azure/docker-test-3',
                                       description='SONiC Package Manager Test Package #3',
                                       default_reference='1.5.0',
                                       version=Version(1, 5, 0),
                                       installed=True, built_in=False),
        'test-package-5': PackageEntry(name='test-package-5',
                                       repository='Azure/docker-test-5',
                                       description='SONiC Package Manager Test Package #5',
                                       default_reference='1.9.0',
                                       version=Version(1, 9, 0),
                                       installed=False, built_in=False),
        'test-package-6': PackageEntry(name='test-package-6',
                                       repository='Azure/docker-test-6',
                                       description='SONiC Package Manager Test Package #6',
                                       default_reference='1.5.0',
                                       installed=False, built_in=False),
    }

    yield PackageDatabase(content)


@pytest.fixture
def fake_db_for_migration(mock_docker_api, mock_registry_resolver):
    content = {
        'database': PackageEntry(name='database',
                                 repository='docker-database',
                                 description='SONiC database service',
                                 default_reference='1.0.0',
                                 version=Version(1, 0, 0),
                                 installed=True, built_in=True),
        'swss': PackageEntry(name='swss',
                             repository='docker-orchagent',
                             description='SONiC switch state service',
                             default_reference='1.0.0',
                             version=Version(1, 0, 0),
                             installed=True, built_in=True),
        'test-package': PackageEntry(name='test-package',
                                     repository='Azure/docker-test',
                                     description='SONiC Package Manager Test Package',
                                     default_reference='1.6.0',
                                     installed=False, built_in=False),
        'test-package-2': PackageEntry(name='test-package-2',
                                       repository='Azure/docker-test-2',
                                       description='SONiC Package Manager Test Package #2',
                                       default_reference='2.0.0',
                                       installed=False, built_in=False),
        'test-package-3': PackageEntry(name='test-package-3',
                                       repository='Azure/docker-test-3',
                                       description='SONiC Package Manager Test Package #2',
                                       default_reference='1.6.0',
                                       version=Version(1, 6, 0),
                                       installed=True, built_in=False),
        'test-package-4': PackageEntry(name='test-package-4',
                                       repository='Azure/docker-test-4',
                                       description='SONiC Package Manager Test Package #4',
                                       default_reference='1.5.0',
                                       version=Version(1, 5, 0),
                                       installed=True, built_in=False),
        'test-package-5': PackageEntry(name='test-package-5',
                                       repository='Azure/docker-test-5',
                                       description='SONiC Package Manager Test Package #5',
                                       default_reference='1.5.0',
                                       version=Version(1, 5, 0),
                                       installed=True, built_in=False),
        'test-package-6': PackageEntry(name='test-package-6',
                                       repository='Azure/docker-test-6',
                                       description='SONiC Package Manager Test Package #6',
                                       default_reference='1.5.0',
                                       version=Version(2, 0, 0),
                                       installed=True, built_in=False),
    }

    yield PackageDatabase(content)


@pytest.fixture
def sonic_fs(fs):
    fs.create_file('/proc/1/root')
    fs.create_dir(ETC_SONIC_PATH)
    fs.create_dir(SYSTEMD_LOCATION)
    fs.create_dir(DOCKER_CTL_SCRIPT_LOCATION)
    fs.create_dir(SERVICE_MGMT_SCRIPT_LOCATION)
    fs.create_dir(MONIT_CONF_LOCATION)
    fs.create_file(os.path.join(TEMPLATES_PATH, SERVICE_FILE_TEMPLATE))
    fs.create_file(os.path.join(TEMPLATES_PATH, TIMER_UNIT_TEMPLATE))
    fs.create_file(os.path.join(TEMPLATES_PATH, SERVICE_MGMT_SCRIPT_TEMPLATE))
    fs.create_file(os.path.join(TEMPLATES_PATH, DOCKER_CTL_SCRIPT_TEMPLATE))
    fs.create_file(os.path.join(TEMPLATES_PATH, MONIT_CONF_TEMPLATE))
    fs.create_file(os.path.join(TEMPLATES_PATH, DEBUG_DUMP_SCRIPT_TEMPLATE))
    yield fs


@pytest.fixture(autouse=True)
def patch_pkgutil():
    with mock.patch('pkgutil.get_loader'):
        yield


@pytest.fixture
def package_manager(mock_docker_api,
                    mock_registry_resolver,
                    mock_service_creator,
                    fake_manifest_resolver,
                    fake_db,
                    fake_device_info):
    yield PackageManager(mock_docker_api, mock_registry_resolver,
                         fake_db, fake_manifest_resolver,
                         mock_service_creator,
                         fake_device_info)


@pytest.fixture
def anything():
    """ Fixture that returns Any object that can be used in
    assert_called_*_with to match any object passed. """

    class Any:
        def __eq__(self, other):
            return True

    yield Any()
