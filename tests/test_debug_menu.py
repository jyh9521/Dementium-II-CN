"""Native-menu PE/data regression checks with optional, local original inputs."""
import io
import json
import mmap
import os
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from debug_menu import build_menu, config, glyph_text, build_font, make_patch
from executable_text import build_executable, apply_executable_patch
from localize import Zar, digest

SOURCE = Path(os.environ.get('DEMENTIUM_SOURCE_EXE', ROOT / 'build/text-layout-fix/original/Dementium II.exe'))
ROM = Path(os.environ.get('DEMENTIUM_SOURCE_ROM', SOURCE.parent / 'rom.zar'))


class NativeMenuLocaleTests(unittest.TestCase):
    def test_translated_printf_tokens_and_nul_termination_contract(self):
        recipe = config()
        self.assertEqual(recipe['schema'], 1)
        tokens = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGcs]|%)')
        for source, target in recipe['labels'].items():
            self.assertEqual(tokens.findall(source), tokens.findall(target), source)
            self.assertTrue(target)
            self.assertNotIn('\0', source)
            self.assertNotIn('\0', target)
        for native_entry in ('Invulnerable', 'Unlimited Ammo', 'Weapons', 'Items', 'Load Section', 'Environment'):
            self.assertIn(native_entry, recipe['labels'])


@unittest.skipUnless(SOURCE.is_file(), 'requires locally supplied locked original EXE')
class NativeMenuPeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pefile
        cls.original = SOURCE.read_bytes()
        cls.literal_recipe = json.loads((ROOT / 'locales/zh-CN/executable-text.json').read_text(encoding='utf8'))
        cls.localized, cls.literal_patch = build_executable(cls.original, cls.literal_recipe)
        cls.modified, cls.report = build_menu(cls.localized)
        cls.before = pefile.PE(data=cls.localized)
        cls.after = pefile.PE(data=cls.modified)
        cls.recipe = config()

    def test_version_guard_and_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact audited executable'):
            build_menu(self.original)
        with self.assertRaisesRegex(ValueError, 'exact audited executable'):
            build_menu(self.modified)
        broken = bytearray(self.localized)
        broken[0x4ee49] ^= 1
        with self.assertRaises(ValueError):
            build_menu(bytes(broken))

    def test_readonly_new_section_mapping_and_existing_sections(self):
        self.assertEqual(len(self.after.sections), len(self.before.sections) + 2)
        for old, new in zip(self.before.sections, self.after.sections):
            if old.Name.rstrip(b'\0')==b'.data':
                self.assertEqual(new.VirtualAddress+new.Misc_VirtualSize,0xa69000)
                self.assertEqual(old.PointerToRawData,new.PointerToRawData)
                self.assertEqual(old.SizeOfRawData,new.SizeOfRawData)
                self.assertEqual(old.Characteristics,new.Characteristics)
            else:
                self.assertEqual(old.__pack__(), new.__pack__())
        section = self.after.sections[-2]
        self.assertEqual(section.Name.rstrip(b'\0'), b'.locmenu')
        self.assertEqual(section.Characteristics, 0x40000040)
        self.assertFalse(section.Characteristics & (0x20000000 | 0x80000000))
        self.assertEqual(section.PointerToRawData % self.after.OPTIONAL_HEADER.FileAlignment, 0)
        self.assertEqual(section.VirtualAddress % self.after.OPTIONAL_HEADER.SectionAlignment, 0)
        ui = self.after.sections[-1]
        self.assertEqual(ui.Name.rstrip(b'\0'),b'.locui')
        self.assertEqual(ui.Characteristics,0x60000020)
        self.assertEqual(ui.PointerToRawData+ui.SizeOfRawData,len(self.modified))
        self.assertEqual(self.after.get_offset_from_rva(section.VirtualAddress), section.PointerToRawData)
        self.assertGreaterEqual(self.after.OPTIONAL_HEADER.SizeOfImage,
                                ui.VirtualAddress + ui.Misc_VirtualSize)

    def read_string(self, pe, data, address):
        offset = pe.get_offset_from_rva(address - pe.OPTIONAL_HEADER.ImageBase)
        return data[offset:].split(b'\0', 1)[0].decode('utf8')

    def test_every_reported_rip_reference_resolves_exact_locale_string(self):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        md.detail = True
        self.assertGreater(self.report['rip_references'], 40)
        self.assertEqual(self.report['labels'], len(self.recipe['labels']))
        section = self.after.sections[-2]
        base = self.after.OPTIONAL_HEADER.ImageBase
        glyph_hits = 0
        for ref in self.report['references']:
            address = int(ref['instruction'], 16)
            instruction = next(md.disasm(self.after.get_data(address - base, 15), address))
            targets = [instruction.address + instruction.size + op.mem.disp
                       for op in instruction.operands
                       if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP]
            target = int(ref['target'], 16)
            self.assertIn(target, targets)
            self.assertTrue(base + section.VirtualAddress <= target <
                            base + section.VirtualAddress + section.Misc_VirtualSize)
            text = self.read_string(self.after, self.modified, target)
            if ref['source'] in self.recipe['labels']:
                self.assertEqual(text, self.recipe['labels'][ref['source']])
            else:
                self.assertEqual(text, glyph_text(self.recipe))
                glyph_hits += 1
        self.assertEqual(glyph_hits, 1)

    def test_only_audited_instruction_bytes_changed(self):
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        md.detail = True
        base = self.before.OPTIONAL_HEADER.ImageBase
        allowed = {0x4ee49, 0x1a714d}
        allowed.update(range(self.before.get_offset_from_rva(0x1a7c5b), self.before.get_offset_from_rva(0x1a7c61)))
        allowed.update(range(self.before.get_offset_from_rva(0x1a7d81), self.before.get_offset_from_rva(0x1a7d90)))
        for rva,size in [(0x1a7c54,7),(0x2ee30,6),(0x1a7d90,11),(0x15587b,7),(0x2f3236,11),(0x2f537c,10),(0x2f5a8,7),(0x2f39cc,6),(0x2f3a3e,7),(0x2de833,7),(0x2f4ad,6),(0x4fa66,8),(0x11b4f7,10),(0x11a7b0,5),(0x11af80,6),(0x123379,10),(0x121e50,5),(0x122a10,11),(0x126da7,10)]:
            offset=self.before.get_offset_from_rva(rva)
            allowed.update(range(offset,offset+size))
        for ref in self.report['references']:
            address = int(ref['instruction'], 16)
            instruction = next(md.disasm(self.before.get_data(address - base, 15), address))
            offset = self.before.get_offset_from_rva(address - base) + instruction.disp_offset
            allowed.update(range(offset, offset + instruction.disp_size))
        code = next(section for section in self.before.sections if section.Name.rstrip(b'\0') == b'.text')
        changed = {offset for offset in range(code.PointerToRawData, code.PointerToRawData + code.SizeOfRawData)
                   if self.localized[offset] != self.modified[offset]}
        self.assertTrue(changed <= allowed, sorted(changed - allowed))
        self.assertEqual(self.modified[0x4ee49:0x4ee4b], bytes.fromhex('eb 04'))
        self.assertEqual(self.modified[0x1a714b:0x1a714e], bytes.fromhex('83 fa 1c'))
        self.assertEqual(self.before.DIRECTORY_ENTRY_IMPORT[0].dll, self.after.DIRECTORY_ENTRY_IMPORT[0].dll)
        self.assertEqual([entry.dll for entry in self.before.DIRECTORY_ENTRY_IMPORT],
                         [entry.dll for entry in self.after.DIRECTORY_ENTRY_IMPORT])

    def test_all_35_entity_and_7_section_pointers_rebase_with_existing_relocations(self):
        import pefile
        old_relocations = [(block.struct.VirtualAddress, [(entry.type, entry.rva) for entry in block.entries])
                           for block in self.before.DIRECTORY_ENTRY_BASERELOC]
        self.assertEqual(old_relocations,
                         [(block.struct.VirtualAddress, [(entry.type, entry.rva) for entry in block.entries])
                          for block in self.after.DIRECTORY_ENTRY_BASERELOC])
        for old in self.before.sections:
            if old.Name.rstrip(b'\0') == b'.reloc':
                self.assertEqual(old.get_data(), self.after.get_data(old.VirtualAddress, old.SizeOfRawData))
        relocated = {entry.rva for block in self.after.DIRECTORY_ENTRY_BASERELOC
                     for entry in block.entries if entry.type == 10}
        changed = 0
        shifted = pefile.PE(data=self.modified)
        new_base = self.before.OPTIONAL_HEADER.ImageBase + 0x2000000
        shifted.relocate_image(new_base)
        rebased = shifted.write()
        for table, count, stride in ((0x3c08c0, 12, 16), (0x3c09d0, 23, 16), (0x3c0e30, 7, 24)):
            for index in range(count):
                rva = table + index * stride
                self.assertIn(rva, relocated)
                offset = self.before.get_offset_from_rva(rva)
                old = struct.unpack_from('<Q', self.localized, offset)[0]
                pointer = struct.unpack_from('<Q', self.modified, offset)[0]
                shifted_pointer = struct.unpack_from('<Q', rebased, offset)[0]
                self.assertEqual(shifted_pointer - pointer, 0x2000000)
                source = self.read_string(self.before, self.localized, old)
                self.assertEqual(self.read_string(self.after, self.modified, pointer), self.recipe['labels'][source])
                self.assertEqual(self.read_string(shifted, rebased, shifted_pointer), self.recipe['labels'][source])
                changed += 1
        self.assertEqual(changed, 42)

    def test_reproducible_build_and_exact_original_rollback(self):
        again, report = build_menu(self.localized)
        self.assertEqual(again, self.modified)
        self.assertEqual(report, self.report)
        patch = make_patch(self.original, self.modified)
        self.assertEqual(apply_executable_patch(self.original, patch), self.modified)
        self.assertEqual(apply_executable_patch(self.modified, patch, True), self.original)
        self.assertEqual(digest(self.original), self.literal_recipe['source_sha256'])

    def test_patch_rejects_hash_run_append_tampering(self):
        import copy
        patch = make_patch(self.original, self.modified)
        for data in (self.original + b'?', self.modified, bytes(bytearray(self.original[:-1]) + b'?')):
            with self.assertRaises(ValueError):
                apply_executable_patch(data, patch)
        for tamper in ('run', 'append'):
            broken = copy.deepcopy(patch)
            if tamper == 'run':
                broken['runs'][0]['new'] = 'ff' * len(bytes.fromhex(broken['runs'][0]['new']))
            else:
                broken['append'] = 'AAAA'
            with self.assertRaises(ValueError):
                apply_executable_patch(self.original, broken)


@unittest.skipUnless(ROM.is_file(), 'requires locally supplied original ROM and installed body font')
class NativeMenuFontTests(unittest.TestCase):
    def test_subset_reproducibility_cmap_and_actual_glyph_ink(self):
        from font_pipeline import resolve_fonts
        from fontTools.ttLib import TTFont
        from PIL import ImageFont
        profile = json.loads((ROOT / 'locales/zh-CN/font-profile.json').read_text(encoding='utf8'))
        font_path = resolve_fonts(profile)['body']
        with ROM.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            archive = Zar(data)
            first = build_font(archive, font_path)
            self.assertEqual(first, build_font(archive, font_path))
        font = TTFont(io.BytesIO(first))
        required = set(map(ord, glyph_text(config())))
        self.assertFalse(required - font.getBestCmap().keys())
        rendered = ImageFont.truetype(io.BytesIO(first), 24)
        for code in required - {32}:
            self.assertIsNotNone(rendered.getmask(chr(code)).getbbox(), chr(code))


if __name__ == '__main__':
    unittest.main(verbosity=2)
