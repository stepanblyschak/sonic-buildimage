#!/usr/bin/env python

import pytest

from sonic_package_manager.constraint import *

@pytest.mark.parametrize(
    'inputstr,result',
    [
        ('database', PackageConstraint('database', semver.parse_constraint('*'))),
        ('database 1.0.0', PackageConstraint('database', semver.parse_constraint('1.0.0'))),
        ('database >1.2.3 < 2.0.1-alpha+23', PackageConstraint('database', semver.parse_constraint('>1.2.3 < 2.0.1-alpha+23'))),
    ]
)
def test_constrain_parsing(inputstr, result):
    assert parse_package_constraint(inputstr) == result
