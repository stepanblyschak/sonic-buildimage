#!/usr/bin/env python
import contextlib
import functools
from typing import Optional, Union, Iterable, List

import docker

from sonic_py_common import device_info

from sonic_package_manager.constraint import PackageConstraint
from sonic_package_manager.database import PackageDatabase, PackageEntry
from sonic_package_manager.dockerapi import DockerApi
from sonic_package_manager.errors import (
    PackageInstallationError,
    PackageDependencyError,
    PackageConflictError,
    PackageSonicRequirementError,
    PackageManagerError,
    PackageUninstallationError
)
from sonic_package_manager.logger import log
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.package import Package
from sonic_package_manager.progress import ProgressManager
from sonic_package_manager.reference import PackageReference
from sonic_package_manager.registry import RegistryResolver
from sonic_package_manager.service_creator.creator import ServiceCreator, run_command
from sonic_package_manager.service_creator.feature import FeatureRegistry
from sonic_package_manager.version import Version, VersionRange


@contextlib.contextmanager
def failure_ignore(ignore: bool):
    """ Ignores failures based on parameter passed. """
    try:
        yield
    except Exception as err:
        if ignore:
            log.warning(f'ignoring error {err}')
        else:
            raise


def get_installation_target(expression):
    try:
        return get_installation_target_from_constraint(PackageConstraint.parse(expression))
    except ValueError:
        # if we failed to parse the expression as constraint expression
        # we will try to parse it as reference
        return PackageReference.parse(expression)


def check_package_dependencies(packages: Iterable[Package]):
    """ Verify that all dependencies are met in all packages passed to this function.
    Args:
        packages: list of packages to check
    Raises:
        PackageDependencyError: if dependency is missing
        PackageConflictError: if there is a conflict between packages
    """

    def find(name: str) -> Optional[Package]:
        for package in packages:
            if package.name == name:
                return package
        return None

    for pkg in packages:
        log.debug(f'checking dependencies for {pkg.name}')
        for dependency in pkg.manifest['package']['depends']:
            dependency_package = find(dependency.name)
            if dependency_package is None:
                raise PackageDependencyError(pkg.name, dependency)
            installed_version = dependency_package.version
            log.debug(f'dependency package is installed {dependency.name}: {installed_version}')
            if not dependency.constraint.allows_all(installed_version):
                raise PackageDependencyError(pkg.name, dependency, installed_version)

        log.debug(f'checking conflicts for {pkg.name}')
        for conflict in pkg.manifest['package']['breaks']:
            conflicting_package = find(conflict.name)
            if conflicting_package is None:
                continue
            installed_version = conflicting_package.version
            log.debug(f'conflicting package is installed {conflict.name}: {installed_version}')
            if conflict.constraint.allows_all(installed_version):
                raise PackageConflictError(pkg.name, conflict, installed_version)


def get_installation_target_from_constraint(constraint: PackageConstraint) -> PackageReference:
    package_name, version_constraint = constraint.name, constraint.constraint
    # Allow only specific version for now.
    # Later we can improve package manager to support
    # installing packages using expressions like 'package>1.0.0'
    if version_constraint == VersionRange():  # empty range means any version
        return PackageReference(package_name, None)
    if not isinstance(version_constraint, Version):
        raise PackageManagerError(f'Can only install specific version. '
                                  f'Use only following expression "{package_name}==<version>" '
                                  f'to install specific version')
    return PackageReference(package_name, str(version_constraint))


class PackageManager:
    def __init__(self,
                 docker: DockerApi,
                 registry_resolver: RegistryResolver,
                 database: PackageDatabase,
                 manifest_resolver: ManifestResolver,
                 service_creator: ServiceCreator):
        """ Initialize PackageManager. """

        self.docker = docker
        self.registry_resolver = registry_resolver
        self.database = database
        self.manifest_resolver = manifest_resolver
        self.service_creator = service_creator
        self.feature_registry = service_creator.feature_registry
        self.is_multi_npu = device_info.is_multi_npu()
        self.num_npus = device_info.get_num_npus()
        self.version_info = device_info.get_sonic_version_info() or {}

    @staticmethod
    def get_manager() -> 'PackageManager':
        docker_api = DockerApi(docker.from_env())
        registry_resolver = RegistryResolver()
        return PackageManager(DockerApi(docker.from_env()),
                              registry_resolver,
                              PackageDatabase.from_file(),
                              ManifestResolver(docker_api, registry_resolver),
                              ServiceCreator(FeatureRegistry.create()))

    def get_database(self):
        return self.database

    def get_docker(self):
        return self.docker

    def add_package(self, *args, **kwargs):
        self.database.add_package(*args, **kwargs)
        self.database.commit()

    def remove_package(self, name: str):
        self.database.remove_package(name)
        self.database.commit()

    def get_package(self, name: str, ref: Optional[Union[Version, str]] = None) -> Package:
        package_info = self.get_database().get_package(name)
        if ref is None:
            if package_info.installed:
                ref = str(package_info.version)
            elif package_info.default_reference is not None:
                ref = package_info.default_reference
            else:
                raise PackageManagerError(f'No default reference tag. '
                                          f'Please specify the version or digest explicitly')
        else:
            if str(package_info.version) != ref:
                package_info.installed = False

        manifest = self.get_manifest(package_info, ref)
        package_info.version = manifest['package']['version']
        return Package(package_info, ref, manifest)

    def get_available_versions(self, name: str, all: bool = False):
        package_info = self.database.get_package(name)
        registry = self.registry_resolver.get_registry_for(package_info.repository)
        available_tags = registry.tags(package_info.repository)

        def is_semantic_ver_tag(tag: str) -> bool:
            if all:
                return True
            try:
                Version.parse(tag)
                return True
            except ValueError:
                pass
            return False

        return filter(is_semantic_ver_tag, available_tags)

    def get_installed_packages_and(self, package: Package):
        packages = self.get_installed_packages() + [package]
        return packages

    def get_installed_packages_except(self, package: Package) -> List[Package]:
        def filter_package(pkg):
            return pkg.name == package.name

        packages = filter(filter_package, self.get_installed_packages())
        return list(packages)

    def is_installed(self, name: str) -> bool:
        if not self.database.has_package(name):
            return False
        package_info = self.database.get_package(name)
        return package_info.installed

    def has_package(self, name: str):
        return self.database.has_package(name)

    def get_installed_packages(self):
        return [self.get_package(entry.name, str(entry.version))
                for entry in self.get_database() if entry.installed]

    def get_manifest(self, package_info: PackageEntry, ref: str):
        return self.manifest_resolver.get_manifest(package_info, ref)

    def systemctl_action(self, package: Package, action: str):
        name = package.manifest['service']['name']
        host_service = package.manifest['service']['host-service']
        asic_service = package.manifest['service']['asic-service']
        single_instance = host_service or (asic_service and not self.is_multi_npu)
        multi_instance = asic_service and self.is_multi_npu

        if single_instance:
            run_command(f'systemctl {action} {name}')
        if multi_instance:
            for npu in range(self.num_npus):
                run_command(f'systemctl {action} {name}@{npu}')

    def install(self, expression: str, force=False):
        package_reference = get_installation_target(expression)
        name, reference = package_reference.name, package_reference.reference

        with failure_ignore(force):
            if self.is_installed(name):
                raise PackageInstallationError(f'{name} is already installed')

        package = self.get_package(name, reference)
        base_os_version = self.get_base_os_version()
        version_constraint = package.manifest['package']['base-os-constraint']

        with failure_ignore(force):
            if not version_constraint.allows_all(base_os_version):
                raise PackageSonicRequirementError(package.name, version_constraint,
                                                   base_os_version)

        installed_packages = self.get_installed_packages_and(package)

        with failure_ignore(force):
            check_package_dependencies(installed_packages)

        version = package.manifest['package']['version']
        cleanup = []  # cleanup function list

        def add_cleanup(func):
            cleanup.append(func)

        def exec_cleanup():
            for cleanup_func in reversed(cleanup):
                try:
                    cleanup_func()
                except Exception as cleanup_err:
                    log.error(f'{cleanup_err}')

        try:
            self.docker.pull(package.repository, package.reference, version, ProgressManager())
            add_cleanup(functools.partial(self.docker.rmi, package.repository, version))

            self.docker.tag(package.repository, version, package.repository, 'latest')
            add_cleanup(functools.partial(self.docker.rmi, package.repository, 'latest'))

            self.service_creator.create(package)
            add_cleanup(functools.partial(self.service_creator.remove, package))
        except Exception as err:
            exec_cleanup()
            raise PackageInstallationError(f'Failed to install {package.name}: {err}')
        except KeyboardInterrupt:
            exec_cleanup()
            raise

        package_entry = package.entry
        package_entry.installed = True
        self.database.update_package(package_entry)
        self.database.commit()

    def uninstall(self, name: str, force=False):
        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageInstallationError(f'{name} is not installed')

        with failure_ignore(force):
            if self.feature_registry.is_feature_enabled(name):
                raise PackageInstallationError(f'{name} is enabled. Disable the feature first')

        package = self.get_package(name)

        installed_packages = self.get_installed_packages_except(package)

        with failure_ignore(force):
            check_package_dependencies(installed_packages)

        try:
            self.service_creator.remove(package)
            self.docker.rm(package.repository, package.reference)
            self.docker.rm(package.repository, 'latest')
            self.docker.rmi(package.repository, package.reference)
            self.docker.rmi(package.repository, 'latest')
        except Exception as err:
            raise PackageUninstallationError(f'Failed to uninstall {package.name}: {err}')

        package_entry = package.entry
        package_entry.installed = False
        package_entry.version = None
        self.database.update_package(package_entry)
        self.database.commit()

    def upgrade(self, expression: str, force=False):
        package_reference = get_installation_target(expression)
        name, reference = package_reference.name, package_reference.reference

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageInstallationError(f'{name} is not installed')

        old_package = self.get_package(name)
        new_package = self.get_package(name, reference)

        old_feature = old_package.manifest['service']['name']
        new_feature = new_package.manifest['service']['name']

        with failure_ignore(force):
            old_version = old_package.manifest['package']['version']
            new_version = new_package.manifest['package']['version']

            if old_version == new_version:
                raise PackageManagerError(f'{new_version} is already installed')

            if new_version < old_version:
                raise PackageManagerError(f'Request to downgrade from {old_version} to {new_version}. '
                                          f'Downgrade might be not supported by the package')

        base_os_version = self.get_base_os_version()
        version_constraint = new_package.manifest['package']['base-os-constraint']

        with failure_ignore(force):
            if not version_constraint.allows_all(base_os_version):
                raise PackageSonicRequirementError(new_package.name, version_constraint,
                                                   base_os_version)

        # remove currently installed package from the list
        installed_packages = self.get_installed_packages_except(old_package)
        # add the package to upgrade to the list
        installed_packages.append(new_package)

        with failure_ignore(force):
            check_package_dependencies(installed_packages)

        version = new_package.manifest['package']['version']
        cleanup = []  # cleanup function list

        def add_cleanup(func):
            cleanup.append(func)

        def exec_cleanup():
            for cleanup_func in reversed(cleanup):
                try:
                    cleanup_func()
                except Exception as cleanup_err:
                    log.error(f'{cleanup_err}')

        try:
            self.docker.pull(new_package.repository, new_package.reference, version, ProgressManager())
            add_cleanup(functools.partial(self.docker.rmi, new_package.repository, version))

            if self.feature_registry.is_feature_enabled(old_feature):
                self.systemctl_action(old_package, 'stop')

            self.service_creator.remove(old_package, deregister_feature=False)
            self.docker.rm(old_package.repository, old_package.reference)
            self.docker.rm(old_package.repository, 'latest')
            self.docker.rmi(old_package.repository, old_package.reference)
            self.docker.rmi(old_package.repository, 'latest')

            self.docker.tag(new_package.repository, version, new_package.repository, 'latest')
            add_cleanup(functools.partial(self.docker.rmi, old_package.repository, 'latest'))

            self.service_creator.create(new_package, register_feature=False)
            add_cleanup(functools.partial(self.service_creator.remove, new_package))

            if self.feature_registry.is_feature_enabled(new_feature):
                self.systemctl_action(new_package, 'start')
        except Exception as err:
            exec_cleanup()
            raise PackageInstallationError(f'Failed to upgrade {new_package.name}: {err}')
        except KeyboardInterrupt:
            exec_cleanup()
            raise

        new_package_entry = new_package.entry
        new_package_entry.installed = True
        self.database.update_package(new_package_entry)
        self.database.commit()

    def migrate_packages(self, old_package_database: PackageDatabase):
        self.migrate_package_database(old_package_database)

        # TODO: Toposort packages by their dependencies first.
        for old_package in old_package_database:
            if not old_package.installed or old_package.built_in:
                continue

            log.info(f'migrating package {old_package.name}')

            new_package = self.database.get_package(old_package.name)
            if new_package.installed or new_package.default_reference is not None:
                pkg = self.get_package(new_package.name)
                new_package_version = pkg.manifest['package']['version']
            else:
                # No default version and package is not installed.
                # Set it to 0.0.0 so it will be
                # always lower than old package version
                # and the old version will be installed.
                new_package_version = Version(0, 0, 0)

            if old_package.version > new_package_version:
                log.info(f'old package version is greater then default version in new image: '
                         f'{old_package.version} > {new_package_version}')
                if new_package.installed:
                    log.info(f'upgrading {new_package.name} to {old_package.version}')
                    self.upgrade(f'{new_package.name}=={old_package.version}')
                else:
                    log.info(f'installing {new_package.name} with version {old_package.version}')
                    self.install(f'{new_package.name}=={old_package.version}')
            else:
                if not new_package.installed:
                    self.install(f'{new_package.name}')
                else:
                    log.info(f'skipping {new_package.name} as installed version is newer')

            self.database.commit()

    def migrate_package_database(self, old_package_database: PackageDatabase):
        for package in old_package_database:
            if not self.has_package(package.name):
                self.database.add_package(package.name,
                                          package.repository,
                                          package.description,
                                          package.default_reference)

    def get_base_os_version(self):
        return self.version_info.get('base-os-compatibility-version') or Version(1, 0, 0)
