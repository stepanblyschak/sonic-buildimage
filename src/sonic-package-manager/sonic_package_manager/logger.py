#!/usr/bin/env python

from __future__ import print_function

import sys
import logging

__log = logging.getLogger("sonic-package-manager")
__log.setLevel(logging.INFO)
__sh = logging.StreamHandler(sys.stdout)
__sh.setFormatter(logging.Formatter(' -- %(message)s'))
__log.addHandler(__sh)

def get_logger():
    return __log
