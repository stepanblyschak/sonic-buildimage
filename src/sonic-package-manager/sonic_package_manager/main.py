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
    """ Show  help message and exit process successfully. """

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


def add_options(options):
    """ Decorator to append options from
    input list to command. """

    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


class MutuallyExclusiveOption(click.Option):
    """ This options type is extended with 'mutually_exclusive'
    parameter which makes CLI to check if several options are now
    used together in single command. """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        help_string = kwargs.get('help', '')
        if self.mutually_exclusive:
            ex_str = ', '.join(self.mutually_exclusive)
            kwargs['help'] = f'{help_string} ' \
                             f'NOTE: This argument is mutually ' \
                             f'exclusive with arguments: [{ex_str}].'
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        if self.name in opts and opts[self.name] is not None:
            for opt_name in self.mutually_exclusive.intersection(opts):
                if opts[opt_name] is None:
                    continue

                raise click.UsageError(f'Illegal usage: {self.name} is mutually '
                                       f'exclusive with arguments '
                                       f'{", ".join(self.mutually_exclusive)}.')

        return super().handle_parse_result(ctx, opts, args)


PACKAGE_SOURCE_OPTIONS = [
    click.option('--from-repository',
                 help='Install package directly from image registry repository',
                 cls=MutuallyExclusiveOption,
                 mutually_exclusive=['from_tarball', 'package_expr']),
    click.option('--from-tarball',
                 type=click.Path(exists=True,
                                 readable=True,
                                 file_okay=True,
                                 dir_okay=False),
                 help='Install package from saved image tarball',
                 cls=MutuallyExclusiveOption,
                 mutually_exclusive=['from_repository', 'package_expr']),
    click.argument('package-expr',
                   type=str,
                   required=False)
]


def get_package_status(package: PackageEntry):
    """ Returns the installation status message for package. """

    if package.built_in:
        return 'Built-In'
    elif package.installed:
        return 'Installed'
    else:
        return 'Not Installed'


@click.group()
@click.pass_context
def cli(ctx):
    """ SONiC Package Manager """

    ctx.obj = PackageManager.get_manager()


@cli.group()
@click.pass_context
def repository(ctx):
    """ Repository management commands """

    pass


@cli.group()
@click.pass_context
def show(ctx):
    """ Package manager show commands """

    pass


@show.group()
@click.pass_context
def package(ctx):
    """ Package show commands """

    pass


@cli.command()
@click.pass_context
def list(ctx):
    """ List available repositories """

    table_header = ['Name', 'Repository', 'Description', 'Version', 'Status']
    table_body = []

    manager: PackageManager = ctx.obj

    try:
        for package in natsorted(manager.database):
            version = package.version or 'N/A'
            description = package.description or 'N/A'
            status = get_package_status(package)

            table_body.append([
                package.name,
                package.repository,
                description,
                version,
                status
            ])

        click.echo(tabulate.tabulate(table_body, table_header))
    except PackageManagerError as err:
        exit_cli(f'Failed to list repositories: {err}', fg='red')


@package.command()
@add_options(PACKAGE_SOURCE_OPTIONS)
@click.pass_context
@click_log.simple_verbosity_option(log)
def manifest(ctx,
             package_expr,
             from_repository,
             from_tarball):
    """ Print package manifest content """

    manager: PackageManager = ctx.obj

    try:
        source = manager.get_package_source(package_expr,
                                            from_repository,
                                            from_tarball)
        package = source.get_package()
        click.echo(json.dumps(package.manifest.unmarshal(), indent=4))
    except Exception as err:
        exit_cli(f'Failed to print manifest: {err}', fg='red')


@package.command()
@click.argument('name')
@click.option('--all', is_flag=True, help='Show all available tags in repository')
@click.option('--plain', is_flag=True, help='Plain output')
@click.pass_context
def versions(ctx, name, all, plain):
    """ Print available versions """

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
@add_options(PACKAGE_SOURCE_OPTIONS)
@click.pass_context
def changelog(ctx,
              package_expr,
              from_repository,
              from_tarball):
    """ Print package changelog """

    manager: PackageManager = ctx.obj

    try:
        source = manager.get_package_source(package_expr,
                                            from_repository,
                                            from_tarball)
        package = source.get_package()
        changelog = package.manifest['package']['changelog']

        if not changelog:
            raise PackageManagerError(f'No changelog for package {package.name}')

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
        manager.add_repository(name,
                               repository,
                               description=description,
                               default_reference=default_reference)
    except Exception as err:
        exit_cli(f'Failed to add repository {name}: {err}', fg='red')


@repository.command()
@click.argument("name")
@click.pass_context
@root_privileges_required
def remove(ctx, name):
    """ Remove package from database. """

    manager: PackageManager = ctx.obj

    try:
        manager.remove_repository(name)
    except Exception as err:
        exit_cli(f'Failed to remove repository {name}: {err}', fg='red')


@cli.command()
@click.option('-f', '--force',
              is_flag=True,
              help='Force installation by ignoring failures')
@click.option('-y', '--yes',
              is_flag=True,
              help='Automatically answer yes on prompts')
@click.option('--enable',
              is_flag=True,
              help='Set the default state of the feature to enabled '
                   'and enable feature right after installation. '
                   'NOTE: user needs to execute "config save -y" to make '
                   'this setting persistent')
@click.option('--default-owner',
              type=click.Choice(['local', 'kube']),
              default='local',
              help='Default owner configuration setting for a feature')
@add_options(PACKAGE_SOURCE_OPTIONS)
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def install(ctx,
            package_expr,
            from_repository,
            from_tarball,
            force,
            yes,
            enable,
            default_owner):
    """ Install package """

    manager: PackageManager = ctx.obj

    package_source = package_expr or from_repository or from_tarball

    if not yes and not force:
        click.confirm(f'{package_source} is going to be installed, '
                      f'continue?', abort=True, show_default=True)

    install_opts = {
        'force': force,
        'enable': enable,
        'default_owner': default_owner,
    }

    try:
        manager.install(package_expr,
                        from_repository,
                        from_tarball,
                        **install_opts)
    except Exception as err:
        exit_cli(f'Failed to install {package_source}: {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('-y', '--yes', is_flag=True)
@add_options(PACKAGE_SOURCE_OPTIONS)
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def upgrade(ctx,
            package_expr,
            from_repository,
            from_tarball,
            force,
            yes):
    """ Upgrade package """

    manager: PackageManager = ctx.obj

    package_source = package_expr or from_repository or from_tarball

    if not yes and not force:
        click.confirm(f'Package is going to be upgraded with {package_source}, '
                      f'continue?', abort=True, show_default=True)

    try:
        manager.upgrade(package_expr,
                        from_repository,
                        from_tarball,
                        force=force)
    except Exception as err:
        exit_cli(f'Failed to upgrade {package_source}: {err}', fg='red')
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
    """ Uninstall package """

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
@click.option('--dockerd-socket', type=click.Path())
@click.argument('database', type=click.Path())
@click.pass_context
@click_log.simple_verbosity_option(log)
@root_privileges_required
def migrate(ctx, database, force, yes, dockerd_socket):
    """ Migrate packages from the given database file """

    manager: PackageManager = ctx.obj

    if not yes and not force:
        click.confirm('Continue with package migration?', abort=True, show_default=True)

    try:
        manager.migrate_packages(PackageDatabase.from_file(database), dockerd_socket)
    except Exception as err:
        exit_cli(f'Failed to migrate packages {err}', fg='red')
    except KeyboardInterrupt:
        exit_cli(f'Operation canceled by user', fg='red')


if __name__ == "__main__":
    cli()
