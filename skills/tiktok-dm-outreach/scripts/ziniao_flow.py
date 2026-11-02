"""Shared post-screening invitation flow. Native page actions are supplied by an adapter.

No browser, store, credentials, selectors, current dates, or messages are defaults.
The adapter is a native UI boundary, not a second implementation of this flow.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
import time

from ziniao_controls import ensure_overlap_50, fill_date, same_commission


FULL_SCOPE = 'full-round-through-ziniao-message'
TERMINAL = {'completed', 'cancelled-before-screening', 'cancelled'}


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _utf16(text):
    return len(text.encode('utf-16-le')) // 2


def _account(value):
    name = value.strip().lstrip('@').lower()
    _require(name and '…' not in name and '...' not in name, 'Full account required')
    return name


def _save(path, state):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def _config(confirmation, state):
    _require(confirmation.get('roundKey') == state.get('roundKey') and
             confirmation.get('storeKey') == state.get('storeKey'),
             'Current round/store confirmation is required')
    config = confirmation['config']
    for field in ('message', 'ziniaoMessage'):
        value = config.get(field)
        _require(isinstance(value, str) and value.strip() and _utf16(value) <= 500,
                 field + ' must be independently confirmed, nonempty and <=500 UTF-16 units')
    products = config.get('products', [])
    _require(1 <= len(products) <= 100 and len({p['id'] for p in products}) == len(products),
             'Confirmed product IDs must be unique and nonempty')
    for p in products:
        _require(bool(p['id']) and isinstance(p.get('adEnabled'), bool), 'Invalid product configuration')
        for field in ('standardRate', 'adRate') if p['adEnabled'] else ('standardRate',):
            try:
                rate = Decimal(str(p[field]))
                valid = rate.is_finite() and 1 <= rate <= 80 and rate == rate.quantize(Decimal('.01'))
            except (InvalidOperation, ValueError, KeyError):
                valid = False
            _require(valid, 'Invalid confirmed commission')
    _require(isinstance(config.get('provideSamples'), bool) and
             config.get('sampleMode') in ('follow', 'auto') and
             config.get('contentType') in ('带货视频', '带货直播', '暂无偏好'),
             'Confirmed content/sample configuration required')
    return config


def _fields(state):
    # Both dates must be bound from their own current sources before this entry.
    naming, shop = date.fromisoformat(state['namingDate']), date.fromisoformat(state['shopDate'])
    batch = state['batchNumber']
    _require(type(batch) is int and batch > 0 and bool(state.get('language')), 'Invalid batch/language')
    name = f'自动批{naming:%m%d}（{state["language"]}）{batch}'
    _require(_utf16(name) <= 30, 'Invitation name exceeds 30 UTF-16 units')
    _require(not state.get('invitationName') or state['invitationName'] == name,
             'Bound invitation name disagrees with the round dates/batch')
    return {'name': name, 'endDate': (shop + timedelta(days=20)).isoformat()}


def _verify_form(actual, fields, config):
    expected = {**fields, 'message': config['message'], 'contentType': config['contentType'],
                'phone': '', 'provideSamples': config['provideSamples']}
    if config['provideSamples']:
        expected['sampleMode'] = config['sampleMode']
    for key, value in expected.items():
        observed = actual.get(key)
        if key == 'endDate' and isinstance(observed, str):
            observed = observed.replace('/', '-')
        if key == 'message':
            # Native invitation filtering is normal; never accept lost words.
            filtered = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0E\uFE0F\u200D\u20E3]', '', value)
            _require(observed in (value, filtered), 'Unified form check failed: message')
        else:
            _require(observed == value, 'Unified form check failed: ' + key)
    _require(bool(actual.get('email')), 'System email missing')
    products = actual.get('products', [])
    _require(len(products) == len(config['products']), 'Unified form check failed: product count')
    by_id = {p['id']: p for p in products}
    _require(len(by_id) == len(products), 'Duplicate observed product IDs')
    for p in config['products']:
        observed = by_id.get(p['id'], {})
        _require(observed.get('adEnabled') == p['adEnabled'] and
                 same_commission(observed.get('standardRate'), p['standardRate']) and
                 (not p['adEnabled'] or same_commission(observed.get('adRate'), p['adRate'])),
                 'Unified form check failed: product commission/switch')


def _page_50(ui, pause):
    return ensure_overlap_50(ui.read_page_control, ui.click_page_control, ui.click_50, pause=pause)


def _read_all_conflicts(ui, pause):
    rows, pages = [], set()
    while True:
        if _page_50(ui, pause).get('empty'):
            return rows
        page = ui.read_overlap_page()
        _require(page.get('page') is not None and page['page'] not in pages,
                 'Overlap page did not change; stop without moving')
        pages.add(page['page'])
        rows.extend(page['rows'])
        if not page['hasNext']:
            return rows
        _page_50(ui, pause)
        ui.next_overlap_page()


def _exclude(rows, shop_date):
    excluded, unresolved = set(), set()
    for row in rows:
        account = _account(row['account'])
        if row['invitationName'].startswith('自动批'):
            try:
                old_date = date.fromisoformat(row['invitationDate'])
            except (KeyError, ValueError, TypeError):
                # The user's rule is the month explicitly encoded in 自动批MMDD.
                # Compare that month directly; do not invent an invitation year.
                named = re.match(r'^自动批\D*?(0[1-9]|1[0-2])([0-2][0-9]|3[01])(?!\d)', row['invitationName'])
                if named:
                    try:
                        date(2000, int(named[1]), int(named[2]))
                    except ValueError:
                        unresolved.add(account)
                        continue
                    if int(named[1]) == date.fromisoformat(shop_date).month:
                        excluded.add(account)
                else:
                    unresolved.add(account)
                continue
            if old_date.strftime('%Y-%m') == shop_date[:7]:
                excluded.add(account)
    _require(not (unresolved - excluded), 'Uncertain invitation date; resolve before moving')
    return excluded


def _resolve(ui, state, path, pause):
    _require(not state.get('overlapMovePending'),
             'Previous conflict move is uncertain; inspect existing result before continuing')
    summary = ui.overlap_summary()
    original = {_account(a) for a in summary['accounts']}
    excluded = set(state.get('excludedAccounts', []))
    pending_exclusions = excluded & original
    if pending_exclusions:
        ui.remove_creators(sorted(pending_exclusions))
        summary = ui.overlap_summary()
        _require({_account(a) for a in summary['accounts']} == original - pending_exclusions,
                 'Saved exclusion recipient deletion was not confirmed')
        original -= pending_exclusions
    expected = original.copy()
    previous, unchanged = None, 0
    while summary['hasConflicts']:
        _require({_account(a) for a in summary['accounts']} == expected,
                 'Conflict recipient identity changed unexpectedly')
        ui.open_overlaps()
        rows = _read_all_conflicts(ui, pause)
        _require(all(_account(r['account']) in expected for r in rows),
                 'Conflict account not in current invitation')
        signature = (tuple(sorted(expected)), tuple(sorted(
            (_account(r['account']), r['invitationName'], r.get('productId', ''),
             r.get('invitationDate', '')) for r in rows)))
        unchanged = unchanged + 1 if signature == previous else 0
        previous = signature
        _require(unchanged < 2, 'Conflict handling made no progress; preserve current dialog')
        new_excluded = _exclude(rows, state['shopDate']) - excluded
        if new_excluded:
            ui.close_overlaps()
            excluded |= new_excluded
            state['excludedAccounts'] = sorted(excluded)
            _save(path, state)
            ui.remove_creators(sorted(new_excluded))
            expected -= new_excluded
        elif not rows:
            # Explicitly observed zero-conflict dialogs have no pagination.
            ui.close_overlaps()
        else:
            # Keep every configured product; a later batch may expose more rows.
            _page_50(ui, pause)
            state['overlapMovePending'] = True
            _save(path, state)
            ui.move_conflicts()
            # The move confirmation may close while the overlap list remains.
            state['overlapMovePending'] = False
            _save(path, state)
            ui.close_overlaps()  # Reopen a fresh list for the next batch.
        summary = ui.overlap_summary()
        _require({_account(a) for a in summary['accounts']} == expected,
                 'Deletion/move recipient identity was not confirmed')
        state['overlapMovePending'] = False
        state['conflictPasses'] = state.get('conflictPasses', 0) + 1
        _save(path, state)
    final = {_account(a) for a in summary['accounts']}
    _require(len(final) == len(summary['accounts']) and not (final & excluded),
             'Duplicate/excluded final recipient identities')
    state.update(excludedAccounts=sorted(excluded), finalCount=len(final), finalAccounts=sorted(final))


def run_invitation(state_path, confirmation, ui, *, scope, pause=time.sleep):
    """Run from the selected-creator invitation form; never opens a new round.

    scope is supplied from the latest direct user instruction. ui implements only
    observed native page actions/readbacks documented in the adjacent reference.
    No live actions happen for repair-only, cancelled or already completed work.
    """
    path = Path(state_path)
    state = json.loads(path.read_text(encoding='utf-8'))
    if scope != FULL_SCOPE:
        return {'status': 'scope-no-business-actions', 'stage': state.get('stage')}
    if state.get('stage') in TERMINAL:
        return state
    _require(not state.get('stage', '').endswith('-pending'),
             'Previous external action is uncertain; inspect its existing result, never resend blindly')
    config = _config(confirmation, state)
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    _require(not state.get('flowConfigDigest') or state['flowConfigDigest'] == digest,
             'Confirmed config changed during active invitation; reconcile before continuing')
    _require(state.get('stage') in ('invitation-form', 'form-verified', 'conflicts-resolved',
                                   'invitation-sent', 'messages-open'), 'Unsupported current invitation stage')
    if state.get('invitationSent'):
        _require(state['stage'] in ('invitation-sent', 'messages-open'),
                 'Sent invitation disagrees with stage; do not refill/resend')
    state['flowConfigDigest'] = digest
    _save(path, state)
    _require(ui.identity().get('storeKey') == state['storeKey'], 'Current browser store mismatch')
    if state['stage'] in ('form-verified', 'conflicts-resolved'):
        # A new invocation is a recovery boundary. Prior readbacks do not prove
        # the live form is unchanged. Normal uninterrupted runs still read once.
        _verify_form(ui.form_snapshot(), _fields(state), config)
        if state['stage'] == 'conflicts-resolved':
            current = ui.overlap_summary()
            _require(not current['hasConflicts'] and 'finalAccounts' in state and
                     {_account(a) for a in current['accounts']} == set(state['finalAccounts']) and
                     len(current['accounts']) == state['finalCount'],
                     'Recovered invitation recipient state changed')
    if state['stage'] == 'invitation-form':
        fields = _fields(state)
        control = ui.date_control()
        _require(type(control.get('readOnly')) is bool, 'Observe actual date readOnly first')
        fill_date(fields['endDate'], control['readOnly'], ui.native_date_input, ui.calendar_select)
        ui.fill_fields(fields, config)
        _verify_form(ui.form_snapshot(), fields, config)
        state.update(stage='form-verified', invitationName=fields['name'], endDate=fields['endDate'])
        _save(path, state)
    if state['stage'] == 'form-verified':
        _resolve(ui, state, path, pause)
        state['stage'] = 'conflicts-resolved'
        _save(path, state)
    if state['stage'] == 'conflicts-resolved':
        if not state['finalCount']:
            state.update(stage='completed', nextAction='none-round-completed',
                         invitationSent=False, completionReason='no-remaining-recipients')
            _save(path, state)
            return state
        state['stage'] = 'invitation-send-pending'
        _save(path, state)
        ui.send_invitation()
        _require(ui.invitation_outcome() == 'success', 'Invitation outcome uncertain; do not resend')
        state.update(stage='invitation-sent', invitationSent=True)
        _save(path, state)
    if state['stage'] == 'invitation-sent':
        ui.open_messages()  # Next browser action after observed invitation success.
        state['stage'] = 'messages-open'
        _save(path, state)
    if state['stage'] == 'messages-open':
        preview = ui.prepare_messages(config['ziniaoMessage'])
        selectable, disabled = preview.get('selectable'), preview.get('disabled')
        _require('finalAccounts' in state and
                 {_account(a) for a in preview.get('accounts', [])} == set(state['finalAccounts']) and
                 len(preview.get('accounts', [])) == state['finalCount'],
                 'Message recipient identity mismatch')
        _require(type(selectable) is int and type(disabled) is int and selectable >= 0 and disabled >= 0
                 and selectable + disabled == state['finalCount'], 'Message recipient counts mismatch')
        if selectable == 0 or preview.get('quota') is True:
            result = {'status': 'quota' if preview.get('quota') else 'disabled',
                      'submitted': 0, 'skipped': state['finalCount']}
        else:
            _require(preview.get('text') == config['ziniaoMessage'] and preview.get('enabled') is True
                     and preview.get('invitationCard') is True, 'Confirmed message preview mismatch')
            state['stage'] = 'message-share-pending'
            _save(path, state)
            ui.share_messages()
            result = ui.message_outcome()
            _require(result.get('status') in ('submitted', 'quota'),
                     'Message outcome uncertain; inspect existing result before any retry')
            _require(all(type(result.get(k)) is int and result[k] >= 0 for k in ('submitted', 'skipped'))
                     and result['submitted'] + result['skipped'] == state['finalCount'],
                     'Message outcome recipient counts mismatch')
        state.update(stage='completed', nextAction='none-round-completed', messageResult=result)
        _save(path, state)
    return state
