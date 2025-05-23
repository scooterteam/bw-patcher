#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# You are free to:
# - Share — copy and redistribute the material in any medium or format
# - Adapt — remix, transform, and build upon the material
#
# Under the following terms:
# - Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
# - NonCommercial — You may not use the material for commercial purposes.
# - ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
#

import crcmod

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern

class ES32Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def _calc_speed(cls, speed, factor=20.9, size=2):
        return int(factor * speed).to_bytes(size, 'little')

    def fix_checksum(self):
        sig = 'SZMC-ES-ZM-'.encode()
        ofs_ = find_pattern(self.data, sig)
        
        ofs = ofs_ + 0x20
        size = int.from_bytes(
            self.data[ofs-0x2a:ofs-0x28],
            byteorder='big'
        )
        pre = self.data[ofs:ofs+2]
        post = self._compute_checksum(
            self.data,
            offset=ofs+0x50,
            size=size
        )
        self.data[ofs:ofs+2] = post[:2]
        print(hex(ofs_), hex(ofs))

        res = super().fix_checksum(ofs_ - 0x10, size)
        return [("fix_checksum", hex(ofs), pre.hex(), post.hex()), res]