#!/usr/bin/env python

from unittest import mock

from click.testing import CliRunner

from sonic_package_manager import main, repository, package


def test_show_changelog():
    """ Test case for "sonic-package-manager package show changelog [NAME]" """

    runner = CliRunner()
    changelog = {
        '1.0.0': [
            'Initial release',
        ],
        '1.0.1': [
            'Bug fix',
        ],
        '1.1.2': [
            'Added functionality',
            'Minor improvements',
        ]
    }

    repo = mock.Mock(repository.Repository)
    pkg = mock.Mock(package.Package)
    pkg.get_changelog = mock.Mock(return_value=changelog)
    repo.get_package = mock.Mock(return_value=pkg)
    repo.is_installed = mock.Mock(return_value=True)

    expected_output = """\
1.0.0:
    • Initial release

1.0.1:
    • Bug fix

1.1.2:
    • Added functionality
    • Minor improvements

"""

    with mock.patch('sonic_package_manager.main.RepositoryDatabase') as mocked:
        db = mocked.return_value
        db.get_repository.return_value = repo
        result = runner.invoke(main.package.commands['show'].commands['changelog'], ['test'])

    assert result.exit_code == 0
    assert result.output == expected_output


def test_show_changelog_no_changelog():
    """ Test case for "sonic-package-manager package show changelog [NAME]"
    when there is no changelog provided by package. """

    runner = CliRunner()

    repo = mock.Mock(repository.Repository)
    pkg = mock.Mock(package.Package)
    pkg.get_changelog = mock.Mock(return_value=None)
    repo.get_package = mock.Mock(return_value=pkg)
    repo.is_installed = mock.Mock(return_value=True)

    expected_output = 'Failed to print package changelog: No changelog for package test\n'

    with mock.patch('sonic_package_manager.main.RepositoryDatabase') as mocked:
        db = mocked.return_value
        db.get_repository.return_value = repo
        result = runner.invoke(main.package.commands['show'].commands['changelog'], ['test'])

    assert result.exit_code == 1
    assert result.output == expected_output
