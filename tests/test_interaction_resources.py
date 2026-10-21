import unittest
from test_localize import fixture
from localize import Zar, extract, import_text


class InteractionResourcesTests(unittest.TestCase):
    def test_open_unlock_utf8_bom_and_controls_roundtrip(self):
        zar=Zar(fixture({'EN/OPEN.000':b'\xef\xbb\xbfIt is \x02locked\x01.\r\n','EN/UNLOCK.000':b'Unlocked.'}))
        rows=extract(zar)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]['source'],'It is \x02locked\x01.\r\n')
        self.assertEqual(rows[0]['offset'],3)
        rows[0]['target']='门\x02锁着\x01'
        rows[1]['target']='锁已打开'
        after=Zar(zar.rebuild(import_text(zar,rows)))
        self.assertEqual(after.read('EN/OPEN.000'),'\ufeff门\x02锁着\x01'.encode('utf8'))
        self.assertEqual([r['source'] for r in extract(after)],[r['target'] for r in rows])


if __name__=='__main__':unittest.main()
