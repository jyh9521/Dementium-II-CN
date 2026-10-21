"""Synthetic editorial policy tests; no game files are required."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lint_locale import lint


class LocaleStyleTests(unittest.TestCase):
    def row(self, target, kind='ui', **extra):
        return {'id': 'fixture:0000', 'target': target, 'text_type': kind, **extra}

    def test_ui_unpunctuated_sentence_omits_period(self):
        self.assertEqual(lint([self.row('按任意键继续')]), [])
        self.assertEqual(lint([self.row('按任意键继续。')])[0]['code'], 'ui-terminal-period')
        self.assertTrue(lint([self.row('Continue.')]))

    def test_narrative_period_allowed(self):
        self.assertEqual(lint([self.row('他回来了。', 'narrative')]), [])

    def test_internal_punctuation_allows_terminal_period(self):
        self.assertEqual(lint([self.row('解毒剂：解除中毒。'), self.row('门锁着，需要钥匙。')]), [])

    def test_semantic_question_exclamation_ellipsis_preserved(self):
        self.assertEqual(lint([self.row('保存进度？'), self.row('消灭敌人！'), self.row('……保存中……')]), [])

    def test_control_code_and_variable_commas_not_punctuation(self):
        self.assertTrue(lint([self.row('按\x02$Lock,1$\x01继续。')]))
        self.assertTrue(lint([self.row('按{key,name}继续。')]))

    def test_each_display_segment_is_checked(self):
        issues = lint([self.row('物品：|\x02恢复生命。')])
        self.assertEqual(len(issues), 1)
        self.assertIn('segment 2', issues[0]['message'])

    def test_token_containing_delimiter_is_not_display_segment(self):
        issues = lint([self.row('按$Keypad,A|B$继续。')])
        self.assertEqual(len(issues), 1)
        self.assertIn('segment 1', issues[0]['message'])

    def test_missing_unknown_classification_is_error(self):
        self.assertEqual(lint([{'id': 'a', 'target': '文本'}])[0]['code'], 'text-type')
        self.assertTrue(lint([self.row('文本', 'unknown')]))

    def test_preservation_reason_required(self):
        self.assertTrue(lint([self.row('AZERTY', 'preserved')]))
        self.assertEqual(lint([self.row('AZERTY', 'preserved', notes='Keyboard layout identifier')]), [])
        self.assertEqual(lint([self.row('AZERTY', 'preserved')], {'require_preservation_note': False}), [])

    def test_configuration_is_locale_neutral(self):
        self.assertEqual(lint([self.row('继续。')], {'terminal_periods': ['.']}), [])
        self.assertTrue(lint([self.row('Continue.')], {'terminal_periods': ['.']}))

    def test_invalid_target_and_configuration(self):
        self.assertEqual(lint([self.row(None)])[0]['code'], 'target-type')
        with self.assertRaises(ValueError):
            lint([], {'terminal_periods': ['...']})


if __name__ == '__main__':
    unittest.main()
