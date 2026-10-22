"""Offline replay of past failures; this fake replaces only the native page boundary."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))


class Page:
    def __init__(self):
        self.calls = []
        self.form = {}
        self.readonly = True
        self.date_sticks = True
        self.page_size = '20/页'
        self.rows = []
        self.accounts = ['creator_one', 'creator_two']
        self.share_status = 'submitted'
        self.store = 'test-store'
        self.fail_send = False
        self.send_observed = 'success'
        self.hang_page_size = False

    def identity(self):
        self.calls.append('identity')
        return {'storeKey': self.store}

    def date_control(self):
        self.calls.append('date_control')
        return {'readOnly': self.readonly}

    def calendar_select(self, value):
        self.calls.append('calendar')
        self.form['endDate'] = value if self.date_sticks else ''

    def native_date_input(self, value):
        self.calls.append('date_input')
        self.form['endDate'] = value if self.date_sticks else ''

    def fill_fields(self, fields, config):
        self.calls.append('fill_fields')
        self.form.update(name=fields['name'], message=config['message'],
                         contentType=config['contentType'], phone='', email='system@example.invalid',
                         provideSamples=config['provideSamples'], sampleMode=config['sampleMode'],
                         products=[dict(p, standardRate=p['standardRate'] + '.00',
                                        adRate=p['adRate'] + '.00') for p in config['products']])

    def form_snapshot(self):
        self.calls.append('form_snapshot')
        return self.form.copy()

    def overlap_summary(self):
        self.calls.append('overlap_summary')
        return {'hasConflicts': bool(self.rows), 'accounts': self.accounts.copy()}

    def open_overlaps(self):
        self.calls.append('open_overlaps')
        self.page_size = '20/页'  # Every reopen recreates the real regression.

    def read_page_control(self):
        self.calls.append('read_page_control')
        return {'ready': True, 'pageSize': self.page_size, 'selector': '#current-dialog-value'}

    def click_page_control(self, selector):
        self.calls.append('click_page_control')

    def click_50(self):
        self.calls.append('click_50')
        if not self.hang_page_size:
            self.page_size = '50/页'

    def read_overlap_page(self):
        if self.page_size != '50/页':
            raise AssertionError('read before current dialog is 50')
        self.calls.append('read_overlap_page')
        return {'page': 1, 'rows': self.rows.copy(), 'hasNext': False}

    def next_overlap_page(self):
        raise AssertionError('fixture has no next page')

    def close_overlaps(self):
        self.calls.append('close_overlaps')

    def remove_creators(self, accounts):
        self.calls.append('remove_creators')
        self.accounts = [a for a in self.accounts if a not in accounts]
        self.rows = [r for r in self.rows if r['account'] not in accounts]

    def move_conflicts(self):
        if self.page_size != '50/页':
            raise AssertionError('move before reopened dialog is 50')
        self.calls.append('move_conflicts')
        self.rows = []

    def send_invitation(self):
        self.calls.append('send_invitation')
        if self.fail_send:
            raise RuntimeError('native transport timeout')

    def invitation_outcome(self):
        self.calls.append('invitation_outcome')
        return self.send_observed

    def open_messages(self):
        self.calls.append('open_messages')

    def prepare_messages(self, text):
        self.calls.append('prepare_messages')
        return {'text': text, 'enabled': True, 'selectable': len(self.accounts),
                'disabled': 0, 'invitationCard': True, 'accounts': self.accounts.copy()}

    def share_messages(self):
        self.calls.append('share_messages')

    def message_outcome(self):
        self.calls.append('message_outcome')
        return {'status': self.share_status, 'submitted': len(self.accounts), 'skipped': 0}


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.json'
        self.state = {'roundKey': 'fixture-round', 'storeKey': 'test-store',
                      'stage': 'invitation-form', 'namingDate': '2026-12-01',
                      'shopDate': '2026-11-30', 'language': '英语', 'batchNumber': 2,
                      'executionScope': 'full-round-through-ziniao-message'}
        self.confirmed = {'roundKey': 'fixture-round', 'storeKey': 'test-store',
                          'config': {'message': 'Approved invitation', 'ziniaoMessage': 'Approved DM',
                                     'contentType': '带货视频', 'provideSamples': True,
                                     'sampleMode': 'follow', 'products': [{'id': 'sample-item',
                                     'standardRate': '10', 'adEnabled': True, 'adRate': '8'}]}}
        self.ui = Page()

    def run_flow(self, scope=None):
        self.path.write_text(json.dumps(self.state), encoding='utf-8')
        spec = importlib.util.find_spec('ziniao_flow')
        self.assertIsNotNone(spec, 'No shared invitation entry exists to enforce these steps')
        flow = importlib.import_module('ziniao_flow')
        return flow.run_invitation(self.path, self.confirmed, self.ui,
                                   scope=scope or self.state['executionScope'], pause=lambda _: None)

    def test_readonly_calendar_and_decimal_padding_complete_in_order(self):
        result = self.run_flow()
        self.assertEqual(result['stage'], 'completed')
        self.assertEqual(self.ui.form['name'], '自动批1201（英语）2')
        self.assertEqual(self.ui.form['endDate'], '2026-12-20')
        self.assertIn('calendar', self.ui.calls)
        self.assertNotIn('date_input', self.ui.calls)
        self.assertEqual(self.ui.calls.count('form_snapshot'), 1)
        i = self.ui.calls.index('invitation_outcome')
        self.assertEqual(self.ui.calls[i + 1], 'open_messages')

    def test_readonly_calendar_return_is_insufficient_when_value_did_not_stick(self):
        self.ui.date_sticks = False
        with self.assertRaisesRegex(RuntimeError, 'endDate'):
            self.run_flow()
        self.assertNotIn('send_invitation', self.ui.calls)

    def test_repair_only_does_not_even_read_or_navigate_browser(self):
        self.assertEqual(self.run_flow(scope='repair-only')['status'], 'scope-no-business-actions')
        self.assertEqual(self.ui.calls, [])

    def test_completed_round_does_not_restart_from_old_confirmation(self):
        self.state.update(stage='completed', invitationSent=True)
        self.assertEqual(self.run_flow()['stage'], 'completed')
        self.assertEqual(self.ui.calls, [])

    def test_stale_round_confirmation_stops_before_browser(self):
        self.confirmed['roundKey'] = 'older-round'
        with self.assertRaisesRegex(RuntimeError, 'confirmation'):
            self.run_flow()
        self.assertEqual(self.ui.calls, [])

    def test_other_store_confirmation_stops_before_browser(self):
        self.confirmed['storeKey'] = 'another-store'
        with self.assertRaisesRegex(RuntimeError, 'confirmation'):
            self.run_flow()
        self.assertEqual(self.ui.calls, [])

    def test_current_browser_identity_must_match_store(self):
        self.ui.store = 'another-store'
        with self.assertRaisesRegex(RuntimeError, 'store'):
            self.run_flow()
        self.assertNotIn('fill_fields', self.ui.calls)

    def test_any_current_shop_month_auto_product_excludes_whole_creator(self):
        self.ui.rows = [
            {'account': 'creator_one', 'invitationName': 'manual1130', 'invitationDate': '2026-11-30'},
            {'account': 'creator_one', 'invitationName': '自动批1129（英语）1', 'invitationDate': '2026-11-29'},
            {'account': 'creator_two', 'invitationName': 'manual1130', 'invitationDate': '2026-11-30'}]
        result = self.run_flow()
        self.assertEqual(result['excludedAccounts'], ['creator_one'])
        self.assertEqual(result['finalCount'], 1)
        self.assertEqual(self.ui.calls.count('remove_creators'), 1)
        self.assertEqual(self.ui.calls.count('click_50'), 2)
        self.assertLess(self.ui.calls.index('remove_creators'), self.ui.calls.index('move_conflicts'))

    def test_page_size_click_without_readback_never_releases_row_read(self):
        self.ui.rows = [{'account': 'creator_one', 'invitationName': 'manual1130',
                         'invitationDate': '2026-11-30'}]
        self.ui.hang_page_size = True
        with self.assertRaisesRegex(RuntimeError, '50'):
            self.run_flow()
        self.assertNotIn('read_overlap_page', self.ui.calls)
        self.assertNotIn('move_conflicts', self.ui.calls)

    def test_send_timeout_records_unknown_and_resume_does_not_send_again(self):
        self.ui.fail_send = True
        with self.assertRaisesRegex(RuntimeError, 'timeout'):
            self.run_flow()
        self.state = json.loads(self.path.read_text())
        self.assertEqual(self.state['stage'], 'invitation-send-pending')
        self.ui.calls.clear()
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            self.run_flow()
        self.assertEqual(self.ui.calls, [])

    def test_sent_invitation_resumes_at_messages_without_form_or_resend(self):
        self.state.update(stage='invitation-sent', invitationSent=True, finalCount=2,
                          finalAccounts=['creator_one', 'creator_two'])
        result = self.run_flow()
        self.assertEqual(result['stage'], 'completed')
        self.assertNotIn('fill_fields', self.ui.calls)
        self.assertNotIn('send_invitation', self.ui.calls)
        self.assertEqual(self.ui.calls[1], 'open_messages')

    def test_quota_is_completed_without_retry_or_postcheck(self):
        self.ui.share_status = 'quota'
        result = self.run_flow()
        self.assertEqual(result['stage'], 'completed')
        self.assertEqual(result['messageResult']['status'], 'quota')
        self.assertEqual(self.ui.calls.count('share_messages'), 1)
        self.assertEqual(self.ui.calls[-1], 'message_outcome')

    def test_wrong_message_preview_blocks_share(self):
        self.ui.prepare_messages = lambda text: {'text': 'Old default', 'enabled': True,
            'selectable': 2, 'disabled': 0, 'invitationCard': True, 'accounts': self.ui.accounts}
        with self.assertRaisesRegex(RuntimeError, 'message preview'):
            self.run_flow()
        self.assertNotIn('share_messages', self.ui.calls)

    def test_mutating_confirmed_config_during_resume_is_rejected(self):
        self.run_flow()
        self.state = json.loads(self.path.read_text())
        self.state['stage'] = 'invitation-sent'
        self.confirmed['config']['message'] = 'Changed after invitation'
        self.ui.calls.clear()
        with self.assertRaisesRegex(RuntimeError, 'config changed'):
            self.run_flow()
        self.assertEqual(self.ui.calls, [])

    def test_true_commission_difference_never_sends(self):
        snapshot = self.ui.form_snapshot
        def changed():
            result = snapshot()
            result['products'][0]['standardRate'] = '10.01'
            return result
        self.ui.form_snapshot = changed
        with self.assertRaisesRegex(RuntimeError, 'commission'):
            self.run_flow()
        self.assertNotIn('send_invitation', self.ui.calls)

    def test_disabled_recipients_complete_without_share_or_extra_browser_checks(self):
        self.ui.prepare_messages = lambda text: {'selectable': 0, 'disabled': 2,
                                                'accounts': self.ui.accounts}
        result = self.run_flow()
        self.assertEqual(result['messageResult'], {'status': 'disabled', 'submitted': 0, 'skipped': 2})
        self.assertNotIn('share_messages', self.ui.calls)

    def test_quota_visible_before_share_does_not_share(self):
        self.ui.prepare_messages = lambda text: {'selectable': 2, 'disabled': 0, 'quota': True,
                                                'accounts': self.ui.accounts}
        result = self.run_flow()
        self.assertEqual(result['messageResult'], {'status': 'quota', 'submitted': 0, 'skipped': 2})
        self.assertNotIn('share_messages', self.ui.calls)

    def test_ambiguous_auto_date_blocks_moving_or_sending(self):
        self.ui.rows = [{'account': 'creator_one', 'invitationName': '自动批1129（英语）1'}]
        with self.assertRaisesRegex(RuntimeError, 'Uncertain invitation date'):
            self.run_flow()
        self.assertNotIn('move_conflicts', self.ui.calls)
        self.assertNotIn('send_invitation', self.ui.calls)

    def test_resuming_form_verified_rechecks_changed_form_once(self):
        self.state.update(stage='form-verified', finalCount=2)
        with self.assertRaisesRegex(RuntimeError, 'Unified form check'):
            self.run_flow()
        self.assertEqual(self.ui.calls.count('form_snapshot'), 1)
        self.assertNotIn('send_invitation', self.ui.calls)

    def test_share_timeout_cannot_trigger_second_share_on_resume(self):
        def timeout():
            self.ui.calls.append('share_messages')
            raise RuntimeError('share timeout')
        self.ui.share_messages = timeout
        with self.assertRaisesRegex(RuntimeError, 'share timeout'):
            self.run_flow()
        self.state = json.loads(self.path.read_text())
        self.assertEqual(self.state['stage'], 'message-share-pending')
        self.ui.calls.clear()
        with self.assertRaisesRegex(RuntimeError, 'uncertain'):
            self.run_flow()
        self.assertEqual(self.ui.calls, [])

    def test_recovered_conflicts_resolved_does_not_send_changed_recipients(self):
        self.ui.fail_send = True
        with self.assertRaises(RuntimeError):
            self.run_flow()
        self.state = json.loads(self.path.read_text())
        self.state['stage'] = 'conflicts-resolved'  # Explicitly reconciled as unsent.
        self.ui.calls.clear()
        self.ui.fail_send = False
        self.ui.accounts = ['different_creator', 'creator_two']
        with self.assertRaisesRegex(RuntimeError, 'recipient'):
            self.run_flow()
        self.assertNotIn('send_invitation', self.ui.calls)

    def test_same_count_wrong_message_recipients_blocks_share(self):
        prepare = self.ui.prepare_messages
        def wrong(text):
            result = prepare(text)
            result['accounts'] = ['different_creator', 'creator_two']
            return result
        self.ui.prepare_messages = wrong
        with self.assertRaisesRegex(RuntimeError, 'recipient'):
            self.run_flow()
        self.assertNotIn('share_messages', self.ui.calls)

    def test_saved_exclusion_plan_is_applied_even_if_conflict_disappears(self):
        self.state['excludedAccounts'] = ['creator_one']
        result = self.run_flow()
        self.assertEqual(result['finalAccounts'], ['creator_two'])
        self.assertEqual(result['finalCount'], 1)
        self.assertEqual(self.ui.calls.count('remove_creators'), 1)
        self.assertLess(self.ui.calls.index('remove_creators'), self.ui.calls.index('send_invitation'))


if __name__ == '__main__':
    unittest.main()
