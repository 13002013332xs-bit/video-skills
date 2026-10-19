"""Evaluate already observed creator PPS; no browser, account or sending access."""
import argparse
from decimal import Decimal, InvalidOperation
import json
import re


def _score(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('PPS must be a finite score from 0 to 5') from None
    if not number.is_finite() or not Decimal('0') <= number <= Decimal('5'):
        raise ValueError('PPS must be a finite score from 0 to 5')
    return number


def parse_pps(card_text):
    if card_text is None:
        return None
    text = str(card_text).strip().replace('：', ':').replace('／', '/')
    match = re.fullmatch(r'(?:PPS\s*:?\s*)?([0-9]+(?:\.[0-9]+)?)\s*(?:/\s*(5(?:\.0+)?))?', text, re.IGNORECASE)
    if not match:
        return None
    try:
        return _score(match.group(1))
    except ValueError:
        return None


def evaluate_pps(card_text, *, selected_scores=None, minimum=None, maximum=None):
    selected = None if selected_scores is None else {_score(x) for x in selected_scores}
    if selected and (minimum is not None or maximum is not None):
        raise ValueError('Choose explicit scores or a range, not both')
    lower = None if minimum is None else _score(minimum)
    upper = None if maximum is None else _score(maximum)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError('PPS minimum exceeds maximum')
    score = parse_pps(card_text)
    if not selected and lower is None and upper is None:
        status = 'not_required'
    elif score is None:
        status = 'pending'
    elif selected:
        status = 'eligible' if score in selected else 'excluded'
    else:
        status = 'eligible' if (lower is None or score >= lower) and (upper is None or score <= upper) else 'excluded'
    return {'status': status, 'score': None if score is None else str(score), 'full_score': '5.0' if score is not None else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('card_text', help='Observed PPS, e.g. 4.9 / 5.0')
    parser.add_argument('--scores', nargs='+')
    parser.add_argument('--min', dest='minimum')
    parser.add_argument('--max', dest='maximum')
    args = parser.parse_args()
    try:
        result = evaluate_pps(args.card_text, selected_scores=args.scores, minimum=args.minimum, maximum=args.maximum)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
