import csv
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from csv_cleaner import analyze, csv_bytes, render_html, run


class CleanerTests(unittest.TestCase):
    def test_no_options_preserves_every_cell(self):
        rows = [['id','名字','note','blank'], ['0007',' 小王 ','a,b\r\nc"d',''], ['0007',' 小王 ','a,b\r\nc"d','']]
        report, output, removed = analyze(csv_bytes(rows))
        self.assertEqual(output, rows)
        self.assertEqual(removed, [rows[0]])
        self.assertEqual(report['input_data_rows'], report['output_data_rows'])

    def test_opt_in_trim_and_exact_dedupe(self):
        rows = [[' id ','名字'], ['001',' 张三 '], ['001','张三'], ['002','李四']]
        report, output, removed = analyze(csv_bytes(rows), True, True)
        self.assertEqual(output, [[' id ','名字'], ['001','张三'], ['002','李四']])
        self.assertEqual(removed, [rows[0], rows[2]])
        self.assertEqual(report['removed_records'][0]['record'], 3)
        self.assertEqual(report['changed_cells'][0]['before'], ' 张三 ')

    def test_data_conservation_and_idempotence_randomized(self):
        rng = random.Random(921)
        values = ['', '00123', '你好', ' x ', 'a,b', 'a\nb', '"quote"', '=1+1', 'é', '\ttext', '😀']
        for trim in [False, True]:
            for dedupe in [False, True]:
                rows = [['id', 'value']] + [[rng.choice(values), rng.choice(values)] for _ in range(300)]
                report, output, removed = analyze(csv_bytes(rows), trim, dedupe)
                self.assertEqual(report['status'], 'ok')
                self.assertEqual(len(rows)-1, len(output)-1 + len(removed)-1)
                recovered = dict(zip(report['output_source_records'], output[1:]))
                for change in report['changed_cells']:
                    recovered[change['record']] = list(recovered[change['record']])
                    recovered[change['record']][change['column']-1] = change['before']
                recovered.update({r['record']: r['cells'] for r in report['removed_records']})
                self.assertEqual([recovered[i] for i in range(2, len(rows)+1)], rows[1:])
                again, output2, removed2 = analyze(csv_bytes(output), trim, dedupe)
                self.assertEqual(output2, output)
                self.assertEqual(again['changed_cells'], [])
                self.assertEqual(again['removed_data_rows'], 0)

    def test_headers_and_formula_hazards_preserved(self):
        rows = [['','x','x'], ['001',' =SUM(A1:A2)','@foo'], ['002','-2','\ttext']]
        report, output, _ = analyze(csv_bytes(rows))
        self.assertEqual(output, rows)
        self.assertEqual(report['blank_header_columns'], [1])
        self.assertEqual(report['duplicate_headers'], [{'value':'x', 'columns':[2,3]}])
        self.assertEqual(len(report['formula_hazards']), 4)

    def test_html_escapes_untrusted_values(self):
        report, _, _ = analyze(csv_bytes([['x'], ['=<script>alert("x")</script>']]))
        output = render_html(report)
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertIn("default-src 'none'", output)

    def test_bad_width_rejected_including_blank_record(self):
        for raw in [b'a,b\n1,2,3\n', b'a,b\n1\n', b'a,b\n\n']:
            report, output, removed = analyze(raw)
            self.assertEqual(report['status'], 'rejected')
            self.assertIsNone(output)
            self.assertIsNone(removed)
            self.assertTrue(report['row_width_errors'])

    def test_parse_and_encoding_errors(self):
        for raw in [b'', b'\n', b'x\n"unclosed', b'x\na"b\n', b'x\n"a"z\n', b'x\n\xff', b'x\na\x00b']:
            report, output, _ = analyze(raw)
            self.assertEqual(report['status'], 'rejected', raw)
            self.assertIsNone(output)
            self.assertTrue(report['errors'])

    def test_bom_and_header_only(self):
        report, rows, removed = analyze(b'\xef\xbb\xbfabc,def\r\n')
        self.assertEqual(report['status'], 'ok')
        self.assertEqual(rows, [['abc','def']])
        self.assertEqual(removed, rows)

    def test_input_preserved_outputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.csv'
            original = b'id,name\n0001, x \n0001, x \n'
            source.write_bytes(original)
            report = run(source, root/'out', True, True)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(set(p.name for p in (root/'out').iterdir()), {'cleaned.csv','removed_rows.csv','audit.html','audit.json'})
            self.assertEqual(json.loads((root/'out/audit.json').read_text()), report)
            with self.assertRaises(FileExistsError):
                run(source, root/'out')
            with self.assertRaises(FileExistsError):
                run(source, source)
            self.assertEqual(source.read_bytes(), original)

    def test_rejected_run_writes_only_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.csv'
            source.write_text('a,b\n1,2,3\n')
            report = run(source, root/'out')
            self.assertEqual(report['status'], 'rejected')
            self.assertEqual(set(p.name for p in (root/'out').iterdir()), {'audit.html','audit.json'})

    def test_cli_success_failure_and_limits(self):
        script = str(Path(__file__).resolve().parents[1]/'csv_cleaner.py')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.csv'
            source.write_text('id,name\n0001, 张三 \n', encoding='utf-8')
            args = [sys.executable, script, str(source), str(root/'out'), '--trim']
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
            source.write_text('a,b\n1\n')
            args[3] = str(root/'bad')
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
        report, _, _ = analyze(b'x' * (10*1024*1024+1))
        self.assertEqual(report['status'], 'rejected')


if __name__ == '__main__':
    unittest.main()
