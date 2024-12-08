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

import keystone

from bwpatcher.utils import find_pattern


class CorePatcher():
    def __init__(self, data):
        self.data = bytearray(data)
        self.ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)

    def assembly(self, code):
        return bytes(self.ks.asm(code)[0])

    def dashboard_max_speed(self, speed: float):
        raise NotImplementedError()

    def speed_limit_drive(self, kmh: float):
        raise NotImplementedError()

    def remove_speed_limit_sport(self):
        raise NotImplementedError()

    def region_free(self):
        raise NotImplementedError()

    def fix_checksum(self):
        raise NotImplementedError()

    def fake_drv_version(self, firmware_version: str):
        if not firmware_version.isdigit():
            raise ValueError(f"Firmware version must contain only digits: {firmware_version}")
        if len(firmware_version) != 4:
            raise ValueError(f"Firmware version must have 4 digits: {firmware_version}")

        sig = [0x6F, 0x6B, 0x0D, None, None, None, None, 0x0D, 0x65, 0x72, 0x72, 0x6F, 0x72]
        ofs = find_pattern(self.data, sig) + 3
        pre = self.data[ofs:ofs+4]
        post = firmware_version.encode("ascii")
        self.data[ofs:ofs+4] = post
        return [("fake_drv_version", hex(ofs), pre.hex(), post.hex())]

    def motor_start_speed(self, speed: int):
        raise NotImplementedError()

