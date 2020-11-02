#!/usr/bin/env python
from unittest.mock import Mock, MagicMock

import pytest

from sonic_package_manager.database import PackageDatabase, PackageEntry
from sonic_package_manager.manager import DockerApi, PackageManager
from sonic_package_manager.manifest import Manifest
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.registry import RegistryResolver
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
def fake_manifest_resolver():
    class TestManifestResolver(ManifestResolver):
        def __init__(self):
            self.manifests = {
                ('database', '1.0.0'): Manifest.marshal({
                    'package': {
                        'version': '1.0.0',
                    },
                    'service': {
                        'name': 'database',
                    },
                }),
                ('swss', '1.0.0'): Manifest.marshal({
                    'package': {
                        'version': '1.0.0',
                    },
                    'service': {
                        'name': 'swss',
                    },
                }),
                ('test-package', '1.6.0'): Manifest.marshal({
                    'package': {
                        'version': '1.6.0',
                    },
                    'service': {
                        'name': 'test-package',
                    },
                }),
                ('test-package-2', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                    },
                    'service': {
                        'name': 'test-package-2',
                    },
                }),
                ('test-package-3', '1.5.0'): Manifest.marshal({
                    'package': {
                        'version': '1.5.0',
                    },
                    'service': {
                        'name': 'test-package-2',
                    },
                }),
            }

        def get_manifest(self, package_info: PackageEntry, ref: str) -> Manifest:
            return self.manifests[(package_info.name, ref)]

    yield TestManifestResolver()


@pytest.fixture
def mock_service_creator():
    return Mock()


@pytest.fixture
def package_manager(mock_docker_api,
                    mock_registry_resolver,
                    mock_service_creator,
                    fake_manifest_resolver,
                    fake_db):
    return PackageManager(mock_docker_api, mock_registry_resolver,
                          fake_db, fake_manifest_resolver,
                          mock_service_creator)


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
                                       description='SONiC Package Manager Test Package #2',
                                       default_reference='1.5.0',
                                       version=Version(1, 5, 0),
                                       installed=True, built_in=False),
    }

    class FakePackageDatabase(PackageDatabase):
        def commit(self):  # don't save anything to file.
            pass

    yield FakePackageDatabase(content)


# @pytest.fixture()
# def mock_package_library_fs(fs, mock_package_library):
#     database, library = mock_package_library
#     fs.create_file('/var/lib/sonic-package-manager/packages.json', content=json.dumps(database))
#     for package, manifest in library.items():
#         fs.create_file(f'/var/lib/sonic-package-manager/{package}/manifest.json', content=json.dumps(manifest))


@pytest.fixture
def anything():
    """ Fixture that returns Any object that can be used in
    assert_called_*_with to match any object passed. """

    class Any:
        def __eq__(self, other):
            return True

    yield Any()
