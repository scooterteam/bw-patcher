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

from bwpatcher.modules import ALL_MODULES
from bwpatcher.utils import patch_map, patch_firmware


parser = argparse.ArgumentParser()
parser.add_argument("model", help="Dev name of scooter.", type=str.lower, choices=ALL_MODULES)
parser.add_argument("infile")
parser.add_argument("outfile")
parser.add_argument("patches", type=str, help="The patches that are to be applied. Choose from: " + ', '.join(patch_map.keys()))
args = parser.parse_args()

with open(args.infile, 'rb') as fh:
    data = fh.read()

output_data = patch_firmware(args.model, data, args.patches.split(","))

with open(args.outfile, 'wb') as fh:
    fh.write(output_data)
