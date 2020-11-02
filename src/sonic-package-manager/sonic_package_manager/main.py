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
    """ PackageEntry management commands. """

    pass


@cli.group()
@click.pass_context
def package(ctx):
    """ SONiC Package commands. """

    pass


@package.group()
@click.pass_context
def show(ctx):
    """ Package show CLI commands. """

    pass


@cli.command()
@click.pass_context
def list(ctx):
    """ List available repositories. """

    table_header = ["Name", "PackageEntry", "Description", "Version", "Status"]
    table_body = []

    manager: PackageManager = ctx.obj

    try:
        db = manager.get_database()
        for package in natsorted(db):
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


@show.command()
@click.argument('name')
@click.pass_context
def manifest(ctx, name):
    """ Print the manifest content. """

    try:
        manager: PackageManager = ctx.obj
        package = manager.get_package(name)
        click.echo(json.dumps(package.manifest.unmarshal(), indent=4))
    except Exception as err:
        exit_cli(f'Failed to describe package {name}: {err}', fg='red')


@show.command()
@click.argument('name')
@click.option('--all', is_flag=True, help='Show all available tags in repository')
@click.option('--plain', is_flag=True, help='Plain output')
@click.pass_context
def versions(ctx, name, all, plain):
    """ Print available versions. """

    try:
        manager: PackageManager = ctx.obj
        versions = manager.get_available_versions(name, all)
        for version in versions:
            if not plain:
                click.secho(f'{BULLET_UC} ', bold=True, fg='green', nl=False)
            click.secho(f'{version}')
    except Exception as err:
        exit_cli(f'Failed to get package versions {name}: {err}', fg='red')


@show.command()
@click.argument('name')
@click.pass_context
def changelog(ctx, name):
    """ Print the package changelog. """

    pass
    # try:
    #     db = PackageDatabase()
    #     repo = db.get_package(name)
    #     if not repo.is_installed():
    #         raise PackageManagerError(f'{name} is not installed')
    #     pkg = repo.get_package()
    #     changelog = pkg.get_changelog()
    #
    #     if changelog is None:
    #         raise errors.PackageManagerError(f'No changelog for package {name}')
    #
    #     for version in sorted(changelog):
    #         click.secho(f'{version}:', fg='green', bold=True)
    #         for line in changelog[version]:
    #             click.secho(f'    {BULLET_UC} {line}', bold=True)
    #         click.secho('')
    #
    # except errors.PackageManagerError as err:
    #     exit_cli(f'Failed to print package changelog: {err}', fg='red')


@repository.command()
@click.argument('name', type=str)
@click.argument('repository', type=str)
@click.option('--default-reference', type=str)
@click.option('--description', type=str)
@click.pass_context
@root_privileged_required
def add(ctx, name, repository, default_reference, description):
    """ Add a new repository to database. """

    manager: PackageManager = ctx.obj

    try:
        manager.add_package(name, repository, description=description, default_reference=default_reference)
    except Exception as err:
        exit_cli(f'Failed to add repository {name}: {err}', fg='red')


@repository.command()
@click.argument("name")
@click.pass_context
@root_privileged_required
def remove(ctx, name):
    """ Remove a package from database. """

    manager: PackageManager = ctx.obj

    try:
        manager.remove_package(name)
    except Exception as err:
        exit_cli(f'Failed to remove repository {name}: {err}', fg='red')


@cli.command()
@click.option('--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.option('--manifest',
              help="manifest file used to override package manifest",
              type=click.Path())
@click.argument('pattern')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileged_required
def install(ctx, pattern, force, yes, manifest):
    """ Install a package. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm(f'Package {pattern} is going to be installed, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.install(pattern, force)
    except Exception as err:
        exit_cli(f'Failed to install package {pattern}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.option('--manifest',
              help="manifest file used to override package manifest",
              type=click.Path())
@click.argument('pattern')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileged_required
def upgrade(ctx, pattern, force, yes, manifest):
    """ Install a package. """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm(f'Package is going to be upgraded to {pattern}, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.upgrade(pattern, force)
    except Exception as err:
        exit_cli(f'Failed to upgrade package {pattern}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('name')
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileged_required
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
@click.option('--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@click.argument('database', type=click.Path())
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileged_required
def migrate(ctx, database, force, yes):
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
