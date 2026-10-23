"""CT-200-specific PDF structure extraction using native PDF text first.

This is intentionally not a generic parser. It retains section-number paths,
page provenance, paragraphs, numbered/bulleted list items, and warnings for
unrecognized content. OCR is not invoked because the supplied manuals expose
an extractable text layer; scanned pages would need an OCR fallback.
"""
from __future__ import annotations
import re
import hashlib
from pathlib import Path
from typing import Any
import fitz

HEADING_RE = re.compile(r'^\s*(\d+(?:\.\d+){0,5}\.?)\s+(.+?)\s*$')
LIST_RE = re.compile(r'^\s*(?:\d+[.)]|[•●▪◦-])\s+(.+?)\s*$')
PAGE_MARKER_RE = re.compile(r'^\s*<PARSED TEXT FOR PAGE:.*>$')


def sha256(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _new_node(number: str, title: str, page: int, parent_number: str | None) -> dict[str, Any]:
    return {
        'number': number, 'heading': title.strip(), 'level': number.count('.') + 1,
        'page_start': page, 'page_end': page, 'parent_number': parent_number,
        'body_parts': [], 'children': [], 'warnings': [],
    }


def parse_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Return a nested tree and extraction diagnostics for the CT-200 manual."""
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)
    roots: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    warnings: list[str] = []
    current_page = 0
    body_without_section: list[str] = []

    # Use text blocks in reading order. Native text is preferred over OCR to
    # avoid OCR errors on numeric safety thresholds.
    for page_index, page in enumerate(doc, start=1):
        current_page = page_index
        blocks = page.get_text('blocks', sort=True)
        for block in blocks:
            raw = str(block[4] or '')
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            for line in lines:
                if PAGE_MARKER_RE.match(line):
                    continue
                if line.lower().startswith('cardiotrack ct-200 home blood') or line.lower().startswith('pressure monitor — technical'):
                    continue
                match = HEADING_RE.match(line)
                if match:
                    number, title = match.group(1).rstrip('.'), match.group(2).strip()
                    # Section numbers in this document are stronger signals
                    # than visual font sizes. A heading is accepted only when
                    # the line starts with a plausible section number.
                    level = number.count('.') + 1
                    while stack and stack[-1]['level'] >= level:
                        stack.pop()
                    parent = stack[-1] if stack else None
                    # If a parent level is missing (e.g. 2.1.1.1), attach to
                    # the nearest existing numbered ancestor and expose warning.
                    expected_parent = '.'.join(number.split('.')[:-1]) or None
                    actual_parent = parent['number'] if parent else None
                    node = _new_node(number, title, current_page, actual_parent)
                    if expected_parent and actual_parent != expected_parent:
                        node['warnings'].append(f'Missing or non-adjacent parent heading {expected_parent}; attached to {actual_parent or "document root"}.')
                        warnings.append(f'Page {current_page}: {number} {title} has no immediate parent heading {expected_parent}.')
                    # Do not merge repeated heading titles: section number and
                    # occurrence are retained, with IDs assigned downstream.
                    if parent:
                        parent['children'].append(node)
                    else:
                        roots.append(node)
                    stack.append(node)
                    flat.append(node)
                    continue
                if not line or line.startswith('•') and len(line) == 1:
                    continue
                if stack:
                    item_match = LIST_RE.match(line)
                    if item_match:
                        stack[-1]['body_parts'].append({'type': 'list_item', 'text': item_match.group(1), 'page': current_page})
                    else:
                        stack[-1]['body_parts'].append({'type': 'paragraph', 'text': line, 'page': current_page})
                    stack[-1]['page_end'] = current_page
                else:
                    body_without_section.append(line)

    # Coalesce line-wrapped PDF text into paragraphs while preserving list rows.
    def finalize(node: dict[str, Any]) -> None:
        parts = node['body_parts']
        merged: list[dict[str, Any]] = []
        for part in parts:
            if part['type'] == 'list_item':
                merged.append(part)
            elif merged and merged[-1]['type'] == 'paragraph' and merged[-1]['page'] == part['page']:
                merged[-1]['text'] += ' ' + part['text']
            else:
                merged.append(dict(part))
        node['body'] = '\n'.join((('- ' if p['type'] == 'list_item' else '') + p['text']) for p in merged).strip()
        node['content_hash'] = sha256(node['heading'] + '\n' + node['body'])
        del node['body_parts']
        for child in node['children']:
            finalize(child)
    for root in roots:
        finalize(root)

    if body_without_section:
        warnings.append(f'{len(body_without_section)} text lines appeared before the first recognized section and were not assigned to a section.')
    if not roots:
        warnings.append('No numbered headings were recognized. Check whether the PDF has a text layer or requires OCR.')
    return {
        'document_title': 'CardioTrack CT-200 Home Blood Pressure Monitor — Technical & User Manual',
        'source_file': pdf_path.name,
        'page_count': len(doc),
        'sections': roots,
        'flat_sections': flat,
        'warnings': warnings,
        'parser_notes': [
            'Native PDF text extraction used; OCR fallback is not implemented.',
            'Section-number hierarchy is used; missing intermediate headings are reported as warnings.',
            'Tables are currently retained as text lines/paragraphs, not guaranteed to be reconstructed as cell grids.',
            'Repeated heading titles remain distinct when their section numbers differ.',
        ],
    }
