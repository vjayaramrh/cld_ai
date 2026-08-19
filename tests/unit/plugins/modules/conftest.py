# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Vishwanath Jayaraman (@vjayaramrh)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""pytest configuration for module unit tests.

Adds this directory to ``sys.path`` so tests can ``import ansible_helpers``
directly regardless of how ansible-test lays the collection out under
``ansible_collections/``.
"""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
