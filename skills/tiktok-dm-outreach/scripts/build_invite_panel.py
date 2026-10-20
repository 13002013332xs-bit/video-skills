#!/usr/bin/env python3
"""Build a fresh store-aware invitation panel from the bundled catalog."""
import argparse
import copy
import json
from pathlib import Path
import re
import uuid


def build(catalog_path, output_path, round_key=None):
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    stores = catalog.get('stores')
    if not isinstance(stores, list):
        raise ValueError('Catalog must contain a stores array')
    keys = [str(s.get('key', '')) for s in stores]
    if any(not k for k in keys) or len(set(keys)) != len(keys):
        raise ValueError('Store keys must be nonempty and unique')
    round_key = round_key or 'round-' + uuid.uuid4().hex
    data = {'contextKey': round_key,
            'pendingStoreCount': catalog.get('pendingStoreCount', 0), 'stores': []}
    for original in stores:
        store = copy.deepcopy(original)
        for field in ('initialDraft', 'message', 'ziniaoMessage', 'contactEmail',
                      'shopDate', 'language', 'batchNumber'):
            store.pop(field, None)
        store['contextKey'] = round_key + ':' + str(store['key'])
        data['stores'].append(store)
    template = (root / 'assets/invite-config-template.html').read_text(encoding='utf-8')
    payload = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    result, count = re.subn(
        r'(<script type="application/json" id="invite-catalog-data">).*?(</script>)',
        lambda m: m[1] + payload + m[2], template, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one catalog data element')
    output = Path(output_path).expanduser().resolve()
    if output.is_relative_to(root):
        raise ValueError('Write generated panels to the current project, outside the skill')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'assets/store-catalog.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--round-key', help='Reuse only when resuming the same round')
    args = parser.parse_args()
    print(build(args.catalog, args.output, args.round_key))


if __name__ == '__main__':
    main()
