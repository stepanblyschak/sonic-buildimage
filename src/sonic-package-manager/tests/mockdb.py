import mock
import semver

from sonic_package_manager.repository import *
from sonic_package_manager.database import *

class MockDatabase(RepositoryDatabase):
    def __init__(self):
        self._repository_database = {
            'test1': create_mock_repo({
                'name': 'test1',
                'repository': 'docker-test1',
                'default-version': semver.Version.parse('1.1.1'),
                'installed-version': semver.Version.parse('1.1.1'),
                'status': 'installed'
            },
            [], []),
            'test2': create_mock_repo({
                'name': 'test2',
                'repository': 'docker-test2',
                'default-version': semver.Version.parse('1.1.1'),
                'installed-version': semver.Version.parse('1.1.1'),
                'status': 'installed'
            },
            [], ['test-conflict >1.5.2'])
        }


def create_mock_repo(metadata, dependencies, conflicts):
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    repo.get_name = mock.Mock(return_value=metadata['name'])
    repo.get_repository = mock.Mock(return_value=metadata['repository'])
    repo.get_default_version = mock.Mock(return_value=metadata['default-version'])
    repo.get_installed_version = mock.Mock(return_value=metadata.get('installed-version'))
    repo.is_installed = mock.Mock(return_value=metadata.get('status') == 'installed')
    repo.get_package = mock.Mock(return_value=package)
    package.get_conflicts = mock.Mock(return_value=[
        parse_package_constraint(conflict) for conflict in conflicts
    ])
    package.get_dependencies = mock.Mock(return_value=[
        parse_package_constraint(dependency) for dependency in dependencies
    ])

    return repo

