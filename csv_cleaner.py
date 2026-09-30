#!/usr/bin/env python3
"""Conservative, offline CSV cleanup sample. Python 3.10+ standard library."""
import argparse
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import sys

VERSION = '1.0.0'
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000


def lexical_check(text):
    """Reject ambiguous quotes Python's permissive unquoted-field parser accepts."""
    state = 'start'
    for pos, char in enumerate(text):
        if char == '\x00':
            raise ValueError(f'NUL character at character offset {pos}')
        if state == 'quoted':
            if char == '"':
                state = 'closed'
        elif state == 'closed':
            if char == '"':
                state = 'quoted'
            elif char == ',':
                state = 'start'
            elif char in '\r\n':
                state = 'start'
            else:
                raise ValueError(f'Unexpected character after closing quote at offset {pos}')
        elif char == '"':
            if state != 'start':
                raise ValueError(f'Quote inside unquoted field at character offset {pos}')
            state = 'quoted'
        elif char == ',' or char in '\r\n':
            state = 'start'
        else:
            state = 'unquoted'
    if state == 'quoted':
        raise ValueError('Unterminated quoted field')


def inspect_headers(headers):
    positions = {}
    for index, value in enumerate(headers, 1):
        positions.setdefault(value, []).append(index)
    return {
        'blank_header_columns': [i for i, v in enumerate(headers, 1) if not v.strip()],
        'duplicate_headers': [{'value': v, 'columns': cols} for v, cols in positions.items() if len(cols) > 1],
    }


def hazards(rows):
    found = []
    for record, row in enumerate(rows, 1):
        for col, value in enumerate(row, 1):
            candidate = value.lstrip()
            if (candidate and candidate[0] in '=+-@') or value.startswith(('\t', '\r', '\n')):
                found.append({'record': record, 'column': col, 'value': value,
                              'reason': 'Potential spreadsheet formula/control-prefix hazard; not sanitized'})
    return found


def analyze(raw, trim=False, deduplicate=False):
    report = {
        'tool_version': VERSION, 'status': 'rejected',
        'input_sha256': hashlib.sha256(raw).hexdigest(), 'input_bytes': len(raw),
        'options': {'trim_data_cells': trim, 'remove_exact_processed_duplicates': deduplicate},
        'errors': [], 'warnings': [],
        'record_numbering': '1-based logical CSV records, including header; not physical lines',
        'deduplication_basis': 'Exact data-cell strings AFTER optional trim; first occurrence kept',
    }
    if len(raw) > MAX_BYTES:
        report['errors'].append('Input exceeds 10 MiB limit')
        return report, None, None
    try:
        text = raw.decode('utf-8-sig', errors='strict')
        lexical_check(text)
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) > MAX_ROWS + 1:
                raise ValueError('Input exceeds 100,000 data-record limit')
    except (UnicodeError, csv.Error, ValueError) as exc:
        report['errors'].append(str(exc))
        return report, None, None
    if not rows or not rows[0]:
        report['errors'].append('Missing nonempty header record')
        return report, None, None
    header, data = rows[0], rows[1:]
    report.update(inspect_headers(header))
    report['input_data_rows'] = len(data)
    report['columns'] = len(header)
    report['formula_hazards'] = hazards(rows)
    report['row_width_errors'] = [
        {'record': i, 'expected': len(header), 'actual': len(row)}
        for i, row in enumerate(data, 2) if len(row) != len(header)
    ]
    if report['blank_header_columns'] or report['duplicate_headers']:
        report['warnings'].append('Headers contain blank or duplicate names; preserved unchanged')
    if report['formula_hazards']:
        report['warnings'].append('Formula-like text is preserved. Do not open CSV directly in a spreadsheet; import all columns as text. Detection is heuristic, not a security guarantee.')
    if report['row_width_errors']:
        report['errors'].append('Inconsistent record widths; no cleaned CSV written')
        return report, None, None
    kept, removed, changes, seen, kept_records = [], [], [], {}, []
    duplicates = []
    for record, original in enumerate(data, 2):
        new = [value.strip() for value in original] if trim else list(original)
        key = tuple(new)
        if key in seen:
            duplicates.append({'record': record, 'first_record': seen[key]})
            if deduplicate:
                removed.append({'record': record, 'first_record': seen[key], 'cells': original})
                continue
        else:
            seen[key] = record
        for col, (before, after) in enumerate(zip(original, new), 1):
            if before != after:
                changes.append({'record': record, 'column': col, 'before': before, 'after': after})
        kept.append(new)
        kept_records.append(record)
    report.update(status='ok', output_data_rows=len(kept), removed_data_rows=len(removed),
                  duplicate_data_rows=duplicates, changed_cells=changes,
                  output_source_records=kept_records, removed_records=removed,
                  output_formula_hazards=hazards([header] + kept))
    report['output_duplicate_count'] = len(kept) - len(set(map(tuple, kept)))
    if report['output_duplicate_count']:
        report['warnings'].append('Output contains exact duplicates. No additional removal was authorized.')
    return report, [header] + kept, [header] + [r['cells'] for r in removed]


def csv_bytes(rows):
    stream = io.StringIO(newline='')
    csv.writer(stream, lineterminator='\r\n').writerows(rows)
    return stream.getvalue().encode('utf-8')


def render_html(report):
    payload = html.escape(json.dumps(report, ensure_ascii=False, indent=2), quote=True)
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CSV cleanup audit / CSV 清理审计</title>
<style>body{font:16px system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 24px;color:#182b39}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f7;padding:24px}h1{color:#164e63}</style>
<h1>CSV cleanup audit / CSV 清理审计</h1>
<p>Local synthetic service sample. Audit values may include private data. Keep reports private.</p>
<p>仅为本地服务样例。审计报告可能包含原始数据，请妥善保管。疑似公式不会被自动修改。</p>
<pre>''' + payload + '</pre></html>\n'


def run(input_path, output_dir, trim=False, deduplicate=False):
    source = Path(input_path)
    target = Path(output_dir)
    # Exclusive directory creation also blocks existing files, symlinks and overwrite attempts.
    if target.exists() or target.is_symlink():
        raise FileExistsError(f'Output path already exists: {target}')
    with source.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Input exceeds 10 MiB limit; no outputs written')
    report, cleaned, removed = analyze(raw, trim, deduplicate)
    outputs = {}
    if cleaned is not None:
        outputs['cleaned.csv'] = csv_bytes(cleaned)
        outputs['removed_rows.csv'] = csv_bytes(removed)
        report['output_sha256'] = hashlib.sha256(outputs['cleaned.csv']).hexdigest()
    outputs['audit.json'] = (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    outputs['audit.html'] = render_html(report).encode('utf-8')
    target.mkdir(parents=False, exist_ok=False)
    written = []
    try:
        for name, content in outputs.items():
            path = target / name
            with path.open('xb') as handle:
                written.append(path)
                handle.write(content)
    except BaseException:
        for path in written:
            path.unlink(missing_ok=True)
        try:
            target.rmdir()
        except OSError:
            pass
        raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='UTF-8 comma-delimited CSV with a header')
    parser.add_argument('output_dir', help='NEW directory; parent must exist; never overwritten')
    parser.add_argument('--trim', action='store_true', help='Strip Unicode edge whitespace from data cells only (can change meaningful whitespace)')
    parser.add_argument('--deduplicate', action='store_true', help='Remove exact duplicate rows AFTER optional trim, keeping first')
    args = parser.parse_args(argv)
    try:
        report = run(args.input, args.output_dir, args.trim, args.deduplicate)
    except (OSError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    print(f"{report['status']}: {args.output_dir}/audit.html")
    return 0 if report['status'] == 'ok' else 2


if __name__ == '__main__':
    sys.exit(main())
