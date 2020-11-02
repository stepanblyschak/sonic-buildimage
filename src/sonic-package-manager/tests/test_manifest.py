#!/usr/bin/env python

import pytest

from sonic_package_manager.manifest import Manifest, ManifestError
from sonic_package_manager.version import VersionRange


def test_manifest_v1_defaults():
    manifest = Manifest.marshal({'package': {'version': '1.0.0'}, 'service': {'name': 'test'}})
    assert manifest['package']['depends'] == []
    assert manifest['package']['breaks'] == []
    assert manifest['package']['base-os-constraint'] == VersionRange()
    assert not manifest['service']['asic-service']
    assert manifest['service']['host-service']


def test_manifest_v1_empty():
    with pytest.raises(ManifestError,
                       match='version is a required field but it is missing'):
        Manifest.marshal({})


def test_manifest_v1_invalid_version():
    with pytest.raises(ManifestError,
                       match='Failed to convert version=abc to type parse: Unable to parse "abc"'):
        Manifest.marshal({'package': {'version': 'abc'}, 'service': {'name': 'test'}})


def test_manifest_v1_invalid_package_constraint():
    with pytest.raises(ManifestError):
        Manifest.marshal({'package': {'version': '1.0.0', 'depends': ['swss>a']}, 'service': {'name': 'test'}})


def test_manifest_v1_service_spec():
    manifest = Manifest.marshal({'package': {'version': '1.0.0'}, 'service': {'name': 'test', 'asic-service': True}})
    assert manifest['service']['asic-service']


def test_manifest_mounts():
    manifest = Manifest.marshal({'version': '1.0.0', 'package': {'version': '1.0.0'},
                                 'service': {'name': 'cpu-report'},
                                 'container': {'privileged': True,
                                               'mounts': [{'source':'a', 'target': 'b', 'type': 'bind'}]}})
    assert manifest['container']['mounts'][0]['source'] == 'a'
    assert manifest['container']['mounts'][0]['target'] == 'b'
    assert manifest['container']['mounts'][0]['type'] == 'bind'
