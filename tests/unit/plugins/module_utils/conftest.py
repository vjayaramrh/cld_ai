# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""pytest configuration for module_utils unit tests.

Adds this directory and the sibling ``modules`` directory to ``sys.path`` so the
shared ``ansible_helpers`` (which lives alongside the module tests) can be
imported here without duplication, regardless of how ansible-test lays the
collection out under ``ansible_collections/``.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "modules"))
