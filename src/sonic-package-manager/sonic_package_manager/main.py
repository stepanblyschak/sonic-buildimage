#!/usr/bin/env python

import os
import sys
import functools
import click
import tabulate
import natsort
import yaml
import docker

from sonic_package_manager.install import install_package, uninstall_package

from sonic_package_manager.database import RepositoryDatabase
from sonic_package_manager.errors import *


def root_privileged_required(func):
    ''' Decorates a function, so that the function is invoked
    only if the user is root. '''

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        ''' Wrapper around func. '''

        if os.geteuid() != 0:
            click.secho('Root privileges required for this operation', fg='red')
            sys.exit(1)

        return func(*args, **kwargs)

    return wrapped_function


@click.group()
def cli():
    ''' SONiC Package Manager. '''

    pass


@cli.group()
def repository():
    ''' Repository management commands. '''

    pass


@repository.command()
def list():
    ''' List available repositories. '''

    table_header = ["Name", "Repository", "Description", "Version", "Status"]
    table_body = []

    try:
        db = RepositoryDatabase()
    except PackageManagerError as err:
        click.secho('Failed to list repositories: {}'.format(err), fg='red')
        sys.exit(1)

    for repo in db:
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


@cli.command()
@click.argument('name')
def show_manifest(name):
    ''' Print the manifest content. '''

    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        if not repo.is_installed():
            raise PackageManagerError('{} is not installed'.format(name))
        pkg = repo.get_package()
        click.echo(yaml.safe_dump(pkg.get_manifest()))
    except PackageManagerError as err:
        click.secho('Failed to describe package {}: {}'.format(name, err), fg='red')
        sys.exit(1)


@repository.command()
@click.argument('name', type=str)
@click.argument('repository', type=str)
@click.option('--default-version', type=str)
@click.option('--description', type=str)
@root_privileged_required
def add(name, repository, default_version, description):
    ''' Add a new repository to database. '''

    try:
        db = RepositoryDatabase()
        db.add_repository(name, repository, description=description, default_version=default_version)
    except PackageManagerError as err:
        click.secho('Failed to add repository {}: {}'.format(name, err), fg='red')
        sys.exit(1)


@repository.command()
@click.argument("name")
@root_privileged_required
def remove(name):
    ''' Remove a package from database. '''

    try:
        db = RepositoryDatabase()
        db.remove_repository(name)
    except PackageManagerError as err:
        click.secho('Failed to remove repository {}: {}'.format(name, err), fg='red')
        sys.exit(1)


@cli.command()
@click.option('--force', is_flag=True)
@click.argument('name')
@root_privileged_required
def install(name, force):
    ''' Install a package. '''

    click.secho('Request to install {}. force: {}'.format(name, force), fg='green')
    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        install_package(db, repo, force=force)
    except PackageManagerError as err:
        click.secho('Failed to install package {}: {}'.format(name, err), fg='red')
        sys.exit(1)
    click.secho('Package {} succesfully installed!'.format(name), fg='green')


@cli.command()
@click.option('--force', is_flag=True)
@click.argument('name')
@root_privileged_required
def uninstall(name, force):
    ''' Uninstall a package. '''

    click.secho('Request to uninstall {}. force: {}'.format(name, force), fg='green')
    try:
        db = RepositoryDatabase()
        repo = db.get_repository(name)
        uninstall_package(db, repo, force=force)
    except PackageManagerError as err:
        click.secho('Failed to uninstall package {}: {}'.format(name, err), fg='red')
        sys.exit(1)
    click.secho('Package {} succesfully uninstalled!'.format(name), fg='green')


if __name__ == "__main__":
    cli()

