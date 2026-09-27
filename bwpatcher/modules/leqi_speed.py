#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher - Leqi Speed Limit Module (shared base)
# Copyright (C) 2024-2026 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

import struct
from typing import List, Tuple, Dict, Optional
from bwpatcher.core_n32 import CoreN32Patcher
from bwpatcher.utils import find_pattern, SignatureException


class LeqiSpeedPatcher(CoreN32Patcher):
    MODE_PEDESTRIAN = 1
    MODE_DRIVE = 2
    MODE_SPORT = 3

    MODE_ORDER = ('ped', 'drive', 'sport')

    REGION_LIMIT_VALUE = 0x15E

    def __init__(self, data: bytes):
        super().__init__(data)
        self.patched_speeds: Dict[str, int] = {}
        self._speed_block_patched = False
        self._inject_offset: Optional[int] = None
        self._hijack_offset: Optional[int] = None
        self._return_address: Optional[int] = None
        self._output_ptr: Optional[int] = None
        self._region_limit_patch_ofs: Optional[int] = None
        self._region_limit_store_ofs: Optional[int] = None

    def _speed_limit_fix(self) -> List[Tuple[str, str, str, str]]:
        """Regional bypass hook; default no-op for variants without it."""
        return []

    def _resolve_region_limit_sites(
        self,
        anchor: List[Optional[int]],
        stock_patch: List[int],
    ) -> Tuple[int, int]:
        if self._region_limit_patch_ofs is not None:
            assert self._region_limit_store_ofs is not None
            return self._region_limit_patch_ofs, self._region_limit_store_ofs

        sig_ofs = find_pattern(self.data, anchor)
        try:
            patch_slot = next(i for i, byte in enumerate(anchor) if byte is None)
        except StopIteration as exc:
            raise Exception("Region limit anchor has no patch-slot wildcards") from exc

        patch_len = sum(1 for byte in anchor if byte is None)
        if patch_len != len(stock_patch):
            raise Exception(
                f"Region limit stock patch length {len(stock_patch)} "
                f"does not match anchor wildcards ({patch_len})"
            )

        patch_ofs = sig_ofs + patch_slot
        store_ofs = sig_ofs + len(anchor) - 2
        self._region_limit_patch_ofs = patch_ofs
        self._region_limit_store_ofs = store_ofs
        return patch_ofs, store_ofs

    def _apply_region_limit_movw_branch(
        self,
        anchor: List[Optional[int]],
        stock_patch: List[int],
        reg: str,
        patch_name: str,
    ) -> List[Tuple[str, str, str, str]]:
        value = self.REGION_LIMIT_VALUE

        try:
            patch_ofs, store_ofs = self._resolve_region_limit_sites(anchor, stock_patch)
        except SignatureException:
            return []

        asm = f"movw {reg}, #{hex(value)}\nb {hex(store_ofs)}"
        post = self.assembly(asm, patch_ofs)
        if len(post) != len(stock_patch):
            raise Exception(
                f"Region limit patch @0x{patch_ofs:X}: expected {len(stock_patch)} bytes, "
                f"got {len(post)}"
            )

        pre = bytes(self.data[patch_ofs:patch_ofs + len(post)])
        if pre == post:
            return []

        stock = bytes(stock_patch)
        if pre == stock:
            self.data[patch_ofs:patch_ofs + len(post)] = post
            return [(patch_name, hex(patch_ofs), pre.hex(), post.hex())]

        raise Exception(
            f"Region limit patch @0x{patch_ofs:X}: expected {stock.hex()}, found {pre.hex()}"
        )

    def _locate_patch_offsets(self) -> None:
        raise NotImplementedError

    def _apply_hijack_patch(self) -> Tuple[str, str, str, str]:
        raise NotImplementedError

    def _build_speed_logic_asm(self) -> str:
        raise NotImplementedError

    def _assemble_inject_block(self, asm_code: str) -> bytes:
        return self.assembly(asm_code, self._inject_offset)

    def _verify_inject_site(self, patch_bytes: bytes) -> None:
        """Verify inject region before first patch; no-op for dead-code variants."""

    def _build_mode_check_asm(
        self,
        mode_reg: str,
        speed_reg: str,
        patched_branch_target: str,
    ) -> str:
        """Build cmp/bne/movw chain for modes present in patched_speeds."""
        mode_map = {
            'ped': self.MODE_PEDESTRIAN,
            'drive': self.MODE_DRIVE,
            'sport': self.MODE_SPORT,
        }
        mode_checks = [m for m in self.MODE_ORDER if m in self.patched_speeds]
        asm_code = ""

        for i, mode in enumerate(mode_checks):
            mode_num = mode_map[mode]
            speed = self.patched_speeds[mode]
            next_label = (
                f"check_{mode_checks[i + 1]}"
                if i + 1 < len(mode_checks)
                else "default_case"
            )

            asm_code += f"""
            check_{mode}:
            cmp {mode_reg}, #{mode_num}
            bne {next_label}
            movw {speed_reg}, #{speed}
            b {patched_branch_target}
            """

        return asm_code

    def _patch_speed_block(
        self,
        ped_kmh: Optional[float] = None,
        drive_kmh: Optional[float] = None,
        sport_kmh: Optional[float] = None,
    ) -> List[Tuple[str, str, str, str]]:
        if ped_kmh is not None:
            self.patched_speeds['ped'] = self._calc_speed(ped_kmh, size=0)
        if drive_kmh is not None:
            self.patched_speeds['drive'] = self._calc_speed(drive_kmh, size=0)
        if sport_kmh is not None:
            self.patched_speeds['sport'] = self._calc_speed(sport_kmh, size=0)

        results: List[Tuple[str, str, str, str]] = []
        results.extend(self._speed_limit_fix())

        if not self._speed_block_patched:
            self._locate_patch_offsets()
            results.append(self._apply_hijack_patch())

        asm_code = self._build_speed_logic_asm()
        assert self._inject_offset is not None
        patch_bytes = self._assemble_inject_block(asm_code)

        if not self._speed_block_patched:
            self._verify_inject_site(patch_bytes)

        pre = self.data[self._inject_offset:self._inject_offset + len(patch_bytes)]
        self.data[self._inject_offset:self._inject_offset + len(patch_bytes)] = patch_bytes

        patch_name = (
            "speed_logic_block" if not self._speed_block_patched else "speed_constants_updated"
        )
        results.append((
            patch_name,
            hex(self._inject_offset),
            pre.hex(),
            patch_bytes.hex(),
        ))

        self._speed_block_patched = True
        return results

    def speed_limit_ped(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(ped_kmh=kmh)

    def speed_limit_drive(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(drive_kmh=kmh)

    def speed_limit_sport(self, kmh: float) -> List[Tuple[str, str, str, str]]:
        return self._patch_speed_block(sport_kmh=kmh)

    def _verify_hijack_bytes(self, offset: int, expected: List[int]) -> None:
        actual = bytes(self.data[offset:offset + len(expected)])
        expected_bytes = bytes(expected)
        if actual != expected_bytes:
            raise Exception(
                f"Hijack site @0x{offset:X}: expected {expected_bytes.hex()}, "
                f"found {actual.hex()}"
            )

    def _verify_zero_padding(self, offset: int, size: int) -> None:
        region = self.data[offset:offset + size]
        if any(b != 0 for b in region):
            raise Exception(
                f"Inject site @0x{offset:X} is not zero padding "
                f"({size} bytes required)"
            )

    def _read_ldr_pc_literal(self, insn_offset: int) -> int:
        """Decode a 16-bit Thumb `ldr Rt, [pc, #imm]` and read its literal pool word."""
        insn = self.data[insn_offset:insn_offset + 2]
        if len(insn) != 2:
            raise Exception(f"ldr @0x{insn_offset:X}: truncated instruction")

        hw = insn[0] | (insn[1] << 8)
        imm = (hw & 0xFF) * 4
        pc = (insn_offset + 4) & ~3
        literal_addr = pc + imm
        if literal_addr + 4 > len(self.data):
            raise Exception(
                f"ldr @0x{insn_offset:X}: literal pool @0x{literal_addr:X} out of range"
            )
        return struct.unpack_from('<I', self.data, literal_addr)[0]

    def _find_tail_zero_padding(
        self,
        min_size: int,
        search_from: Optional[int] = None,
        search_window: Optional[int] = None,
        pad_marker: Optional[List[int]] = None,
    ) -> int:
        """
        Locate inject padding after search_from.

        Prefer an optional pad_marker signature (e.g. the 8-byte trailer before the
        real zero run). Fall back to find_pattern on a min_size 0x00 signature.
        Always verifies a contiguous zero run of at least min_size (CRC excluded).
        """
        if search_from is None:
            window = search_window if search_window is not None else 0x800
            search_from = max(0, len(self.data) - window)

        search_end = max(search_from, len(self.data) - 2)  # keep embedded CRC
        if search_end - search_from < min_size:
            raise Exception(
                f"No room for {min_size}-byte zero padding after 0x{search_from:X} "
                f"(end=0x{search_end:X})"
            )

        pad_ofs: Optional[int] = None
        if pad_marker:
            try:
                marker_ofs = find_pattern(self.data, pad_marker, start=search_from)
                pad_ofs = marker_ofs + len(pad_marker)
            except SignatureException:
                pad_ofs = None

        if pad_ofs is None:
            zero_sig = [0x00] * min_size
            try:
                pad_ofs = find_pattern(self.data, zero_sig, start=search_from)
            except SignatureException as exc:
                raise Exception(
                    f"No zero padding signature ({min_size} x 00) found after 0x{search_from:X}"
                ) from exc

        if pad_ofs + min_size > search_end:
            raise Exception(
                f"Zero padding @0x{pad_ofs:X} overlaps CRC / end of firmware"
            )

        run_end = pad_ofs
        while run_end < search_end and self.data[run_end] == 0:
            run_end += 1
        if run_end - pad_ofs < min_size:
            raise Exception(
                f"Zero padding @0x{pad_ofs:X} only {run_end - pad_ofs} bytes "
                f"(need {min_size})"
            )

        return pad_ofs

    def _resolve_speed_padding_sites(
        self,
        anchor: List[int],
        hijack_size: int,
        output_ptr_ldr_offset: int,
        min_padding_size: int,
        inject_search_from: Optional[int] = None,
        pad_marker: Optional[List[int]] = None,
    ) -> None:
        if self._hijack_offset is not None:
            assert self._inject_offset is not None
            assert self._return_address is not None
            assert self._output_ptr is not None
            return

        sig_ofs = find_pattern(self.data, anchor)
        if hijack_size > len(anchor):
            raise Exception(
                f"Speed calc hijack size {hijack_size} exceeds anchor length {len(anchor)}"
            )
        if output_ptr_ldr_offset + 2 > len(anchor):
            raise Exception("output_ptr_ldr_offset must fall within speed calc anchor")

        self._hijack_offset = sig_ofs
        self._return_address = sig_ofs + len(anchor)
        self._output_ptr = self._read_ldr_pc_literal(sig_ofs + output_ptr_ldr_offset)
        self._inject_offset = self._find_tail_zero_padding(
            min_padding_size,
            search_from=inject_search_from,
            pad_marker=pad_marker,
        )

    def _apply_bw_hijack(
        self,
        hijack_offset: int,
        inject_offset: int,
        sig_hijack: List[int],
        patch_name: str = "hijack_speed_calc",
    ) -> Tuple[str, str, str, str]:
        self._verify_hijack_bytes(hijack_offset, sig_hijack)
        branch_asm = f"b.w {hex(inject_offset)}"
        branch_bytes = self.assembly(branch_asm, hijack_offset)
        if len(branch_bytes) != 4:
            raise Exception(f"Hijack branch must be 4 bytes, got {len(branch_bytes)}")

        pre = self.data[hijack_offset:hijack_offset + 4]
        self.data[hijack_offset:hijack_offset + 4] = branch_bytes
        return (patch_name, hex(hijack_offset), pre.hex(), branch_bytes.hex())

    def _build_padding_speed_logic_asm(
        self,
        reload_asm: str,
        mode_reg: str,
        speed_reg: str,
        ptr_reg: str,
        return_address: int,
        output_ptr: int,
    ) -> str:
        """Build self-contained inject block for padding-injection variants."""
        store_label = "store"
        patched_target = store_label

        asm_code = reload_asm + "\n"
        asm_code += f"and {mode_reg}, {mode_reg}, #3\n"
        asm_code += self._build_mode_check_asm(mode_reg, speed_reg, patched_target)
        asm_code += f"""
        default_case:
        add.w {speed_reg}, {speed_reg}, {speed_reg}, lsl #2
        lsls {speed_reg}, {speed_reg}, #1
        {store_label}:
        ldr {ptr_reg}, [pc, #4]
        strh {speed_reg}, [{ptr_reg}]
        b.w {hex(return_address)}
        """
        # Note: [pc, #4] is a placeholder; _assemble_with_literal_pool patches the
        # immediate so the appended .word lands at the correct PC-relative address.
        return asm_code

    def _assemble_with_literal_pool(
        self, asm_code: str, inject_offset: int, literal_value: int
    ) -> bytes:
        """
        Assemble inject block and append a 4-byte literal pool word.

        Epilogue is always: ldr (2) + strh (2) + b.w (4). The ldr imm is rewritten
        so PC-relative addressing hits the literal after optional alignment padding.
        """
        code_bytes = bytearray(self.assembly(asm_code, inject_offset))
        if len(code_bytes) < 8:
            raise Exception("Inject block too short for ldr/strh/b.w epilogue")

        ldr_at = inject_offset + len(code_bytes) - 8
        pc = (ldr_at + 4) & ~3
        code_end = inject_offset + len(code_bytes)
        lit_addr = (code_end + 3) & ~3
        if lit_addr < code_end:
            lit_addr += 4
        imm = lit_addr - pc
        if imm < 0 or imm > 1020 or imm % 4 != 0:
            raise Exception(
                f"Cannot place literal pool: ldr@0x{ldr_at:X} pc=0x{pc:X} "
                f"lit=0x{lit_addr:X} imm={imm}"
            )

        old_ldr = code_bytes[-8:-6]
        # Thumb T1: ldr Rt, [pc, #imm8*4]  ->  01001ttt iiiiiiii
        if (old_ldr[1] & 0xF8) != 0x48:
            raise Exception(
                f"Expected Thumb ldr [pc] before strh/b.w, found {old_ldr.hex()}"
            )
        rt = old_ldr[1] & 0x07
        code_bytes[-8:-6] = bytes([imm // 4, 0x48 | rt])
        pad = lit_addr - code_end
        return bytes(code_bytes) + (b"\x00" * pad) + struct.pack("<I", literal_value)


class LeqiPaddingSpeedPatcher(LeqiSpeedPatcher):
    """
    Leqi speed patcher using verified-zero padding for injected code (mi6, mi6lite).

    Hijacks a 4-byte instruction run with b.w into tail zero padding. Hijack,
    return, output pointer, and inject sites are resolved via pattern matching.

    Zero-region layout after SIG_INJECT_PAD_MARKER:
      [margin][inject block][margin]
    where margin = PADDING_SAFETY_MARGIN.
    """

    SIG_SPEED_CALC_ANCHOR: List[int]
    HIJACK_SIZE: int = 4
    OUTPUT_PTR_LDR_OFFSET: int
    # Leading/trailing free zeros around the inject block inside the zero run.
    PADDING_SAFETY_MARGIN: int = 16
    # Don't search for inject padding before this offset (keeps us out of code/data).
    INJECT_SEARCH_START: int = 0xA000
    # Trailer immediately before the real zero-padding run (mi6 / mi6lite).
    SIG_INJECT_PAD_MARKER: List[int] = [
        0x21, 0x3B, 0xB0, 0x17, 0xFD, 0x63, 0x69, 0x34,
    ]

    def _locate_patch_offsets(self) -> None:
        try:
            # Provisional: leading margin only; full size checked after assemble.
            provisional = self.PADDING_SAFETY_MARGIN
            self._resolve_speed_padding_sites(
                self.SIG_SPEED_CALC_ANCHOR,
                self.HIJACK_SIZE,
                self.OUTPUT_PTR_LDR_OFFSET,
                provisional,
                inject_search_from=self.INJECT_SEARCH_START,
                pad_marker=self.SIG_INJECT_PAD_MARKER,
            )
        except SignatureException as exc:
            raise Exception("Could not find speed calc signature for patching") from exc
        assert self._inject_offset is not None
        # Place the block after a leading safety margin inside the zero run.
        self._inject_offset += self.PADDING_SAFETY_MARGIN

    def _apply_hijack_patch(self) -> Tuple[str, str, str, str]:
        assert self._hijack_offset is not None
        assert self._inject_offset is not None
        return self._apply_bw_hijack(
            self._hijack_offset,
            self._inject_offset,
            self.SIG_SPEED_CALC_ANCHOR[:self.HIJACK_SIZE],
        )

    def _required_padding_size(self, patch_bytes: bytes) -> int:
        """Zeros needed from inject offset: patch + trailing safety margin."""
        return len(patch_bytes) + self.PADDING_SAFETY_MARGIN

    def _verify_inject_site(self, patch_bytes: bytes) -> None:
        """Require zeros of (patch + trailing margin) starting at the inject site."""
        assert self._inject_offset is not None
        need = self._required_padding_size(patch_bytes)
        zero_sig = [0x00] * need
        try:
            found = find_pattern(self.data, zero_sig, start=self._inject_offset)
        except SignatureException as exc:
            raise Exception(
                f"Inject site @0x{self._inject_offset:X} lacks {need}-byte zero padding "
                f"(patch={len(patch_bytes)} + margin={self.PADDING_SAFETY_MARGIN})"
            ) from exc
        if found != self._inject_offset:
            raise Exception(
                f"Inject site @0x{self._inject_offset:X} is not zero padding "
                f"({need} bytes required; next zero run @0x{found:X})"
            )

    def _assemble_inject_block(self, asm_code: str) -> bytes:
        assert self._inject_offset is not None
        assert self._output_ptr is not None
        return self._assemble_with_literal_pool(
            asm_code, self._inject_offset, self._output_ptr
        )

