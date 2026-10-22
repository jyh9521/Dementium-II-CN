"""Legacy-input importer must reject changed release files before extraction/writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("import_legacy_installer", Path(__file__).resolve().parents[1] / "tools/import_legacy_installer.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LegacyImportTests(unittest.TestCase):
    def test_mismatch_does_not_execute_extractor_or_write_outputs(self):
        for changed in (b"bad", b"verifieD"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                manifest = root / "assets/releases/v1.0.json"
                manifest.parent.mkdir(parents=True)
                manifest.write_text(json.dumps(dict(size=8, sha256=hashlib.sha256(b"verified").hexdigest())), encoding="utf-8")
                installer = root / "old.exe"
                installer.write_bytes(changed)
                with patch.object(MODULE.subprocess, "run") as run:
                    with self.assertRaisesRegex(ValueError, "writes=NONE"):
                        MODULE.import_inputs(installer, root, "7z")
                    run.assert_not_called()
                self.assertFalse((root / "build").exists())
                self.assertFalse((root / "installer").exists())
                self.assertEqual(installer.read_bytes(), changed)


if __name__ == "__main__":
    unittest.main()
