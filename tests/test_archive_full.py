"""Standalone archive selection, portable recovery and hostile-input guards."""
import copy
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import archive_full as archive
import archive_increment as delta


class FullArchiveTests(unittest.TestCase):
    def command(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)

    def fixture(self, root):
        repo = root/'repo'; repo.mkdir()
        self.command(repo, 'init', '-q', '-b', 'main')
        self.command(repo, 'config', 'user.name', 'Archive Test')
        self.command(repo, 'config', 'user.email', 'archive@example.invalid')
        (repo/'source.py').write_text('value = 1\n')
        (repo/'.gitignore').write_text('build/\ndist/\nsource-history.bundle\n')
        (repo/'ROLLBACK.sh').write_text('#!/bin/sh\nexit 0\n')
        self.command(repo, 'add', '.')
        self.command(repo, 'commit', '-qm', 'baseline')
        self.command(repo, 'tag', 'baseline')
        (repo/'source.py').write_text('value = 2\n')
        self.command(repo, 'commit', '-qam', 'updated')
        (repo/'build/original').mkdir(parents=True)
        (repo/'build/original/program.exe').write_bytes(bytes(range(256))*5)
        (repo/'build/original/rom.zar').write_bytes(b'original archive data')
        current = root/'current'; current.mkdir()
        (current/'new.exe').write_bytes(b'new'+bytes(range(256))*5)
        delta.create_source_deltas(repo, current, root/'deltas',
                                  [('build/original/program.exe', 'new.exe', 'program.exe')])
        shutil.copytree(root/'deltas', repo/'build/source-deltas')
        (repo/'dist').mkdir()
        (repo/'dist/Setup.exe').write_bytes(b'fixture installer')
        rows = [dict(path='build/original/program.exe', role='baseline-input'),
                dict(path='build/original/rom.zar', role='baseline-input'),
                dict(path='build/source-deltas/manifest.json', role='recipe'),
                dict(path='build/source-deltas/program.exe.delta.gz', role='recipe'),
                dict(path='dist/Setup.exe', role='installer')]
        plan = dict(schema=1, baseline_directory='build/original', installer='dist/Setup.exe',
                    files=rows, source_manifests=['build/source-deltas/manifest.json'])
        return repo, plan

    def rewrite(self, original, target, mutate):
        with zipfile.ZipFile(original) as src, zipfile.ZipFile(target, 'w') as dst:
            for info in src.infolist():
                dst.writestr(info, mutate(info.filename, src.read(info)))

    def test_standalone_roundtrip_git_history_and_offline_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            commit = self.command(repo, 'rev-parse', 'HEAD').decode().strip()
            baseline = self.command(repo, 'rev-parse', 'baseline').decode().strip()
            before = delta.identity(repo/'build/original/program.exe')
            result = archive.package_full(repo, plan, root/'full.zip')
            self.assertTrue(result['standalone']); self.assertEqual(result['original_roms'], 1)
            archive.extract_full(root/'full.zip', root/'extracted')
            saved = root/'extracted/Dementium-II-CN'
            repo.rename(root/'unavailable-old-workspace')
            restored = archive.restore_git(saved)
            self.assertEqual(restored['source_commit'], commit)
            self.assertEqual(self.command(saved, 'rev-parse', 'baseline').decode().strip(), baseline)
            self.assertEqual(self.command(saved, 'status', '--porcelain', '--untracked-files=no'), b'')
            delta.restore_sources(saved, saved/'build/source-deltas/manifest.json', root/'restored-original')
            self.assertEqual((root/'restored-original/program.exe').read_bytes(), (root/'current/new.exe').read_bytes())
            self.assertEqual(delta.identity(saved/'build/original/program.exe'), before)
            with self.assertRaises(FileExistsError): archive.restore_git(saved)

    def test_reproducible_zip_and_executable_shell_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            archive.package_full(repo, plan, root/'one.zip')
            archive.package_full(repo, plan, root/'two.zip')
            self.assertEqual(delta.identity(root/'one.zip'), delta.identity(root/'two.zip'))
            with zipfile.ZipFile(root/'one.zip') as result:
                info = result.getinfo('Dementium-II-CN/ROLLBACK.sh')
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o755)
                self.assertEqual(info.date_time, archive.ZIP_TIME)
                self.assertFalse(any('/.git/' in name for name in result.namelist()))

    def test_cache_nested_archive_duplicate_rom_and_binary_roles_rejected(self):
        cases = [('build/toolchain/sdk.txt', 'input'), ('build/__pycache__/x.pyc', 'evidence'),
                 ('dist/duplicate.zip', 'input'), ('build/inputs/other/rom.zar', 'evidence'),
                 ('build/inputs/other/rom.zar', 'baseline-input'), ('other.exe', 'evidence'),
                 ('another.exe', 'installer')]
        for path, role in cases:
            with self.subTest(path=path, role=role), self.assertRaises(ValueError):
                archive.permitted(path, role, 'build/original', 'dist/Setup.exe')

    def test_unsafe_and_windows_ambiguous_paths(self):
        for path in ['../x', '/x', 'C:/x', 'a\\b', 'a//b', 'a/../b', 'NUL.txt', 'a/COM1', 'a./b', 'a /b']:
            with self.subTest(path=path), self.assertRaises(ValueError): archive.safe_path(path)

    def test_second_complete_rom_is_rejected_even_within_baseline_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            plan['files'].append(dict(path='build/original/another.zar', role='baseline-input'))
            with self.assertRaisesRegex(ValueError, 'Only one complete'):
                archive.package_full(repo, plan, root/'out.zip')

    def test_dirty_source_stops_before_archive_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            (repo/'source.py').write_text('uncommitted\n')
            with self.assertRaisesRegex(ValueError, 'Commit source'):
                archive.package_full(repo, plan, root/'out.zip')
            self.assertFalse((root/'out.zip').exists())

    def test_duplicate_source_and_explicit_file_stops_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            plan['files'].append(dict(path='source.py', role='evidence'))
            with self.assertRaisesRegex(ValueError, 'Duplicate source'):
                archive.package_full(repo, plan, root/'out.zip')
            self.assertFalse((root/'out.zip').exists())

    def test_missing_delta_baseline_is_not_a_standalone_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            plan['files'] = [r for r in plan['files'] if r['path'] != 'build/original/program.exe']
            with self.assertRaisesRegex(ValueError, 'missing archive input'):
                archive.package_full(repo, plan, root/'out.zip')
            self.assertFalse((root/'out.zip').exists())

    def test_delta_identity_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            (repo/'build/original/program.exe').write_bytes(b'wrong original')
            with self.assertRaisesRegex(ValueError, 'dependency identity'):
                archive.package_full(repo, plan, root/'out.zip')

    def test_mutated_payload_detected_before_extraction_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            archive.package_full(repo, plan, root/'good.zip')
            self.rewrite(root/'good.zip', root/'bad.zip', lambda name, raw: b'changed' if name.endswith('/source.py') else raw)
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                archive.extract_full(root/'bad.zip', root/'extracted')
            self.assertFalse((root/'extracted').exists())

    def test_manifest_disagreement_with_rehashed_envelope_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            archive.package_full(repo, plan, root/'good.zip')
            with zipfile.ZipFile(root/'good.zip') as src:
                manifest = json.loads(src.read(archive.MANIFEST))
                manifest['files'][0]['bytes'] += 1
                raw = delta.canonical(manifest)
                hashes = json.loads(src.read(archive.HASHES))
                hashes[archive.MANIFEST] = delta.digest(raw)
            self.rewrite(root/'good.zip', root/'bad.zip', lambda name, data: raw if name == archive.MANIFEST else delta.canonical(hashes) if name == archive.HASHES else data)
            with self.assertRaisesRegex(ValueError, 'manifest identity'):
                archive.verify_full(root/'bad.zip')

    def test_existing_archive_or_extraction_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            archive.package_full(repo, plan, root/'out.zip')
            original = delta.identity(root/'out.zip')
            with self.assertRaises(FileExistsError): archive.package_full(repo, plan, root/'out.zip')
            self.assertEqual(delta.identity(root/'out.zip'), original)
            (root/'existing').mkdir(); (root/'existing/keep').write_text('untouched')
            with self.assertRaises(FileExistsError): archive.extract_full(root/'out.zip', root/'existing')
            self.assertEqual((root/'existing/keep').read_text(), 'untouched')

    def test_duplicate_case_collision_path_traversal_and_link_members(self):
        cases = [('duplicate', ['same', 'same']), ('case', ['same', 'SAME']),
                 ('traversal', ['../outside']), ('collision', ['thing', 'thing/child']),
                 ('link', ['link'])]
        with tempfile.TemporaryDirectory() as tmp:
            for label, names in cases:
                path = Path(tmp)/(label+'.zip')
                with warnings.catch_warnings(), zipfile.ZipFile(path, 'w') as output:
                    warnings.simplefilter('ignore', UserWarning)
                    for name in names:
                        info = archive.zip_info(name)
                        if label == 'link': info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        output.writestr(info, b'bad')
                with self.subTest(case=label), self.assertRaises(ValueError): archive.verify_full(path)

    def test_shell_executable_mode_loss_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, plan = self.fixture(root)
            archive.package_full(repo, plan, root/'good.zip')
            with zipfile.ZipFile(root/'good.zip') as src, zipfile.ZipFile(root/'bad.zip', 'w') as dst:
                for info in src.infolist():
                    if info.filename.endswith('.sh'): info.external_attr = (stat.S_IFREG | 0o644) << 16
                    dst.writestr(info, src.read(info))
            with self.assertRaisesRegex(ValueError, 'executable mode'): archive.verify_full(root/'bad.zip')

    def test_full_bundle_rejects_external_prerequisites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'history.bundle'
            path.write_bytes(b'# v2 git bundle\n-'+b'a'*40+b' old baseline\n\nPACK')
            with self.assertRaisesRegex(ValueError, 'requires another'): archive.check_bundle_header(path)


if __name__ == '__main__': unittest.main()
