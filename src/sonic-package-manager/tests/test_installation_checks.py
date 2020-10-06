import pytest
import mock

from sonic_package_manager.database import *
from sonic_package_manager.errors import PackageSonicRequirementError, PackageDependencyError, PackageConflictError
from sonic_package_manager.install import check_sonic_version_compatibility, check_installation
from sonic_package_manager.package import *
from sonic_package_manager.constraint import *

from tests.mockdb import create_mock_repo, MockDatabase


@pytest.mark.parametrize(
    "req,sonicver,raises",
    [
        (">1.2.0", "1.1.1", True),
        ("<=1.2.0", "1.1.1", False),
    ]
)
def test_sonic_base_requirement_check(req, sonicver, raises):
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    package.get_sonic_version_constraint = mock.Mock(return_value=semver.parse_constraint(req))
    repo.get_name = mock.Mock(return_value='test')
    repo.get_package = mock.Mock(return_value=package)
    if raises:
        with pytest.raises(PackageSonicRequirementError):
            check_sonic_version_compatibility(repo, semver.Version.parse(sonicver))
    else:
        check_sonic_version_compatibility(repo, semver.Version.parse(sonicver))

@pytest.mark.parametrize('pkgname,depends,breaks,version,error',
    [
        ('test', ['non-existing'], [], '2.0.0', 'dependency'),
        ('test', [], ['test1'], '2.0.0', 'conflict'),
        ('test', ['test1 < 5.0'], [], '2.0.0', ''),
        ('test', ['test1 > 5.0'], [], '2.0.0', 'dependency'),
        ('test-conflict', [], [], '2.0.0', 'conflict'),
        ('test-conflict', [], [], '1.0.0', ''),
    ])
def test_installation_check(pkgname, depends, breaks, version, error):
    repo = create_mock_repo(
        {'name': pkgname,
         'repository': 'docker-test',
         'default-version': '2.0.0'},
        depends, breaks)
    if error == 'dependency':
        with pytest.raises(PackageDependencyError):
            check_installation(MockDatabase(), repo, semver.Version.parse(version))
    elif error == 'conflict':
        with pytest.raises(PackageConflictError):
            check_installation(MockDatabase(), repo, semver.Version.parse(version))
    else:
        check_installation(MockDatabase(), repo, semver.Version.parse(version))

