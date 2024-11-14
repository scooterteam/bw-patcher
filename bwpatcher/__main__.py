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

import argparse

from importlib import import_module

from bwpatcher.modules import ALL_MODULES
from bwpatcher.utils import SignatureException

parser = argparse.ArgumentParser()
parser.add_argument("model", help="Dev name of scooter.", type=str.lower, choices=ALL_MODULES)
parser.add_argument("infile")
parser.add_argument("outfile")
parser.add_argument("patches", help="The patches that are to be applied.")
args = parser.parse_args()

with open(args.infile, 'rb') as fh:
    data = fh.read()

module = import_module(f"bwpatcher.modules.{args.model}")
patcher_class = getattr(module, f"{args.model.capitalize()}Patcher")
patcher = patcher_class(data)

patches = {
    "rsls": patcher.remove_speed_limit_sport,
    "dms": patcher.dashboard_max_speed,
    "sld": patcher.speed_limit_drive,
    "rfm": patcher.region_free,
    "chk": patcher.fix_checksum,
}

for patch in args.patches.split(','):
    value = None
    if '=' in patch:
        patch, value = patch.split('=')
        value = float(value)
    if patch in patches:
        try:
            if value:
                print(patches[patch](value))
            else:
                print(patches[patch]())
        except SignatureException:
            print(f"{patch.upper()} can't be applied")

    else:
        print(f"{patch.upper()} doesn't exist")

with open(args.outfile, 'wb') as fh:
    fh.write(patcher.data)
