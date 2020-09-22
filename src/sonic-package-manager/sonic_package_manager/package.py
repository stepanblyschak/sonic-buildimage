#!/usr/bin/env python

import os
import json
import yaml
import docker


class Package:
    ''' SONiC package interface '''

    def __init__(self, name, package_data, metadata_path):
        ''' Create an instance of Pacakge.

        Args:
            name (str): Package name.
            package_data (dict): Database information about this package.
            metadata_path (str): Path to package metadata.
        Returns:
            None.
        '''

        self._name = name
        self._package_data = package_data
        self._metadata_path = metadata_path

    def get_name(self):
        ''' Package name. '''

        return self._name

    def get_repository(self):
        ''' Package repository. '''

        return self._package_data["repository"]

    def get_default_version(self):
        ''' Package default version. '''

        return self._package_data.get("default-version", None)

    def get_description(self):
        ''' Package description. '''

        return self._package_data.get("description", "N/A")

    def is_builtin(self):
        ''' Tell if a package is an essential package. '''

        return self._package_data.get("essential", False)

    def is_installed(self):
        ''' Tell if a package is installed. '''

        # TODO: change to read the database info about package
        client = docker.from_env()
        images = client.images.list()
        repository = self.get_repository()
        for image in images:
            for tag in image.tags:
                if tag.rsplit(':', 1)[0] == self.get_repository():
                    return True
        return False

    def installed_version(self):
        ''' Return an installed version as string.
        Returns None if the pacakge is not installed.
        '''

        client = docker.from_env()
        images = client.images.list()
        repository = self.get_repository()
        for image in images:
            for tag in image.tags:
                if tag.split(':')[-1] == 'latest':
                    continue
                return tag.split(':')[-1]
        return None

    def status(self):
        ''' Tell the package status - Installed/Not Installed/Built-In. '''

        if self.is_builtin():
            return "Built-In"
        elif self.is_installed():
            return "Installed"
        else:
            return "Not Installed"

    def get_manifest(self):
        ''' Returns the manifest content. '''

        base_path = self._metadata_path
        manifests = [
            os.path.join(base_path, 'manifest.json'),
            os.path.join(base_path, 'manifest.yml'),
            os.path.join(base_path, 'manifest.yaml'),
        ]
        for manifest in manifests:
            try:
                with open(manifest) as stream:
                    if manifest.endswith('json'):
                        return json.load(stream)
                    else:
                        return yaml.safe_load(stream)
            except IOError:
                continue
