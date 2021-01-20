#!/usr/bin/env python

import functools
import json
import os
import sys
import typing

import click
import click_log
import tabulate
from natsort import natsorted

from sonic_package_manager.database import PackageEntry, PackageDatabase
from sonic_package_manager.errors import PackageManagerError
from sonic_package_manager.logger import log
from sonic_package_manager.manager import PackageManager

BULLET_UC = '\u2022'


def exit_cli(*args, **kwargs):
    """ Print a message and exit with rc 1. """

    click.secho(*args, **kwargs)
    sys.exit(1)


def show_help(ctx):
    click.echo(ctx.get_help())
    ctx.exit(0)


def root_privileges_required(func: typing.Callable) -> typing.Callable:
    """ Decorates a function, so that the function is invoked
    only if the user is root. """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        """ Wrapper around func. """

        if os.geteuid() != 0:
            exit_cli('Root privileges required for this operation', fg='red')

        return func(*args, **kwargs)

    return wrapped_function


def get_package_status(package: PackageEntry):
    if package.built_in:
        return 'Built-In'
    elif package.installed:
        return 'Installed'
    else:
        return 'Not Installed'


@click.group()
@click.pass_context
def cli(ctx):
    """ SONiC Package Manager. """

    ctx.obj = PackageManager.get_manager()


@cli.group()
@click.pass_context
def repository(ctx):
    """ Repository management commands. """

    pass


@cli.group()
@click.pass_context
def show(ctx):
    """ SONiC package manager show commands. """

    pass


@show.group()
@click.pass_context
def package(ctx):
    """ Package show CLI commands. """

    pass


@cli.command()
@click.pass_context
def list(ctx):
    """ List available repositories. """

    table_header = ["Name", "Repository", "Description", "Version", "Status"]
    table_body = []

    manager: PackageManager = ctx.obj

    try:
        for package in natsorted(manager.database):
            version = package.version or 'N/A'
            status = get_package_status(package)

            table_body.append([
                package.name,
                package.repository,
                package.description,
                version,
                status
            ])

        click.echo(tabulate.tabulate(table_body, table_header))
    except PackageManagerError as err:
        exit_cli(f'Failed to list repositories: {err}', fg='red')


@package.command()
@click.argument('expression')
@click.pass_context
@click_log.simple_verbosity_option(log)
def manifest(ctx, expression):
    """ Print the manifest content. """

    manager: PackageManager = ctx.obj

    try:
        package = manager.resolve_package(expression)
        click.echo(json.dumps(package.manifest.unmarshal(), indent=4))
    except Exception as err:
        exit_cli(f'Failed to print manifest for {expression}: {err}', fg='red')


@package.command()
@click.argument('name')
@click.option('--all', is_flag=True, help='Show all available tags in repository')
@click.option('--plain', is_flag=True, help='Plain output')
@click.pass_context
def versions(ctx, name, all, plain):
    """ Print available versions. """

    try:
        manager: PackageManager = ctx.obj
        versions = manager.get_package_available_versions(name, all)
        for version in versions:
            if not plain:
                click.secho(f'{BULLET_UC} ', bold=True, fg='green', nl=False)
            click.secho(f'{version}')
    except Exception as err:
        exit_cli(f'Failed to get package versions for {name}: {err}', fg='red')


@package.command()
@click.argument('expression')
@click.pass_context
def changelog(ctx, expression):
    """ Print the package changelog. """

    manager: PackageManager = ctx.obj

    try:
        package = manager.resolve_package(expression)
        changelog = package.manifest['package']['changelog']

        if not changelog:
            raise PackageManagerError(f'No changelog for package {expression}')

        for version, entry in changelog.items():
            author = entry.get('author') or 'N/A'
            email = entry.get('email') or 'N/A'
            changes = entry.get('changes') or []
            date = entry.get('date') or 'N/A'
            click.secho(f'{version}:\n', fg='green', bold=True)
            for line in changes:
                click.secho(f'    {BULLET_UC} {line}', bold=True)
            click.secho(f'\n        {author} '
                        f'({email}) {date}', fg='green', bold=True)
            click.secho('')

    except Exception as err:
        exit_cli(f'Failed to print package changelog: {err}', fg='red')


@repository.command()
@click.argument('name', type=str)
@click.argument('repository', type=str)
@click.option('--default-reference', type=str)
@click.option('--description', type=str)
@click.pass_context
@root_privileges_required
def add(ctx, name, repository, default_reference, description):
    """ Add a new repository to database. """

    manager: PackageManager = ctx.obj

    try:
        manager.add_repository(name, repository, description=description, default_reference=default_reference)
    except Exception as err:
        exit_cli(f'Failed to add repository {name}: {err}', fg='red')


@repository.command()
@click.argument("name")
@click.pass_context
@root_privileges_required
def remove(ctx, name):
    """ Remove a package from database. """

    manager: PackageManager = ctx.obj

    try:
        manager.remove_repository(name)
    except Exception as err:
        exit_cli(f'Failed to remove repository {name}: {err}', fg='red')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('expression')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def install(ctx, expression, force, yes):
    """ Install a package. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm(f'Package {expression} is going to be installed, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.install(expression, force)
    except Exception as err:
        exit_cli(f'Failed to install package {expression}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('expression')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def upgrade(ctx, expression, force, yes):
    """ Upgrade a package. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm(f'Package is going to be upgraded to {expression}, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.upgrade(expression, force)
    except Exception as err:
        exit_cli(f'Failed to upgrade package {expression}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('name')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def uninstall(ctx, name, force, yes):
    """ Uninstall a package. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm(f'Package {name} is going to be uninstalled, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.uninstall(name, force)
    except Exception as err:
        exit_cli(f'Failed to uninstall package {name}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('database', type=click.Path())
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def migrate(ctx, database, force, yes):
    """ Migrate SONiC packages from the given database file. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm('Continue with package migration?', abort=True, show_default=True)

    try:
        manager.migrate_packages(PackageDatabase.from_file(database))
    except Exception as err:
        exit_cli(f'Failed to migrate packages {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


if __name__ == "__main__":
    cli()
