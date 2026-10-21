from pathlib import Path
import tempfile
import unittest

from localize import write_json
from package_probe import text_payload


class PackagingTests(unittest.TestCase):
    def test_checkout_line_endings_do_not_change_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
            self.assertEqual(text_payload(path), b'{\n  "value": 1\n}\n')

    def test_generated_json_uses_lf_on_all_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.json'
            write_json(path, {'value': '中文'})
            self.assertNotIn(b'\r', path.read_bytes())
