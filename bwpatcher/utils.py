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

from importlib import import_module
import re


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
    # CHK patch must always come last for scooters based on the ES32 MCU (4pro2nd and 5pro)
    if model in ["mi4pro2nd", "mi5pro"] and patches[-1] != "chk":
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


def extract_ldr_offset(instruction: str) -> int:
    """Extract the offset number from an LDR instruction like 'ldr r1, [pc, #0x1dc]'"""
    match = re.search(r'\[pc,\s*#(0x[0-9a-fA-F]+)\]', instruction)
    if match:
        return int(match.group(1), 16)
    return None

def offset_to_nearest_word(ofs):
    rem = -1
    while rem != 0:
        ofs += 2
        rem = ofs % 4
    return ofs