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

from importlib import import_module


class SignatureException(Exception):
    pass


patch_map = {
    "rsls": lambda patcher: patcher.remove_speed_limit_sport,
    "dms": lambda patcher: patcher.dashboard_max_speed,
    "sld": lambda patcher: patcher.speed_limit_drive,
    "sls": lambda patcher: patcher.speed_limit_sport,
    "rfm": lambda patcher: patcher.region_free,
    "fdv": lambda patcher: patcher.fake_drv_version,
    "chk": lambda patcher: patcher.fix_checksum,
    "mss": lambda patcher: patcher.motor_start_speed,
}


def patch_firmware(model: str, data: bytes, patches: list):
    # CHK patch must always come last for 4pro2nd
    if model == "mi4pro2nd" and patches[-1] != "chk":
        patches.append("chk")

    module = import_module(f"bwpatcher.modules.{model}")
    patcher_class = getattr(module, f"{model.capitalize()}Patcher")
    patcher = patcher_class(data)

    for patch in patches:
        value = None
        if '=' in patch:
            patch, value = patch.split('=')
            if patch != 'fdv':
                value = float(value)

        if patch in patch_map:
            try:
                if value:
                    res = patch_map[patch](patcher)(value)
                else:
                    res = patch_map[patch](patcher)()
                print(res)
            except SignatureException:
                print(f"{patch.upper()} can't be applied")
        else:
            print(f"{patch.upper()} doesn't exist")

    output = patcher.data
    return output


# https://github.com/BotoX/xiaomi-m365-firmware-patcher/blob/master/patcher.py
# Thx BotoX!
def find_pattern(data, signature, mask=None, start=None, maxit=None):
    sig_len = len(signature)
    if start is None:
        start = 0
    stop = len(data) - len(signature)
    if maxit is not None:
        stop = start + maxit

    if mask:
        assert sig_len == len(mask), 'mask must be as long as the signature!'
        for i in range(sig_len):
            signature[i] &= mask[i]

    for i in range(start, stop):
        matches = 0

        while signature[matches] is None or signature[matches] == (data[i+matches] & (mask[matches] if mask else 0xFF)):
            matches += 1
            if matches == sig_len:
                return i

    raise SignatureException('Pattern not found!')
