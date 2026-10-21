"""Offline full-inventory layout gates with synthetic text only."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_text_layout import audit
from font_pipeline import wrap_text,glyph_width,layout_document
from localize import TOKEN


class FullTextLayoutTests(unittest.TestCase):
    def setUp(self):
        self.meta={'glyphs':{'0':{'logw':12}},'linefeed':16}
        self.profile={'document_width':228,'review_width':240,'forbidden_start':'，。！？）','forbidden_end':'（','document_defaults':{'min_tail_width':52}}

    def test_emphasized_phrase_stays_atomic_and_tokens_are_preserved(self):
        source='甲乙丙丁甲乙丙丁\x02匕首\x01的槽。'
        result=wrap_text(source,self.meta,129,'，。','（',52)
        self.assertIn('\x02匕首\x01',result)
        self.assertEqual(TOKEN.findall(result),TOKEN.findall(source))
        self.assertTrue(all(s.count('\x02')==s.count('\x01') for s in result.splitlines()))

    def test_variable_tail_uses_placeholder_width_without_creating_extra_row(self):
        source='甲乙丙丁甲乙丙丁你：$Dagger,0$'
        result=wrap_text(source,self.meta,129,'，。','（',52)
        self.assertEqual(len(result.splitlines()),2)
        self.assertTrue(all(glyph_width(line,self.meta)<=129 for line in result.splitlines()))
        self.assertEqual(TOKEN.findall(result),TOKEN.findall(source))

    def test_intentional_indentation_is_preserved_when_configured(self):
        source='   甲乙   丙丁\n\n  丁丙  乙甲'
        result=layout_document(source,self.meta,self.profile,{'preserve_whitespace':True,'min_tail_width':52})
        self.assertEqual(result,source)

    def run_audit(self,logical,compiled,resource='EN/EXAMINE.000'):
        row={'id':resource+':0000','resource':resource,'source':logical,'target':logical,'context':'document','prefix':''}
        actual={'id':row['id'],'source':compiled,'prefix':''}
        archive=type('FixtureArchive',(),{'read':lambda _,name:json.dumps(self.meta).encode()})()
        with patch('audit_text_layout.extract',return_value=[actual]):
            return audit(archive,[row],self.profile)

    def test_generated_short_tail_is_red_but_authored_heading_is_not(self):
        report=self.run_audit('甲乙丙丁甲乙丙。','甲乙丙丁甲乙\n丙。')
        self.assertIn('generated-short-tail',[i['code'] for i in report['issues']])
        report=self.run_audit('我\n甲乙丙丁','我\n甲乙丙丁')
        self.assertEqual(report['issues'],[])

    def test_control_span_split_is_a_separate_failure(self):
        report=self.run_audit('甲乙\x02匕首\x01丙丁','甲乙\x02匕\n首\x01丙丁')
        self.assertEqual(sum(i['code']=='split-emphasis' for i in report['issues']),2)

    def test_invalid_table_record_break_is_red(self):
        report=self.run_audit('甲乙丙丁','甲乙\n丙丁','EN/GUI.TBL')
        self.assertIn('physical-record-break',[i['code'] for i in report['issues']])


if __name__=='__main__':unittest.main()
