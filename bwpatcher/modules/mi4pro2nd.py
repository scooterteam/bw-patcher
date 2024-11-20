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

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern


class Mi4pro2ndPatcher(CorePatcher):
    CHK_CONST = 0x1021

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def __compute_checksum(cls, data, offset, size):
        def checksum(param_1: int, param_2: int) -> int:
            param_1 = (param_2 << 8) ^ param_1
            for _ in range(8):
                if (param_1 & 0x8000) != 0:
                    param_1 = (param_1 << 1) ^ cls.CHK_CONST
                else:
                    param_1 = param_1 << 1
                param_1 &= 0xFFFF
            return param_1

        data = data[offset:]
        if size > len(data):
            raise Exception("Error: File is shorter than expected range.")

        chk = 0
        for i in range(0, size):
            chk = checksum(chk, data[i])
        return chk.to_bytes(2, byteorder='big')

    def fix_checksum(self):
        sig = 'SZMC-ES-ZM-0283M'.encode()
        ofs = find_pattern(self.data, sig) + 0x20
        size = int.from_bytes(
            self.data[ofs-0x2a:ofs-0x28],
            byteorder='big'
        )
        pre = self.data[ofs:ofs+2]
        post = self.__compute_checksum(
            self.data,
            offset=ofs+0x50,
            size=size
        )
        self.data[ofs:ofs+2] = post[:2]

        return ("fix_checksum", hex(ofs), pre.hex(), post.hex())

    def region_free(self):
        res = []

        sig = [0x9c, 0xa7, 0x00, 0x00, 0x22, 0x03, 0x00, 0x20]
        ofs = find_pattern(self.data, sig)
        for i in range(7):
            ofs += 4
            pre = self.data[ofs:ofs+4]
            post = b'\x21\x03\x00\x20'
            self.data[ofs:ofs+4] = post
            res += [(f"region_free_{i}", hex(ofs), pre.hex(), post.hex())]

        sig = [0x60, 0x8b, 0x60, 0x82, 0x56, 0x48, 0x00, 0x78]
        ofs = find_pattern(self.data, sig) + len(sig)
        pre = self.data[ofs:ofs+2]
        post = self.assembly("cmp r0,#0xff")
        self.data[ofs:ofs+2] = post
        res += [("region_free_fix", hex(ofs), pre.hex(), post.hex())]

        return res

    def remove_speed_limit_sport(self):
        res = []

        sig = [0x00, 0x00, 0xa1, 0x01, 0x0a, 0x02, 0xa1, 0x01]
        ofs = find_pattern(self.data, sig)
        post = b'\xff\x02'
        for i in range(11):
            ofs += 2
            pre = self.data[ofs:ofs+2]
            self.data[ofs:ofs+2] = post
            res += [(f"remove_sls_{i}", hex(ofs), pre.hex(), post.hex())]

        return res

    def fake_drv_version(self, firmware_version: str):
        raise NotImplementedError("Not implemented for 4Pro2nd")
