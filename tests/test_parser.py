from pathlib import Path
from app.parser import parse_pdf

DATA = Path(__file__).resolve().parents[1] / 'data'


def all_nodes(nodes):
    out = []
    for n in nodes:
        out.append(n)
        out.extend(all_nodes(n.get('children', [])))
    return out


def test_both_pdfs_extract_numbered_sections():
    for filename in ('ct200_manual.pdf', 'ct200_manual_v2.pdf'):
        result = parse_pdf(DATA / filename)
        nodes = all_nodes(result['sections'])
        assert result['page_count'] >= 6
        assert any(n['number'] == '4.2' for n in nodes)
        assert any(n['number'] == '7.1' for n in nodes)
        assert all(n['heading'] and n['content_hash'] for n in nodes)


def test_duplicate_error_code_headings_are_distinct_nodes():
    result = parse_pdf(DATA / 'ct200_manual.pdf')
    nodes = all_nodes(result['sections'])
    error_code_nodes = [n for n in nodes if n['heading'].lower() == 'error codes']
    assert len(error_code_nodes) == 2
    assert {n['number'] for n in error_code_nodes} == {'4.2', '7.1'}


def test_missing_intermediate_heading_is_exposed():
    result = parse_pdf(DATA / 'ct200_manual.pdf')
    nodes = all_nodes(result['sections'])
    battery = next(n for n in nodes if n['number'] == '2.1.1.1')
    assert battery['warnings']
    assert any('2.1.1' in warning for warning in battery['warnings'])


def test_version_specific_threshold_text_is_extracted():
    v1 = all_nodes(parse_pdf(DATA / 'ct200_manual.pdf')['sections'])
    v2 = all_nodes(parse_pdf(DATA / 'ct200_manual_v2.pdf')['sections'])
    b1 = next(n for n in v1 if n['number'] == '2.1.1.1')
    b2 = next(n for n in v2 if n['number'] == '2.1.1.1')
    assert '300 measurement cycles' in b1['body']
    assert '250 measurement cycles' in b2['body']
    assert b1['content_hash'] != b2['content_hash']
