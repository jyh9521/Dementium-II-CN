"""Synthetic archival delta, exact incremental scope, and pre-write guards."""
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import archive_increment as archive
from test_localize import fixture


class SourceDeltaTests(unittest.TestCase):
    def test_binary_shift_insert_remove_and_empty(self):
        source = bytes(range(256)) * 30 + b'old footer'
        for target in [source, b'insert' + source[100:-10] + b'new end', b'', b'new']:
            with self.subTest(size=len(target)):
                delta = archive.make_delta(source, target)
                self.assertEqual(archive.apply_delta(source, delta), target)

    def test_zar_rename_and_reorder_preserves_exact_padding(self):
        source = fixture({'A': b'A' * 2000, 'B': b'B' * 513, 'C': b'old'})
        target = bytearray(fixture({'A': b'A' * 2000, 'C': b'new', 'D': b'B' * 513}))
        target[900:908] = b'gapbytes'
        delta = archive.make_delta(source, bytes(target), 'zar')
        self.assertEqual(delta['copied_bytes'], 2513)
        self.assertEqual(archive.apply_delta(source, delta), bytes(target))

    def test_wrong_baseline_and_tampered_copy_rejected(self):
        source = bytes(range(256)) * 4
        delta = archive.make_delta(source, b'new' + source)
        with self.assertRaisesRegex(ValueError, 'baseline identity'):
            archive.apply_delta(b'x' + source[1:], delta)
        bad = copy.deepcopy(delta)
        next(op for op in bad['operations'] if op[0] == 'copy')[1] = -1
        with self.assertRaisesRegex(ValueError, 'COPY bounds'):
            archive.apply_delta(source, bad)
        bad = copy.deepcopy(delta)
        bad['target']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'target identity'):
            archive.apply_delta(source, bad)

    def setup_files(self, root):
        base, current = root/'base', root/'current'
        for path in [base, current]:
            (path/'build/original').mkdir(parents=True)
        (base/'build/original/program.exe').write_bytes(bytes(range(256)) * 4)
        (current/'build/original/program.exe').write_bytes(b'NEW' + bytes(range(256)) * 4)
        manifest = root/'deltas/manifest.json'
        archive.create_source_deltas(base, current, manifest.parent,
            [('build/original/program.exe', 'build/original/program.exe', 'program.exe')])
        return base, current, manifest

    def test_restore_is_new_directory_and_exact_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current, manifest = self.setup_files(root)
            baseline = archive.identity(base/'build/original/program.exe')
            result = archive.restore_sources(base, manifest, root/'restored')
            self.assertEqual(result['program.exe'], archive.identity(current/'build/original/program.exe'))
            self.assertEqual((root/'restored/program.exe').read_bytes(), (current/'build/original/program.exe').read_bytes())
            self.assertEqual(baseline, archive.identity(base/'build/original/program.exe'))
            with self.assertRaises(FileExistsError):
                archive.restore_sources(base, manifest, root/'restored')
            with self.assertRaisesRegex(ValueError, 'overlaps'):
                archive.restore_sources(base, manifest, base/'new')

    def test_restore_preflights_every_input_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _, manifest = self.setup_files(root)
            data = json.loads(manifest.read_text())
            data['files'].append(dict(data['files'][0], output_path='second.exe', delta='absent.delta.gz'))
            manifest.write_bytes(archive.canonical(data))
            with self.assertRaises(FileNotFoundError):
                archive.restore_sources(base, manifest, root/'restored')
            self.assertFalse((root/'restored').exists())

    def test_restore_rejects_changed_delta_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _, manifest = self.setup_files(root)
            delta = manifest.parent/'program.exe.delta.gz'
            delta.write_bytes(delta.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'input identity'):
                archive.restore_sources(base, manifest, root/'restored')
            self.assertFalse((root/'restored').exists())

    def test_empty_manifest_is_not_a_successful_restoration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _, manifest = self.setup_files(root)
            data = json.loads(manifest.read_text())
            data['files'] = []
            manifest.write_bytes(archive.canonical(data))
            with self.assertRaisesRegex(ValueError, 'at least one file'):
                archive.restore_sources(base, manifest, root/'restored')
            self.assertFalse((root/'restored').exists())

    def test_unsafe_relative_paths(self):
        for value in ['../x', '/x', 'C:/x', 'a\\b', 'a//b', './x', 'a/../b', '']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                archive.relative_path(value)

    def test_manifest_output_traversal_and_duplicate_are_prewrite_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, _, manifest = self.setup_files(root)
            original = json.loads(manifest.read_text())
            for value in ['../outside.exe', 'nested/program.exe']:
                bad = copy.deepcopy(original)
                bad['files'][0]['output_path'] = value
                manifest.write_bytes(archive.canonical(bad))
                with self.assertRaises(ValueError):
                    archive.restore_sources(base, manifest, root/'restored')
                self.assertFalse((root/'restored').exists())
            bad = copy.deepcopy(original)
            bad['files'].append(bad['files'][0])
            manifest.write_bytes(archive.canonical(bad))
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                archive.restore_sources(base, manifest, root/'restored')
            self.assertFalse((root/'restored').exists())


class IncrementPackageTests(unittest.TestCase):
    def command(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)

    def setup_repositories(self, root):
        base, current = root/'base', root/'current'
        base.mkdir()
        self.command(base, 'init', '-q')
        self.command(base, 'config', 'user.name', 'Archive Test')
        self.command(base, 'config', 'user.email', 'archive@example.invalid')
        for name, value in [('same.txt', 'same'), ('change.txt', 'old'), ('removed.txt', 'removed'), ('.gitignore', 'dist/\nevidence/\n')]:
            (base/name).write_text(value)
        self.command(base, 'add', '.')
        self.command(base, 'commit', '-qm', 'baseline')
        subprocess.check_output(['git', 'clone', '-q', str(base), str(current)], stderr=subprocess.PIPE)
        self.command(current, 'config', 'user.name', 'Archive Test')
        self.command(current, 'config', 'user.email', 'archive@example.invalid')
        (current/'change.txt').write_text('new')
        (current/'added.txt').write_text('added')
        (current/'removed.txt').unlink()
        self.command(current, 'add', '-A')
        self.command(current, 'commit', '-qm', 'increment')
        return base, current

    def test_exact_changed_scope_and_deleted_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            result = archive.package_increment(current, base, root/'out.zip', bundle=True)
            self.assertEqual(result['result'], 'PASS')
            with zipfile.ZipFile(root/'out.zip') as output:
                manifest = json.loads(output.read('INCREMENT_MANIFEST.json'))
                self.assertEqual({r['path'] for r in manifest['files']}, {
                    'Dementium-II-CN/added.txt', 'Dementium-II-CN/change.txt', 'Dementium-II-CN/source-history.bundle'})
                self.assertEqual([r['path'] for r in manifest['deleted_tracked_paths']], ['Dementium-II-CN/removed.txt'])
                self.assertNotIn('Dementium-II-CN/same.txt', output.namelist())
            self.assertEqual((base/'change.txt').read_text(), 'old')

    def test_only_explicit_installer_and_no_originals_or_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            (current/'dist').mkdir()
            (current/'dist/Setup.exe').write_bytes(b'installer')
            archive.package_increment(current, base, root/'out.zip', installer='dist/Setup.exe')
            for bad in ['build/original/rom.zar', 'build/original/Dementium II.exe', 'build/toolchain/a.json', 'evidence/__pycache__/x.pyc']:
                with self.subTest(path=bad), self.assertRaisesRegex(ValueError, 'Excluded'):
                    archive._permitted(bad, 'dist/Setup.exe')

    def test_dirty_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            (current/'added.txt').write_text('uncommitted')
            with self.assertRaisesRegex(ValueError, 'Commit source'):
                archive.package_increment(current, base, root/'out.zip')
            self.assertFalse((root/'out.zip').exists())

    def test_zip_readback_detects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            archive.package_increment(current, base, root/'good.zip')
            with zipfile.ZipFile(root/'good.zip') as original, zipfile.ZipFile(root/'bad.zip', 'w') as modified:
                for name in original.namelist():
                    modified.writestr(name, b'corrupt' if name.endswith('/added.txt') else original.read(name))
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                archive.verify_increment(root/'bad.zip')

    def test_reproducible_zip_bytes_without_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            archive.package_increment(current, base, root/'one.zip')
            archive.package_increment(current, base, root/'two.zip')
            self.assertEqual((root/'one.zip').read_bytes(), (root/'two.zip').read_bytes())

    def test_explicit_unchanged_input_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base, current = self.setup_repositories(root)
            for repo in [base, current]:
                (repo/'evidence').mkdir()
                (repo/'evidence/prior.json').write_text('{"same":true}')
            archive.package_increment(current, base, root/'out.zip', includes=['evidence/prior.json'])
            with zipfile.ZipFile(root/'out.zip') as output:
                self.assertNotIn('Dementium-II-CN/evidence/prior.json', output.namelist())

    def test_zip_path_traversal_is_rejected_before_manifest_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'bad.zip'
            with zipfile.ZipFile(output, 'w') as archive_file:
                archive_file.writestr('../outside', b'bad')
            with self.assertRaisesRegex(ValueError, 'Unsafe relative'):
                archive.verify_increment(output)


if __name__ == '__main__':
    unittest.main()
