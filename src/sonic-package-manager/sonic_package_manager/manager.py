#!/usr/bin/env python
import contextlib
import functools
import os
import pkgutil
import tempfile
from typing import Dict, Any, Iterable, Optional, Callable

import docker
import filelock
from sonic_py_common import device_info

from sonic_package_manager import utils
from sonic_package_manager.constraint import PackageConstraint
from sonic_package_manager.database import PackageDatabase, PackageEntry, PACKAGE_MANAGER_LOCK_FILE
from sonic_package_manager.dockerapi import DockerApi, get_repository_from_image
from sonic_package_manager.errors import (
    PackageInstallationError,
    PackageDependencyError,
    PackageConflictError,
    PackageSonicRequirementError,
    PackageManagerError,
    PackageUninstallationError,
    PackageUpgradeError
)
from sonic_package_manager.logger import log
from sonic_package_manager.manifest_resolver import ManifestResolver
from sonic_package_manager.package import Package
from sonic_package_manager.progress import ProgressManager
from sonic_package_manager.reference import PackageReference
from sonic_package_manager.registry import RegistryResolver
from sonic_package_manager.service_creator.creator import ServiceCreator, run_command
from sonic_package_manager.service_creator.feature import FeatureRegistry
from sonic_package_manager.service_creator.sonic_db import SonicDB
from sonic_package_manager.service_creator.utils import in_chroot
from sonic_package_manager.version import Version, VersionRange, version_to_tag, tag_to_version


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


def under_lock(func: Callable) -> Callable:
    """ Execute operations under lock. """

    def wrapped_function(*args, **kwargs):
        self = args[0]
        with self.lock:
            return func(*args, **kwargs)
    return wrapped_function


def rollback_wrapper(func, *args, **kwargs):
    """ Used in rollback callbacks to ignore failure
    but proceed with rollback. Error will be printed
    but not fail the whole procedure of rollback. """

    def wrapper():
        try:
            functools.partial(func, *args, **kwargs)
        except Exception as err:
            log.error(f'failed in rollback: {err}')
    return wrapper


def package_constraint_to_reference(constraint: PackageConstraint) -> PackageReference:
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
    return PackageReference(package_name, version_to_tag(version_constraint))


def parse_reference_expression(expression):
    try:
        return package_constraint_to_reference(PackageConstraint.parse(expression))
    except ValueError:
        # if we failed to parse the expression as constraint expression
        # we will try to parse it as reference
        return PackageReference.parse(expression)


def validate_package_tree(packages: Dict[str, Package]):
    """ Verify that all dependencies are met in all packages passed to this function.
    Args:
        packages: list of packages to check
    Raises:
        PackageDependencyError: if dependency is missing
        PackageConflictError: if there is a conflict between packages
    """

    for name, package in packages.items():
        log.debug(f'checking dependencies for {name}')
        for dependency in package.manifest['package']['depends']:
            dependency_package = packages.get(dependency.name)
            if dependency_package is None:
                raise PackageDependencyError(package.name, dependency)
            installed_version = dependency_package.version
            log.debug(f'dependency package is installed {dependency.name}: {installed_version}')
            if not dependency.constraint.allows_all(installed_version):
                raise PackageDependencyError(package.name, dependency, installed_version)

        log.debug(f'checking conflicts for {name}')
        for conflict in package.manifest['package']['breaks']:
            conflicting_package = packages.get(conflict.name)
            if conflicting_package is None:
                continue
            installed_version = conflicting_package.version
            log.debug(f'conflicting package is installed {conflict.name}: {installed_version}')
            if conflict.constraint.allows_all(installed_version):
                raise PackageConflictError(package.name, conflict, installed_version)


class PackageManager:
    """ SONiC Package Manager. """

    def __init__(self,
                 dockerapi: DockerApi,
                 registry_resolver: RegistryResolver,
                 database: PackageDatabase,
                 manifest_resolver: ManifestResolver,
                 service_creator: ServiceCreator,
                 device_information: Any,
                 lock: filelock.FileLock):
        """ Initialize PackageManager. """

        self.lock = lock
        self.docker = dockerapi
        self.registry_resolver = registry_resolver
        self.database = database
        self.manifest_resolver = manifest_resolver
        self.service_creator = service_creator
        self.feature_registry = service_creator.feature_registry
        self.is_multi_npu = device_information.is_multi_npu()
        self.num_npus = device_information.get_num_npus()
        self.version_info = device_information.get_sonic_version_info()
        self.base_os_version = Version.parse(self.version_info.get('base_os_compatibility_version'))

    @under_lock
    def add_repository(self, *args, **kwargs):
        """ Add repository to package database.

        """

        self.database.add_package(*args, **kwargs)
        self.database.commit()

    @under_lock
    def remove_repository(self, name: str):
        """ Remove repository from package database.

        Args:
            name: package name
        """

        self.database.remove_package(name)
        self.database.commit()

    @under_lock
    def install(self,
                expression: str,
                force=False,
                enable=False,
                default_owner='local'):
        """ Install a SONiC Package from the package reference
        expression string. Can force the installation if force parameter
        is True.

        Args:
            expression: SONiC Package reference expression
            force: Force the installation.
            enable: If True the installed feature package will be enabled.
            default_owner: Owner of the installed package.
        Raises:
            PackageManagerError
        """

        package = self.resolve_package(expression)
        name = package.name

        with failure_ignore(force):
            if self.is_installed(name):
                raise PackageInstallationError(f'{name} is already installed')

        version_constraint = package.manifest['package']['base-os-constraint']
        feature_state = 'enabled' if enable else 'disabled'

        with failure_ignore(force):
            if not version_constraint.allows_all(self.base_os_version):
                raise PackageSonicRequirementError(package.name, version_constraint,
                                                   self.base_os_version)

        installed_packages = self._get_installed_packages_and(package)

        with failure_ignore(force):
            validate_package_tree(installed_packages)

        # After all checks are passed we proceed to actual installation

        try:
            with contextlib.ExitStack() as exit_stack:
                if package.reference:
                    image = self.docker.pull(package.repository, package.reference)
                    exit_stack.callback(rollback_wrapper(self.docker.rmi, image.id))
                else:
                    image = self.docker.load(expression)
                    self._init_repository_from_image(package, image)
                    exit_stack.callback(rollback_wrapper(self.docker.rmi, image.id))

                repotag = f'{package.repository}:latest'
                self.docker.tag(image.id, repotag)
                exit_stack.callback(rollback_wrapper(self.docker.rmi, repotag))

                self.service_creator.create(package, state=feature_state, owner=default_owner)
                exit_stack.callback(rollback_wrapper(self.service_creator.remove, package))

                self._install_cli_plugins(package)
                exit_stack.callback(rollback_wrapper(self._uninstall_cli_plugins, package))

                exit_stack.pop_all()
        except Exception as err:
            raise PackageInstallationError(f'Failed to install {package.name}: {err}')
        except KeyboardInterrupt:
            raise

        package.entry.installed = True
        # When installing package from a tarball, package may not be in database.
        if not self.database.has_package(package.name):
            self.database.add_package(package.name, package.repository)
        self.database.update_package(package.entry)
        self.database.commit()

    @under_lock
    def uninstall(self, name: str, force=False):
        """ Uninstall a SONiC Package referenced by name.
        The uninstallation can be forced if force argument is
        True.

        Args:
            name: SONiC Package name.
            force: Force the installation.
        Raises:
            PackageManagerError
        """

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageUninstallationError(f'{name} is not installed')\

        package = self.get_package(name)
        service_name = package.manifest['service']['name']

        with failure_ignore(force):
            if self.feature_registry.is_feature_enabled(service_name):
                raise PackageUninstallationError(f'{service_name} is enabled. Disable the feature first')

        if package.built_in:
            raise PackageUninstallationError(f'Cannot uninstall built-in package {package.name}')

        installed_packages = self._get_installed_packages_except(package)

        with failure_ignore(force):
            validate_package_tree(installed_packages)

        # After all checks are passed we proceed to actual uninstallation

        try:
            self._uninstall_cli_plugins(package)
            self.service_creator.remove(package)

            repotag = f'{package.repository}:latest'
            image = self.docker.get_image(repotag)

            # Clean containers based on this image
            containers = self.docker.ps(filters={'ancestor': image.id}, all=True)
            for container in containers:
                self.docker.rm(container.id, force=True)

            self.docker.rmi(image.id, force=True)
        except Exception as err:
            raise PackageUninstallationError(f'Failed to uninstall {package.name}: {err}')

        package.entry.installed = False
        package.entry.version = None
        self.database.update_package(package.entry)
        self.database.commit()

    @under_lock
    def upgrade(self, expression: str, force=False):
        """ Upgrade a SONiC Package to a version the package reference
        expression specifies. Can force the upgrade if force parameter
        is True. Force can allow a package downgrade.

        Args:
            expression: SONiC Package reference expression
            force: Force the installation.
        Raises:
            PackageManagerError
        """

        new_package = self.resolve_package(expression)
        name = new_package.name

        with failure_ignore(force):
            if not self.is_installed(name):
                raise PackageUpgradeError(f'{name} is not installed')

        old_package = self.get_package(name)

        if old_package.built_in:
            raise PackageUpgradeError(f'Cannot upgrade built-in package {old_package.name}')

        old_feature = old_package.manifest['service']['name']
        new_feature = new_package.manifest['service']['name']
        old_version = old_package.manifest['package']['version']
        new_version = new_package.manifest['package']['version']

        with failure_ignore(force):
            if old_version == new_version:
                raise PackageUpgradeError(f'{new_version} is already installed')

            # TODO: Not all packages might support downgrade.
            # We put a check here but we understand that for some packages
            # the downgrade might be safe to do. In that case we might want to
            # add another argument to this function: allow_downgrade: bool = False.
            # Another way to do that might be a variable in manifest describing package
            # downgrade ability or downgrade-able versions.
            if new_version < old_version:
                raise PackageUpgradeError(f'Request to downgrade from {old_version} to {new_version}. '
                                          f'Downgrade might be not supported by the package')

        version_constraint = new_package.manifest['package']['base-os-constraint']

        with failure_ignore(force):
            if not version_constraint.allows_all(self.base_os_version):
                raise PackageSonicRequirementError(new_package.name, version_constraint,
                                                   self.base_os_version)

        # remove currently installed package from the list
        installed_packages = self._get_installed_packages_except(old_package)
        # add the package to upgrade to the list
        installed_packages[new_package.name] = new_package

        with failure_ignore(force):
            validate_package_tree(installed_packages)

        # After all checks are passed we proceed to actual upgrade

        try:
            with contextlib.ExitStack() as exit_stack:
                self._uninstall_cli_plugins(old_package)
                exit_stack.callback(rollback_wrapper(self._install_cli_plugins, old_package))

                if new_package.reference:
                    image = self.docker.pull(new_package.repository, new_package.reference)
                    exit_stack.callback(rollback_wrapper(self.docker.rmi, image.id))
                else:
                    image = self.docker.load(expression)
                    self._init_repository_from_image(new_package, image)
                    exit_stack.callback(rollback_wrapper(self.docker.rmi, image.id))

                if self.feature_registry.is_feature_enabled(old_feature):
                    self._systemctl_action(old_package, 'stop')
                    exit_stack.callback(rollback_wrapper(self._systemctl_action,
                                                         old_package, 'start'))

                self.service_creator.remove(old_package, deregister_feature=False)
                exit_stack.callback(rollback_wrapper(self.service_creator.create,
                                                     old_package, register_feature=False))

                # This is no return point, after we start removing old Docker images
                # there is no guaranty we can actually successfully roll-back.

                old_repotag = f'{old_package.repository}:latest'
                new_repotag = f'{new_package.repository}:latest'

                old_image = self.docker.get_image(old_repotag)

                # Clean containers based on the old image
                containers = self.docker.ps(filters={'ancestor': old_image.id}, all=True)
                for container in containers:
                    self.docker.rm(container.id, force=True)

                self.docker.rmi(old_image.id, force=True)
                self.docker.tag(image.id, new_repotag)

                self.service_creator.create(new_package, register_feature=False)

                if self.feature_registry.is_feature_enabled(new_feature):
                    self._systemctl_action(new_package, 'start')

                self._install_cli_plugins(new_package)

                exit_stack.pop_all()
        except Exception as err:
            raise PackageUpgradeError(f'Failed to upgrade {new_package.name}: {err}')
        except KeyboardInterrupt:
            raise

        new_package_entry = new_package.entry
        new_package_entry.installed = True
        self.database.update_package(new_package_entry)
        self.database.commit()

    @under_lock
    def migrate_packages(self,
                         old_package_database: PackageDatabase,
                         dockerd_sock: Optional[str] = None):
        """ Migrate packages from old database. This function can
        do a comparison between current database and the database
        passed in as argument.
            If the package is missing in the current database it will be added.
            If the package is installed in the passed database and in the current
        it is not installed it will be installed with a passed database package version.
            If the package is installed in the passed database and it is installed
        in the current database but with older version the package will be upgraded to
        the never version.
            If the package is installed in the passed database and in the current
        it is installed but with never version - no actions are taken.
            If dockerd_sock parameter is passed, the migration process will use loaded
        images from docker library of the currently installed image.

        Args:
            old_package_database: SONiC Package Database to migrate packages from.
            dockerd_sock: Path to dockerd socket.
        Raises:
            PackageManagerError
        """

        self._migrate_package_database(old_package_database)

        def migrate_package(package_entry, migrate_operation=self.install):
            if migrate_operation == self.install:
                log_msg_operation = 'installing'
            elif migrate_operation == self.upgrade:
                log_msg_operation = 'upgrading'
            else:
                raise ValueError(f'Invalid operation passed in {migrate_operation}')

            if dockerd_sock:
                log.info(f'{log_msg_operation} {package_entry.name} from old docker library')
                dockerapi = DockerApi(docker.DockerClient(base_url=f'unix://{dockerd_sock}'))
                image = dockerapi.get_image(f'{package_entry.repository}:latest')
                with tempfile.NamedTemporaryFile('wb') as file:
                    for chunk in image.save(named=True):
                        file.write(chunk)
                    migrate_operation(file.name)
            else:
                log.info(f'{log_msg_operation} {package_entry.name} version {package_entry.version}')
                migrate_operation(f'{package_entry.name}=={package_entry.version}')

        # TODO: Topological sort packages by their dependencies first.
        for old_package in old_package_database:
            if not old_package.installed or old_package.built_in:
                continue

            log.info(f'migrating package {old_package.name}')

            new_package = self.database.get_package(old_package.name)

            if new_package.installed:
                if old_package.version > new_package.version:
                    log.info(f'{old_package.name} package version is greater '
                             f'then installed in new image: '
                             f'{old_package.version} > {new_package.version}')
                    log.info(f'upgrading {new_package.name} to {old_package.version}')
                    new_package.version = old_package.version
                    migrate_package(new_package, self.upgrade)
                else:
                    log.info(f'skipping {new_package.name} as installed version is newer')
            elif new_package.default_reference is not None:
                new_package_ref = PackageReference(new_package.name, new_package.default_reference)
                package = self.query_package(new_package_ref)
                new_package_default_version = package.manifest['package']['version']
                if old_package.version > new_package_default_version:
                    log.info(f'{old_package.name} package version is lower '
                             f'then the default in new image: '
                             f'{old_package.version} > {new_package_default_version}')
                    new_package.version = old_package.version
                    migrate_package(new_package)
                else:
                    self.install(f'{new_package.name}=={new_package_default_version}')
            else:
                # No default version and package is not installed.
                # Migrate old package same version.
                new_package.version = old_package.version
                migrate_package(new_package, self.install)

            self.database.commit()

    def get_package(self, name: str) -> Package:
        """ Get installed package by name.

        Args:
            name: package name.
        Returns:
            Package object.
        """

        package_entry = self.database.get_package(name)
        manifest = self.manifest_resolver.get_manifest(package_entry)
        return Package(package_entry, 'latest', manifest)

    def query_package(self, package_ref: PackageReference) -> Package:
        """ Get package from name and reference. If reference is not provided
        reference returned by get_package_default_reference is used.

        Args:
            package_ref: Package reference
        Returns:
            Package object
        """

        package_entry = self.database.get_package(package_ref.name)

        if package_ref.reference is None:
            if package_entry.installed:
                return self.get_package(package_entry.name)
            if package_entry.default_reference is not None:
                package_ref.reference = package_entry.default_reference
            else:
                raise PackageManagerError(f'No default reference tag. '
                                          f'Please specify the version or tag explicitly')

        package_entry.installed = False
        manifest = self.manifest_resolver.get_manifest(package_entry, package_ref.reference)
        package_entry.version = manifest['package']['version']
        return Package(package_entry, package_ref.reference, manifest)

    def read_package(self, image_path: str) -> Package:
        """ Creates package object from local image tarball.

        Args:
            image_path: str
        Returns:
            Package object.
        """

        manifest = self.manifest_resolver.get_manifest_from_image_tarball(image_path)

        name = manifest['package']['name']
        version = manifest['package']['version']

        if self.database.has_package(name):
            # inherit package database info
            package = self.database.get_package(name)
            repository = package.repository
        else:
            # put an empty repository, since this is a local installation
            # repository has to be initialized after the local image is loaded.
            repository = ''

        # Put empty reference, since this is a local installation
        reference = ''

        return Package(
            PackageEntry(
                name,
                repository=repository,
                version=version
            ),
            reference,
            manifest
        )

    def resolve_package(self, expression: str) -> Package:
        """ Resolve package from expression string.
        The expression can be a constraint expression,
        reference expression or a path to a file.

        Args:
            expression: package expression string
        Returns:
            Package object.

        """

        if os.path.exists(expression):
            return self.read_package(expression)

        package_ref = parse_reference_expression(expression)

        return self.query_package(package_ref)

    def get_package_available_versions(self,
                                       name: str,
                                       all: bool = False) -> Iterable:
        """ Returns a list of available versions for package.

        Args:
            name: Package name.
            all: If set to True will return all tags including
                 those which do not follow semantic versioning.
        Returns:
            List of versions
        """
        package_info = self.database.get_package(name)
        registry = self.registry_resolver.get_registry_for(package_info.repository)
        available_tags = registry.tags(package_info.repository)

        def is_semantic_ver_tag(tag: str) -> bool:
            try:
                tag_to_version(tag)
                return True
            except ValueError:
                pass
            return False

        if all:
            return available_tags

        return map(tag_to_version, filter(is_semantic_ver_tag, available_tags))

    def is_installed(self, name: str) -> bool:
        """ Returns boolean whether a package called name is installed.

        Args:
            name: Package name.
        Returns:
            True if package is installed, False otherwise.
        """

        if not self.database.has_package(name):
            return False
        package_info = self.database.get_package(name)
        return package_info.installed

    def get_installed_packages(self) -> Dict[str, Package]:
        """ Returns a dictionary of installed packages where
        keys are package names and values are package objects.

        Returns:
            Installed packages dictionary.
        """

        return {
            entry.name: self.get_package(entry.name)
            for entry in self.database if entry.installed
        }

    def _migrate_package_database(self, old_package_database: PackageDatabase):
        for package in old_package_database:
            if not self.database.has_package(package.name):
                self.database.add_package(package.name,
                                          package.repository,
                                          package.description,
                                          package.default_reference)

    def _get_installed_packages_and(self, package: Package) -> Dict[str, Package]:
        packages = self.get_installed_packages()
        packages[package.name] = package
        return packages

    def _get_installed_packages_except(self, package: Package) -> Dict[str, Package]:
        packages = self.get_installed_packages()
        packages.pop(package.name)
        return packages

    # TODO: Replace with "config feature" command.
    # The problem with current "config feature" command
    # is that it is asynchronous, thus can't be used
    # for package upgrade purposes where we need to wait
    # till service stops before upgrading docker image.
    # It would be really handy if we could just call
    # smth like: "config feature state <name> <state> --wait"
    # instead of operating on systemd service since
    # this is basically a duplicated code from hostcfgd.
    def _systemctl_action(self, package: Package, action: str):
        name = package.manifest['service']['name']
        host_service = package.manifest['service']['host-service']
        asic_service = package.manifest['service']['asic-service']
        single_instance = host_service or (asic_service and not self.is_multi_npu)
        multi_instance = asic_service and self.is_multi_npu

        if in_chroot():
            return

        if single_instance:
            run_command(f'systemctl {action} {name}')
        if multi_instance:
            for npu in range(self.num_npus):
                run_command(f'systemctl {action} {name}@{npu}')

    @staticmethod
    def _init_repository_from_image(package: Package, image):
        """ Set package repository based on image if
        package has no repository set. """

        if package.repository:  # already set
            return

        repository = get_repository_from_image(image)
        if not repository:
            # This means the image was saved as unnamed.
            # Using package name as a repository.
            repository = package.name
        package.entry.repository = repository

    @staticmethod
    def _get_cli_plugin_name(package: Package):
        return utils.make_python_identifier(package.name) + '.py'

    @classmethod
    def _get_cli_plugin_path(cls, package: Package, command):
        pkg_loader = pkgutil.get_loader(f'{command}.plugins')
        if pkg_loader is None:
            raise PackageManagerError(f'Failed to get plugins path for {command} CLI')
        plugins_pkg_path = os.path.dirname(pkg_loader.path)
        return os.path.join(plugins_pkg_path, cls._get_cli_plugin_name(package))

    def _install_cli_plugins(self, package: Package):
        for command in ('show', 'config', 'clear'):
            self._install_cli_plugin(package, command)

    def _uninstall_cli_plugins(self, package: Package):
        for command in ('show', 'config', 'clear'):
            self._uninstall_cli_plugin(package, command)

    def _install_cli_plugin(self, package: Package, command: str):
        image_plugin_path = package.manifest['cli'][command]
        if not image_plugin_path:
            return
        host_plugin_path = self._get_cli_plugin_path(package, command)
        repotag = f'{package.repository}:latest'
        image = self.docker.get_image(repotag)
        self.docker.extract(image.id, image_plugin_path, host_plugin_path)

    def _uninstall_cli_plugin(self, package: Package, command: str):
        image_plugin_path = package.manifest['cli'][command]
        if not image_plugin_path:
            return
        host_plugin_path = self._get_cli_plugin_path(package, command)
        if os.path.exists(host_plugin_path):
            os.remove(host_plugin_path)

    @staticmethod
    def get_manager() -> 'PackageManager':
        docker_api = DockerApi(docker.from_env())
        registry_resolver = RegistryResolver()
        return PackageManager(DockerApi(docker.from_env(), ProgressManager()),
                              registry_resolver,
                              PackageDatabase.from_file(),
                              ManifestResolver(docker_api, registry_resolver),
                              ServiceCreator(FeatureRegistry(SonicDB), SonicDB),
                              device_info,
                              filelock.FileLock(PACKAGE_MANAGER_LOCK_FILE, timeout=0))
