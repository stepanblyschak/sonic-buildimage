#!/usr/bin/env python3

from sonic_package_manager.database import PackageDatabase, PackageEntry
from sonic_package_manager.dockerapi import DockerApi, get_repository_from_image
from sonic_package_manager.manifest import Manifest
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.package import Package


class PackageSource(object):
    """ PackageSource abstracts the way manifest is read
    and image is retrieved based on different image sources.
    (i.e from registry, from tarball or locally installed) """

    def __init__(self,
                 database: PackageDatabase,
                 docker: DockerApi,
                 manifest_resolver: ManifestResolver):
        self.database = database
        self.docker = docker
        self.manifest_resolver = manifest_resolver

    def get_manifest(self) -> Manifest:
        """ Returns package manifest.
        Child class has to implement this method.

        Returns:
            Manifest
        """
        raise NotImplementedError

    def install_image(self):
        """ Install image based on package source. 
        Child class has to implement this method.
        
        Returns:
            Docker Image object.
        """

        raise NotImplementedError

    def install(self, package: Package):
        """ Install image based on package source,
        record installation infromation in PackageEntry..

        Args:
            package: SONiC Package
        """

        image = self.install_image()
        package.entry.image_id = image.id
        # if no repository is defined for this package
        # get repository from image
        if not package.repository:
            package.entry.repository = get_repository_from_image(image)

    def uninstall(self, package: Package):
        """ Uninstall image.

        Args:
            package: SONiC Package
        """

        self.docker.rmi(package.image_id)
        package.entry.image_id = None

    def get_package(self) -> Package:
        """ Returns SONiC Package based on manifest.

        Returns:
              SONiC Package
        """

        manifest = self.get_manifest()

        name = manifest['package']['name']
        description = manifest['package']['description']

        repository = None

        if self.database.has_package(name):
            # inherit package database info
            package = self.database.get_package(name)
            repository = package.repository
            description = description or package.description

        return Package(
            PackageEntry(
                name,
                repository,
                description,
            ),
            manifest
        )


class TarballSource(PackageSource):
    """ TarballSource implements PackageSource
    for locally existing image saved as tarball. """

    def __init__(self,
                 tarball_path: str,
                 database: PackageDatabase,
                 docker: DockerApi,
                 manifest_resolver: ManifestResolver):
        super().__init__(database,
                         docker,
                         manifest_resolver)
        self.tarball_path = tarball_path

    def get_manifest(self) -> Manifest:
        """ Returns manifest read from tarball. """

        return self.manifest_resolver.from_tarball(self.tarball_path)

    def install_image(self):
        """ Installs image from local tarball source. """

        return self.docker.load(self.tarball_path)


class RegistrySource(PackageSource):
    """ RegistrySource implements PackageSource
    for packages that are pulled from registry. """

    def __init__(self,
                 repository: str,
                 reference: str,
                 database: PackageDatabase,
                 docker: DockerApi,
                 manifest_resolver: ManifestResolver):
        super().__init__(database,
                         docker,
                         manifest_resolver)
        self.repository = repository
        self.reference = reference

    def get_manifest(self) -> Manifest:
        """ Returns manifest read from registry. """

        return self.manifest_resolver.from_registry(self.repository,
                                                    self.reference)

    def install_image(self):
        """ Installs image from registry. """

        return self.docker.pull(self.repository, self.reference)


class LocalSource(PackageSource):
    """ LocalSource accesses local docker library to retrieve manifest
    but does not implement installation of the image. """

    def __init__(self,
                 entry: PackageEntry,
                 database: PackageDatabase,
                 docker: DockerApi,
                 manifest_resolver: ManifestResolver):
        super().__init__(database,
                         docker,
                         manifest_resolver)
        self.entry = entry

    def get_manifest(self) -> Manifest:
        """ Returns manifest read from locally installed Docker. """

        image = self.entry.image_id

        if self.entry.built_in:
            # Built-in (installed not via sonic-package-manager)
            # won't have image_id in database. Using their
            # repository name as image.
            image = f'{self.entry.repository}:latest'

        return self.manifest_resolver.from_local(image)

    def get_package(self) -> Package:
        return Package(self.entry, self.get_manifest())
