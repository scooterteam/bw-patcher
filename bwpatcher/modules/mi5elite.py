#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Mi 5 Elite Module
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

from typing import List, Tuple, Dict, Optional
from bwpatcher.core_n32 import CoreN32Patcher
from bwpatcher.utils import find_pattern, SignatureException


class Mi5elitePatcher(CoreN32Patcher):
    """
    Patcher for Xiaomi Mi 5 Elite with N32 (Leqi) controller.

    Uses signature-based pattern matching to apply binary patches for:
    - Speed limits per mode (pedestrian, drive, sport)
    - Motor start speed threshold
    - Regional speed limit removal

    Architecture:
    - Branch patch at ldrb.w location (6 bytes)
    - Speed logic with ldr r1 at beginning (executed by all paths)
    - Two return paths: default (executes add.w + lsls) and patched (jumps to strh)
    - Dynamic pattern matching for data addresses
    """

    # Mode constants
    MODE_PEDESTRIAN = 1
    MODE_DRIVE = 2
    MODE_SPORT = 3

    # Pattern signatures
    SIG_SPEED_LIMIT_RETURN = [
        0x08, 0x80, 0x52, 0x48, 0x52, 0x49, 0x00, 0x88,
        0x09, 0x88, 0x00, 0xf1, 0x0a, 0x02, 0x8a, 0x42, 0x01, 0xd9
    ]

    SIG_SPEED_LIMIT_DST = [
        0xdf, 0xf8, 0xf0, 0x81, 0xa8, 0xf8, 0x00, 0x10, 0x7b, 0x49, 0x67, 0x45
    ]

    SIG_MOTOR_START = [
        0x01, 0x80, 0x2D, 0x2B, 0xEF, 0xD3, 0x11, 0x70,
        0x70, 0xBD, 0x14, 0x33, 0x2D, 0x2B, 0x07, 0xD2
    ]

    def __init__(self, data: bytes):
        """
        Initialize Mi5Elite patcher with firmware or full image data.

        Args:
            data: Firmware or full image data
        """
        super().__init__(data)
        self.patched_speeds: Dict[str, int] = {}
        self._speed_block_patched = False

        # Offsets discovered during first patch (cached for subsequent updates)
        self._ldr_patch_offset: Optional[int] = None
        self._speed_logic_offset: Optional[int] = None
        self._default_path_address: Optional[int] = None  # Address for non-patched modes
        self._patched_path_address: Optional[int] = None  # Address for patched modes
        self._ldr_r0_offset: Optional[int] = None
        self._ldr_r1_offset: Optional[int] = None

    def _locate_speed_patch_offsets(self) -> None:
        """Locate all offsets needed for speed patching (called on first patch only)."""
        try:
            sig_offset = find_pattern(self.data, self.SIG_SPEED_LIMIT_RETURN)
            self._ldr_patch_offset = sig_offset - 12
        except SignatureException:
            raise Exception("Could not find speed limit signature for patching")

        try:
            self._speed_logic_offset = (
                find_pattern(self.data, self.SIG_SPEED_LIMIT_DST) +
                len(self.SIG_SPEED_LIMIT_DST) + 2
            )
        except SignatureException:
            raise Exception("Could not find speed logic destination")

        # Set return addresses for different code paths
        self._default_path_address = self._ldr_patch_offset + 6   # Non-patched modes (execute add.w + lsls)
        self._patched_path_address = self._ldr_patch_offset + 12  # Patched modes (jump to strh)

        # Find mode data address (0x2000018A) and calculate PC-relative offset for ldr r0
        mode_data_addr = find_pattern(self.data, [0x8a, 0x01, 0x00, 0x20])
        ldr_r0_pc = (self._ldr_patch_offset + 4) & ~3
        self._ldr_r0_offset = mode_data_addr - ldr_r0_pc

        # Find r1 data address (0x200001A4) and calculate PC-relative offset for ldr r1
        r1_data_addr = find_pattern(self.data, [0xa4, 0x01, 0x00, 0x20])
        ldr_r1_pc = (self._speed_logic_offset + 4) & ~3
        self._ldr_r1_offset = r1_data_addr - ldr_r1_pc

    def _apply_branch_patch(self) -> Tuple[str, str, str, str]:
        """Apply the initial branch patch (6 bytes: ldr r0 + ldrb r0 + branch)."""
        branch_asm = f"""
        ldr r0, [pc, #{self._ldr_r0_offset}]
        ldrb r0, [r0, #0]
        b {hex(self._speed_logic_offset)}
        """
        branch_bytes = self.assembly(branch_asm, self._ldr_patch_offset)

        if len(branch_bytes) != 6:
            raise Exception(f"Branch patch must be 6 bytes, got {len(branch_bytes)}")

        pre_branch = self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6]
        self.data[self._ldr_patch_offset:self._ldr_patch_offset + 6] = branch_bytes

        return ("branch_patch", hex(self._ldr_patch_offset), pre_branch.hex(), branch_bytes.hex())

    def _build_speed_logic_asm(self) -> str:
        """Build assembly code for speed logic based on patched modes."""
        asm_code = f"ldr r1, [pc, #{self._ldr_r1_offset}]\n"

        mode_map = {'ped': self.MODE_PEDESTRIAN, 'drive': self.MODE_DRIVE, 'sport': self.MODE_SPORT}
        mode_checks = [m for m in ['ped', 'drive', 'sport'] if m in self.patched_speeds]

        for i, mode in enumerate(mode_checks):
            mode_num = mode_map[mode]
            speed = self.patched_speeds[mode]
            next_label = f"check_{mode_checks[i+1]}" if i+1 < len(mode_checks) else "default_case"

            asm_code += f"""
            check_{mode}:
            cmp r0, #{mode_num}
            bne {next_label}
            movs.w r0, #{speed}
            b {hex(self._patched_path_address)}
            """

        asm_code += f"""
        default_case:
        ldrb.w r0, [r8, #5]
        b {hex(self._default_path_address)}
        """

        return asm_code

    def _patch_speed_block(self, ped_kmh: Optional[float] = None,
                          drive_kmh: Optional[float] = None,
                          sport_kmh: Optional[float] = None) -> List[Tuple[str, str, str, str]]:
        """
        Apply speed limit patches for specified modes.

        First call: Applies structural patches (branch + speed logic framework)
        Subsequent calls: Updates speed values by rebuilding speed logic block

        Args:
            ped_kmh: Pedestrian mode speed in km/h
            drive_kmh: Drive mode speed in km/h
            sport_kmh: Sport mode speed in km/h

        Returns:
            List of patch result tuples (name, offset, old_hex, new_hex)
        """
        # Update speed values for modes being patched
        if ped_kmh is not None:
            self.patched_speeds['ped'] = self._calc_speed(ped_kmh, size=0)
        if drive_kmh is not None:
            self.patched_speeds['drive'] = self._calc_speed(drive_kmh, size=0)
        if sport_kmh is not None:
            self.patched_speeds['sport'] = self._calc_speed(sport_kmh, size=0)

        results = []
        results.extend(self._speed_limit_fix())

        # First-time setup
        if not self._speed_block_patched:
            self._locate_speed_patch_offsets()
            results.append(self._apply_branch_patch())

        # Build and apply speed logic patch
        asm_code = self._build_speed_logic_asm()
        patch_bytes = self.assembly(asm_code, self._speed_logic_offset)
        pre = self.data[self._speed_logic_offset:self._speed_logic_offset + len(patch_bytes)]
        self.data[self._speed_logic_offset:self._speed_logic_offset + len(patch_bytes)] = patch_bytes

        patch_name = "speed_logic_block" if not self._speed_block_patched else "speed_constants_updated"
        results.append((patch_name, hex(self._speed_logic_offset), pre.hex(), patch_bytes.hex()))

        self._speed_block_patched = True
        return results

    def speed_limit_ped(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        """
        Set Pedestrian mode speed limit.

        Args:
            kmh: Speed limit in km/h

        Returns:
            List of patch result tuples
        """
        return self._patch_speed_block(ped_kmh=kmh)

    def speed_limit_drive(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        """
        Set Drive mode speed limit.

        Args:
            kmh: Speed limit in km/h

        Returns:
            List of patch result tuples
        """
        return self._patch_speed_block(drive_kmh=kmh)

    def speed_limit_sport(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        """
        Set Sport mode speed limit.

        Args:
            kmh: Speed limit in km/h

        Returns:
            List of patch result tuples
        """
        return self._patch_speed_block(sport_kmh=kmh)

    def _speed_limit_fix(self) -> List[Tuple[str, str, str, str]]:
        """
        Remove regional speed limits by replacing conditional branch with unconditional branch.

        Returns:
            List of patch result tuples
        """
        results = []

        try:
            ofs_sig = find_pattern(self.data, self.SIG_SPEED_LIMIT_DST)
        except SignatureException:
            return results  # Already patched or not found

        ofs = ofs_sig + len(self.SIG_SPEED_LIMIT_DST)

        # Calculate branch target: PC+4 + (63 * 2) = current_addr + 130
        branch_target = ofs + 130
        branch_asm = f"b {hex(branch_target)}"
        post = self.assembly(branch_asm, ofs)

        pre = self.data[ofs:ofs + len(post)]
        if pre == post:
            return results  # Already patched

        self.data[ofs:ofs + len(post)] = post
        results.append(("speed_limit_fix", hex(ofs), pre.hex(), post.hex()))

        return results

    def motor_start_speed(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        """
        Set motor start speed (minimum speed before motor engages).

        Patches three comparison values in the firmware:
        - Main threshold (appears twice at offsets +2 and +12)
        - Hysteresis threshold at offset +10 (half of main threshold)

        Args:
            kmh: Desired motor start speed in km/h

        Returns:
            List of patch result tuples
        """
        results = []
        ofs_sig = find_pattern(self.data, self.SIG_MOTOR_START)

        speed = self._calc_speed(kmh, size=0)
        speed_hyst = speed // 2

        # Patch main threshold (offset +2)
        ofs = ofs_sig + 2
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_1", hex(ofs), pre.hex(), post.hex()))

        # Patch hysteresis threshold (offset +10)
        ofs = ofs_sig + 10
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed_hyst & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_hysteresis", hex(ofs), pre.hex(), post.hex()))

        # Patch main threshold duplicate (offset +12)
        ofs = ofs_sig + 12
        pre = self.data[ofs:ofs + 1]
        post = bytes([speed & 0xFF])
        self.data[ofs:ofs + 1] = post
        results.append(("motor_start_speed_threshold_2", hex(ofs), pre.hex(), post.hex()))

        return results
