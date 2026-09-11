#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2026 ScooterTeam
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

import shutil
import traceback

from functools import wraps
from importlib import import_module
import re


class SignatureException(Exception):
    pass


class ExperimentalPatchError(Exception):
    """Raised when an @experimental patch is requested without allow_experimental."""


def experimental(fn):
    """Mark a patcher method as experimental (UI/CLI gated unless explicitly allowed)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    wrapper._bw_experimental = True
    return wrapper


def is_experimental_method(method) -> bool:
    fn = getattr(method, "__func__", method)
    return bool(getattr(fn, "_bw_experimental", False))


def is_patch_experimental(patcher, patch_code: str) -> bool:
    """True if this model's implementation of ``patch_code`` is @experimental."""
    if patch_code not in patch_map:
        return False
    return is_experimental_method(patch_map[patch_code](patcher))


patch_map = {
    "rsls": lambda patcher: patcher.remove_speed_limit_sport,
    "dms": lambda patcher: patcher.dashboard_max_speed,
    "slp": lambda patcher: patcher.speed_limit_ped,
    "sld": lambda patcher: patcher.speed_limit_drive,
    "sls": lambda patcher: patcher.speed_limit_sport,
    "rfm": lambda patcher: patcher.region_free,
    "fdv": lambda patcher: patcher.fake_drv_version,
    "chk": lambda patcher: patcher.fix_checksum,
    "img": lambda patcher: patcher.create_full_image,
    "mss": lambda patcher: patcher.motor_start_speed,
    "cce": lambda patcher: patcher.cruise_control_enable,
}

# patch code → CorePatcher method name (for class-level @experimental checks)
PATCH_METHOD_NAMES = {
    "rsls": "remove_speed_limit_sport",
    "dms": "dashboard_max_speed",
    "slp": "speed_limit_ped",
    "sld": "speed_limit_drive",
    "sls": "speed_limit_sport",
    "rfm": "region_free",
    "fdv": "fake_drv_version",
    "chk": "fix_checksum",
    "img": "create_full_image",
    "mss": "motor_start_speed",
    "cce": "cruise_control_enable",
}


def is_model_patch_experimental(model: str, patch_code: str) -> bool:
    """True if ``model``'s class marks this patch code with @experimental."""
    method_name = PATCH_METHOD_NAMES.get(patch_code)
    if not method_name:
        return False
    module = import_module(f"bwpatcher.modules.{model}")
    patcher_class = getattr(module, f"{model.capitalize()}Patcher")
    method = getattr(patcher_class, method_name, None)
    if method is None:
        return False
    return is_experimental_method(method)


def patch_firmware(model: str, data: bytes, patches: list, web=True, allow_experimental=False):
    # CHK patch must always come last for every scooter using update file
    # --> no longer forcing, instead put in GUI
    #if patches[-1] != "chk":
    #    patches.append("chk")
    print("Patchlist:", patches)

    errors = []
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
                method = patch_map[patch](patcher)
                if is_experimental_method(method) and not allow_experimental:
                    raise ExperimentalPatchError(
                        f"{patch} is experimental on {model}; "
                        "pass allow_experimental=True / --experimental / ?experimental=1"
                    )
                if value:
                    res = method(value)
                else:
                    res = method()
                print(res)
            except ExperimentalPatchError:
                raise
            except Exception as e:
                if web:
                    raise e
                else:
                    errors.append((patch, e))
        else:
            errors.append((patch, "The specified patch doesn't exist."))

    if errors:
        width = shutil.get_terminal_size(fallback=(80,24)).columns // 3
        for patch, error in errors:
            msg = f"ERROR: {patch} "
            print(f"{msg}{'-'*(width - len(msg))}")
            traceback.print_exception(type(error), error, error.__traceback__)

        print("-" * width)

        for patch, _ in errors:
            print(f"Failed to use the {patch} patch. Check the logs.")

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

def get_reg(disasm, default="r1"):
    reg = default
    try:
        reg = disasm.split('\t')[1].split(',')[0]
    except:
        pass
    return reg
