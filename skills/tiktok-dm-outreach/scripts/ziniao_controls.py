"""Reusable helpers for observed invitation controls; no store or round defaults."""

from decimal import Decimal, InvalidOperation
import time


def same_commission(actual, expected):
    """Ignore backend decimal padding, but reject missing/nonfinite values."""
    try:
        a, b = Decimal(str(actual).strip()), Decimal(str(expected).strip())
        return a.is_finite() and b.is_finite() and a == b
    except (InvalidOperation, ValueError):
        return False


def fill_date(value, read_only, native_input, calendar_select):
    """Route from the observed input property; callers provide native actions."""
    if read_only:
        calendar_select(value)
        return 'calendar'
    native_input(value)
    return 'input'


def ensure_overlap_50(read_control, click_control, click_50, *, pause=time.sleep):
    """Verify this open dialog. Readbacks, never click responses, release the gate.

    read_control returns ready/pageSize/selector/expanded for the current dialog.
    The selector must point to its visible value label. No row reads or moves
    belong in the callbacks. Only a known non-interactable click is recoverable.
    """
    def ready():
        for _ in range(8):
            current = read_control()
            if current.get('ready'):
                return current
            pause(.15)
        raise RuntimeError('Overlap page-size control is not ready')

    current = ready()
    if current.get('pageSize') in ('50/页', '50/Page'):
        return {**current, 'changed': False}
    for attempt in range(2):
        if current.get('expanded'):
            break
        try:
            click_control(current['selector'])
            break
        except RuntimeError as error:
            if 'ELEMENT_NOT_INTERACTABLE' not in str(error) or attempt == 1:
                raise
            current = ready()
            if current.get('pageSize') in ('50/页', '50/Page'):
                return {**current, 'changed': True}
    click_50()
    for _ in range(8):
        current = read_control()
        if current.get('ready') and current.get('pageSize') in ('50/页', '50/Page'):
            return {**current, 'changed': True}
        pause(.15)
    raise RuntimeError('Page size is not verified as 50; stop before reading or moving rows')
