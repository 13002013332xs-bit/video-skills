import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ziniao_controls as controls


class ControlTests(unittest.TestCase):
    def helper(self, name):
        value = getattr(controls, name, None)
        self.assertTrue(callable(value), f'missing control behavior: {name}')
        return value

    def test_backend_decimal_format_preserves_commission(self):
        same = self.helper('same_commission')
        self.assertTrue(same('10.00', '10'))
        self.assertTrue(same('8.00', '8'))
        self.assertFalse(same('10.01', '10'))
        for bad in ('', 'NaN', 'Infinity', '10x'):
            self.assertFalse(same(bad, '10'))

    def test_readonly_date_uses_calendar_without_direct_input(self):
        actions = []
        value = self.helper('fill_date')(
            '2026-11-10', True,
            lambda v: actions.append(('input', v)),
            lambda v: actions.append(('calendar', v)),
        )
        self.assertEqual(actions, [('calendar', '2026-11-10')])
        self.assertEqual(value, 'calendar')

    def test_writable_date_uses_native_input(self):
        actions = []
        self.helper('fill_date')('2026-11-10', False, actions.append,
                                 lambda _: self.fail('unnecessary calendar'))
        self.assertEqual(actions, ['2026-11-10'])

    def test_already_50_needs_no_click(self):
        check = self.helper('ensure_overlap_50')
        result = check(lambda: {'ready': True, 'pageSize': '50/Page'},
                       lambda _: self.fail('unnecessary click'),
                       lambda: self.fail('unnecessary option click'))
        self.assertEqual(result['pageSize'], '50/Page')

    def test_not_interactable_rereads_and_recovers_same_dialog(self):
        check = self.helper('ensure_overlap_50')
        state = {'ready': True, 'pageSize': '20/页', 'selector': 'current', 'expanded': False}
        attempts = []
        def click(selector):
            attempts.append(selector)
            if len(attempts) == 1:
                state['selector'] = 'fresh'
                raise RuntimeError('ELEMENT_NOT_INTERACTABLE')
            self.assertEqual(selector, 'fresh')
            state['expanded'] = True
        def choose():
            self.assertTrue(state['expanded'])
            state['pageSize'] = '50/页'
        result = check(lambda: dict(state), click, choose, pause=lambda _: None)
        self.assertEqual(result['pageSize'], '50/页')
        self.assertEqual(attempts, ['current', 'fresh'])

    def test_click_success_without_value_change_cannot_pass(self):
        check = self.helper('ensure_overlap_50')
        state = {'ready': True, 'pageSize': '20/页', 'selector': 'current', 'expanded': True}
        with self.assertRaises(RuntimeError):
            check(lambda: dict(state), lambda _: None, lambda: None, pause=lambda _: None)

    def test_connection_error_is_not_retried_as_a_control_error(self):
        check = self.helper('ensure_overlap_50')
        def fail(_):
            raise RuntimeError('BRIDGE_UNAVAILABLE')
        with self.assertRaisesRegex(RuntimeError, 'BRIDGE_UNAVAILABLE'):
            check(lambda: {'ready': True, 'pageSize': '20/页', 'selector': 'current'},
                  fail, lambda: self.fail('must stop'), pause=lambda _: None)


if __name__ == '__main__':
    unittest.main()
