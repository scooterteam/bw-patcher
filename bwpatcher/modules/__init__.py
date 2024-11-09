#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024 ScooterTeam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import glob

from os.path import dirname, basename, isfile


# Get all modules to import from directory
# https://stackoverflow.com/a/47473360
def _get_all_modules():
    mod_paths = glob.glob(dirname(__file__) + '/*.py')
    return [
        basename(f)[:-3] for f in mod_paths
        if isfile(f) and f.endswith('.py') and not f.endswith('__init__.py')
    ]


ALL_MODULES = sorted(_get_all_modules())
