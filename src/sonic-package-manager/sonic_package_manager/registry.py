#!/usr/bin/env python
import json
import time
from dataclasses import dataclass
from typing import List, Dict

from docker_image import reference

import requests

from sonic_package_manager.errors import PackageManagerError
from sonic_package_manager.logger import log


class AuthService:
    @dataclass
    class Token:
        value: str
        expires: int

    def __init__(self, host, service):
        self._host = host
        self._service = service
        self._tokens = {}

    def get_token(self, repository: str, action: str = 'pull'):
        log.debug(f'getting authentication token for {repository}:{action}')

        scope = f'scope=repository:{repository}:{action}'

        # Try to get the token from cached tokens if cached token did not expire
        if scope in self._tokens and self._tokens[scope].expires > time.time():
            token = self._tokens[scope]
            log.debug(f'using cached authentication token for {repository}:{action}: {token}')
            return token.value

        response = requests.get(f'{self._host}/token?{scope}&service={self._service}')
        if response.status_code != requests.codes.ok:
            raise RuntimeError(f'Failed to retrieve token for {repository} action {action}')

        content = json.loads(response.content)
        token = AuthService.Token(content['token'], time.time() + content['expires_in'])

        log.debug(f'authentication token for {repository}:{action}: {token}')
        self._tokens[scope] = token
        return token.value


class Registry:
    def __init__(self, host: str, auth=None):
        self.url = host
        self.auth = auth

        log.debug(f'initialized registry object with {self.url} {self.auth}')

    def _get_headers(self, repository: str):
        _, repository = reference.Reference.split_docker_domain(repository)
        headers = {}
        if self.auth:
            token = self.auth.get_token(repository)
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def tags(self, repository: str) -> List[str]:
        log.debug(f'getting tags for {repository}')

        _, repository = reference.Reference.split_docker_domain(repository)
        headers = self._get_headers(repository)
        headers['Accept'] = 'application/json'
        response = requests.get(f'{self.url}/v2/{repository}/tags/list',
                                headers=self._get_headers(repository))
        if response.status_code != requests.codes.ok:
            raise PackageManagerError(f'Failed to retrieve tags from {repository}: '
                                      f'response: {response.status_code}, content: {response.content}')

        content = json.loads(response.content)
        log.debug(f'tags list api response: f{content}')

        return content['tags']

    def manifest(self, repository: str, ref: str) -> Dict:
        log.debug(f'getting manifest for {repository}:{ref}')

        _, repository = reference.Reference.split_docker_domain(repository)
        headers = self._get_headers(repository)
        headers['Accept'] = 'application/vnd.docker.distribution.manifest.v2+json'
        response = requests.get(f'{self.url}/v2/{repository}/manifests/{ref}',
                                headers=headers)

        if response.status_code != requests.codes.ok:
            raise PackageManagerError(f'Failed to retrieve manifest for {repository}:{ref}: '
                                      f'response: {response.status_code}, content: {response.content}')

        content = json.loads(response.content)
        log.debug(f'manifest content for {repository}:{ref}: {content}')

        return content

    def blobs(self, repository: str, digest: str):
        log.debug(f'retrieving blob for {repository}:{digest}')

        _, repository = reference.Reference.split_docker_domain(repository)
        headers = self._get_headers(repository)
        headers['Accept'] = 'application/vnd.docker.distribution.manifest.v2+json'
        response = requests.get(f'{self.url}/v2/{repository}/blobs/{digest}',
                                headers=headers)
        if response.status_code != requests.codes.ok:
            raise PackageManagerError(f'Failed to retrieve blobs for {repository}:{digest}: '
                                      f'response: {response.status_code}, content: {response.content}')
        content = json.loads(response.content)

        log.debug(f'retrieved blob for {repository}:{digest}: {content}')
        return content


class RegistryResolver:
    DockerHubAuthService = AuthService('https://auth.docker.io', 'registry.docker.io')
    DockerHubRegistry = Registry('https://index.docker.io', DockerHubAuthService)

    def __init__(self):
        pass

    def get_registry_for(self, ref: str) -> Registry:
        domain, _ = reference.Reference.split_docker_domain(ref)
        if domain == reference.DEFAULT_DOMAIN:
            return self.DockerHubRegistry
        # TODO: authentication service for private registries
        # TODO: support insecure registries
        return Registry(f'https://{domain}')
