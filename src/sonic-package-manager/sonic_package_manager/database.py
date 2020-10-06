#!/usr/bin/env python

""" Repository Database interface module. """

import typing

import yaml

from sonic_package_manager import common
from sonic_package_manager.errors import PackageManagerError, RepositoryNotFoundError
from sonic_package_manager.repository import Repository


class RepositoryDatabase:
    """ An interface to SONiC repository database """

    def __init__(self):
        """ Initialize PackageDatabase.
        Reads the content of packages.yml and loads the database.
        """

        self._repository_database = {}
        self._read_db()

    def add_repository(self,
                       name: str,
                       repository: str,
                       description: str = '',
                       default_version: typing.Optional[str] = None):
        """ Adds a new repository entry in database.

        Args:
            name: Package name.
            repository: Repository URL.
            description: Description string.
            default_version: Default version string.

        Raises:
            PackageManagerError: if repository already exists in database.
        """

        if self.has_repository(name):
            raise PackageManagerError(f'Repository {name} already exists in database')

        self._repository_database[name] = Repository(name, {
            'repository': repository,
            'description': description,
            'default-version': default_version,
        })

        self._commit_db()

    def remove_repository(self, name: str):
        """ Removes repository entry from database.

        Args:
            name: repository name.
        Raises:
            PackageManagerError: Raises when repository with the given name does not exist
                                 in the database.
        """

        if not self.has_repository(name):
            raise PackageManagerError(f'Repository {name} does not exist in database')

        repo = self.get_repository(name)

        if repo.is_installed():
            raise PackageManagerError(f'Repository {name} is installed, uninstall it first')

        self._repository_database.pop(name)

        self._commit_db()

    def update_repository(self, repo: Repository):
        """ Modify repository in the database.

        Args:
            repo: Repository object.
        Raises:
            PackageManagerError: Raises when repository with the given name does not exist
                                 in the database.
        """

        name = repo.get_name()

        if not self.has_repository(name):
            raise PackageManagerError(f'Repository {name} does not exist in database')

        self._repository_database[name] = repo
        self._commit_db()

    def get_repository(self, name: str) -> Repository:
        """ Return a repository called name.
        If the repository wan't found RepositoryNotFoundError is thrown.

        Args:
            name: Repository name.
        Returns:
            Repository object.
        Raises:
            RepositoryNotFoundError: When repository called name was not found.
        """

        try:
            repo = self._repository_database[name]
        except KeyError:
            raise RepositoryNotFoundError(name)

        return repo

    def has_repository(self, name: str) -> bool:
        """ Checks if the database contains an entry for a repository.
        called name. Returns True if the repository exists, otherwise False.

        Args:
            name: Repository name.
        Returns:
            True of the repository exists, otherwise False.
        """

        try:
            self.get_repository(name)
            return True
        except RepositoryNotFoundError:
            return False

    def is_package_installed(self, feature_name: str) -> bool:
        """ Checks if the database contains an entry for a repository called name
        and it is installed. Returns True if the package, otherwise False.

        Args:
            feature_name: Feature name
        Returns:
            True of the package is installed, otherwise False.
        """

        for repo in self:
            if not repo.is_installed():
                continue
            package = repo.get_package()
            if package.get_feature_name() == feature_name:
                return True

        return False

    def _read_db(self):
        """ Read the database file. """

        dbfile = common.get_sonic_packages_file()

        try:
            with open(dbfile) as database:
                dbcontent = yaml.safe_load(database)
        except OSError as err:
            raise PackageManagerError(f'Failed to read {dbfile}: {err}')

        for reponame, repodata in dbcontent.items():
            self._repository_database[reponame] = Repository(reponame, repodata)

    def _commit_db(self):
        """ Save the database to persistent file. """

        dbcontent = dict()
        dbfile = common.get_sonic_packages_file()

        for repo in self:
            dbcontent[repo.get_name()] = repo.get_metadata()

        try:
            with open(dbfile, 'w') as database:
                yaml.safe_dump(dbcontent, database)
        except OSError as err:
            raise PackageManagerError(f'Failed to write to {dbfile}: {err}')

    def __iter__(self):
        """ Iterates over repositories in the database.

        Yields:
            Repository: Repository object.

        """

        for name, _ in self._repository_database.items():
            yield self.get_repository(name)
