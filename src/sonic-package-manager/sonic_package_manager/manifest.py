#!/usr/bin/env python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable

from sonic_package_manager.constraint import PackageConstraint, VersionConstraint
from sonic_package_manager.errors import ManifestError
from sonic_package_manager.version import Version, VersionRange


class ManifestSchema:
    """ ManifestSchema class describes and provides marshalling
    and unmarshalling methods.
    """

    @dataclass
    class ManifestNode:
        """
        Base class for any manifest object.

        Attrs:
            key: String representing the key for this object.
        """

        key: str

        def marshal(self, value):
            """ Validates and returns a valid manifest dictionary.

            Args:
                value: input value to validate.
            Returns: valid manifest node.
            """

            raise NotImplementedError

        def unmarshal(self, value):
            """ Un-marshals the manifest to a dictionary.

            Args:
                value: input value to validate.
            Returns: valid manifest node.
            """

            raise NotImplementedError

    @dataclass
    class ManifestRoot(ManifestNode):
        items: List

        def marshal(self, value: Optional[dict]):
            result = {}
            if value is None:
                value = {}

            for item in self.items:
                next_value = value.get(item.key)
                result[item.key] = item.marshal(next_value)
            return result

        def unmarshal(self, value):
            return_value = {}
            for item in self.items:
                return_value[item.key] = item.unmarshal(value[item.key])
            return return_value

    @dataclass
    class ManifestField(ManifestNode):
        type: Callable
        default: Optional[Any] = None

        def marshal(self, value):
            if value is None:
                if self.default is not None:
                    return self.default
                raise ManifestError(f'{self.key} is a required field but it is missing')
            try:
                return_value = self.type(value)
            except Exception as err:
                raise ManifestError(f'Failed to convert {self.key}={value} to type {self.type.__name__}: {err}')
            return return_value

        def unmarshal(self, value):
            # return raw value for built-in types which can be serialized by JSONEncoder
            if self.type in (dict, list, tuple, str, int, float, bool):
                return value
            return str(value)

    @dataclass
    class ManifestArray(ManifestNode):
        type: Any

        def marshal(self, value):
            if value is None:
                return []

            def marshal(v):
                if isinstance(self.type, ManifestSchema.ManifestNode):
                    return self.type.marshal(v)
                else:
                    return self.type(v)

            return_value = []
            try:
                for item in value:
                    return_value.append(marshal(item))
            except Exception as err:
                raise ManifestError(f'Failed to convert {self.key}={value} to array: {err}')

            return return_value

        def unmarshal(self, value):
            def unmarshal(v):
                if isinstance(self.type, ManifestSchema.ManifestNode):
                    return self.type.unmarshal(v)
                else:
                    return str(v)
            return [unmarshal(item) for item in value]

    # TODO: add description for each field
    SCHEMA = ManifestRoot('root', [
        ManifestField('version', Version.parse, Version(1, 0, 0)),
        ManifestRoot('package', [
            ManifestField('version', Version.parse),
            ManifestField('name', str),
            ManifestField('base-os-constraint', VersionConstraint.parse, VersionRange()),
            ManifestArray('depends', PackageConstraint.parse),
            ManifestArray('breaks', PackageConstraint.parse),
            ManifestField('init-cfg', dict, dict()),
            ManifestField('changelog', dict, dict()),
            ManifestField('debug-dump', str, ''),
        ]),
        ManifestRoot('service', [
            ManifestField('name', str),
            ManifestArray('requires', str),
            ManifestArray('requisite', str),
            ManifestArray('wanted-by', str),
            ManifestArray('after', str),
            ManifestArray('before', str),
            ManifestArray('dependent', str),
            ManifestArray('dependent-of', str),
            ManifestField('post-start-action', str, ''),
            ManifestField('pre-shutdown-action', str, ''),
            ManifestField('asic-service', bool, False),
            ManifestField('host-service', bool, True),
            ManifestField('delayed', bool, False),
        ]),
        ManifestRoot('container', [
            ManifestField('privileged', bool, False),
            ManifestArray('volumes', str),
            ManifestArray('mounts', ManifestRoot('mounts', [
                ManifestField('source', str),
                ManifestField('target', str),
                ManifestField('type', str),
            ])),
            ManifestField('environment', dict, dict()),
        ]),
        ManifestArray('processes', ManifestRoot('processes', [
            ManifestField('critical', bool),
            ManifestField('name', str),
            ManifestField('command', str),
        ])),
        ManifestRoot('cli', [
            ManifestField('show', str, ''),
            ManifestField('config', str, ''),
            ManifestField('clear', str, '')
        ])
    ])


class Manifest(dict):
    """ Manifest object. """

    SCHEMA = ManifestSchema.SCHEMA
    LABEL_NAME = 'com.azure.sonic.manifest'

    @classmethod
    def marshal(cls, input_dict: dict):
        return Manifest(cls.SCHEMA.marshal(input_dict))

    def unmarshal(self) -> Dict:
        return self.SCHEMA.unmarshal(self)
