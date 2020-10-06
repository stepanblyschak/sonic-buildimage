#!/usr/bin/env python

import functools
import os
import sys
import typing

import click
import click_log
import tabulate
import yaml
from natsort import natsorted

from sonic_package_manager import errors
from sonic_package_manager.database import RepositoryDatabase
from sonic_package_manager.install import install_package, uninstall_package
from sonic_package_manager.logger import get_logger


BULLET_UC = '\u2022'


def exit_cli(*args, **kwargs):
    """ Print a message and exit with rc 1. """

    click.secho(*args, **kwargs)
    sys.exit(1)


def root_privileged_required(func: typing.Callable) -> typing.Callable:
    """ Decorates a function, so that the function is invoked
    only if the user is root. """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        """ Wrapper around func. """

        if os.geteuid() != 0:
            exit_cli('Root privileges required for this operation', fg='red')

        return func(*args, **kwargs)

    return wrapped_function


@click.group()
def cli():
    """ SONiC Package Manager. """

    pass


@cli.group()
def repository():
    """ Repository management commands. """

    pass


@cli.group()
def package():
    """ SONiC Package commands. """

    pass


@package.group()
def show():
    """ Package show CLI commands. """

    pass


@cli.command()
def list():
    """ List available repositories. """

    table_header = ["Name", "Repository", "Description", "Version", "Status"]
    table_body = []

    try:
        db = RepositoryDatabase()
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to list repositories: {err}', fg='red')

    for repo in natsorted(db):
        name = repo.get_name()
        repository = repo.get_repository()
        description = repo.get_description()
        if repo.is_installed():
            version = repo.get_installed_version()
        else:
            version = 'N/A'
        version = str(version)
        status = repo.get_status()

        table_body.append([
            name,
            repository,
            description,
            version,
            status,
        ])

    click.echo(tabulate.tabulate(table_body, table_header))


@show.command()
@click.argument('name')
def manifest(name):
    """ Print the manifest content. """

    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        if not repo.is_installed():
            raise errors.PackageManagerError(f'{name} is not installed')
        pkg = repo.get_package()
        click.echo(yaml.safe_dump(pkg.get_manifest()))
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to describe package {name}: {err}', fg='red')


@show.command()
@click.argument('name')
def changelog(name):
    """ Print the package changelog. """

    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        if not repo.is_installed():
            raise errors.PackageManagerError(f'{name} is not installed')
        pkg = repo.get_package()
        changelog = pkg.get_changelog()

        if changelog is None:
            raise errors.PackageManagerError(f'No changelog for package {name}')

        for version in sorted(changelog):
            click.secho(f'{version}:', fg='green', bold=True)
            for line in changelog[version]:
                click.secho(f'    {BULLET_UC} {line}', bold=True)
            click.secho('')

    except errors.PackageManagerError as err:
        exit_cli(f'Failed to print package changelog: {err}', fg='red')


@repository.command()
@click.argument('name', type=str)
@click.argument('repository', type=str)
@click.option('--default-version', type=str)
@click.option('--description', type=str)
@root_privileged_required
def add(name, repository, default_version, description):
    """ Add a new repository to database. """

    try:
        db = RepositoryDatabase()
        db.add_repository(name, repository, description=description, default_version=default_version)
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to add repository {name}: {err}', fg='red')


@repository.command()
@click.argument("name")
@root_privileged_required
def remove(name):
    """ Remove a package from database. """

    try:
        db = RepositoryDatabase()
        db.remove_repository(name)
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to remove repository {name}: {err}', fg='red')


@cli.command()
@click.option('--force', is_flag=True)
@click.option('--yes', is_flag=True)
@click.argument('pattern')
@click_log.simple_verbosity_option(get_logger())
@root_privileged_required
def install(pattern, force, yes):
    """ Install a package. """

    name = pattern
    version = None

    if '==' in pattern:
        name, version = pattern.split('==', 1)

    (not yes or force) or click.confirm(
        f'Package {pattern} is going to be installed, continue?', abort=True, show_default=True)

    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        install_package(db, repo, version=version, force=force)
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to install package {name}: {err}', fg='red')


@cli.command()
@click.option('--force', is_flag=True)
@click.option('--yes', is_flag=True)
@click.argument('name')
@click_log.simple_verbosity_option(get_logger())
@root_privileged_required
def uninstall(name, force, yes):
    """ Uninstall a package. """

    (not yes or force) or click.confirm(
        f'Package {name} is going to be uninstalled, continue?', abort=True, show_default=True)

    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        uninstall_package(db, repo, force=force)
    except errors.PackageManagerError as err:
        exit_cli(f'Failed to uninstall package {name}: {err}', fg='red')


if __name__ == "__main__":
    cli()
