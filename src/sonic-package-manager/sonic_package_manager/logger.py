#!/usr/bin/env python

from __future__ import print_function

import sys
import logging

__log = logging.getLogger("sonic-package-manager")
__log.setLevel(logging.INFO)
__log.addHandler(logging.StreamHandler(sys.stdout))

def get_logger():
    return __log
