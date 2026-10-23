from pathlib import Path
import argparse, json
from .parser import parse_pdf


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get('children', []))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Parse a CT-200 PDF into a nested JSON tree')
    ap.add_argument('pdf', nargs='?', default='data/ct200_manual.pdf')
    ap.add_argument('--out', default='output/ct200_tree.json')
    args = ap.parse_args()
    result = parse_pdf(args.pdf)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.pop('flat_sections', None)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    count = sum(1 for _ in walk(result['sections']))
    print(f"Parsed {result['source_file']}: {result['page_count']} pages, {count} sections")
    print(f"Warnings: {len(result['warnings'])}; JSON: {out}")
    for warning in result['warnings']:
        print(f"WARNING: {warning}")
