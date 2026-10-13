"""Kiểm thử bộ đọc JSON streaming."""

import json
import tempfile
import unittest
from pathlib import Path

from src.services.json_stream_reader import JsonStreamReader


class JsonStreamReaderTests(unittest.TestCase):
    def test_read_json_array_across_small_chunks(self):
        records = [
            {"id": "1", "message": "Cảnh báo một"},
            {"id": "2", "message": "Cảnh báo hai"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.json"
            path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

            actual = list(JsonStreamReader.iter_records(path, chunk_size=7))

        self.assertEqual(records, actual)

    def test_read_json_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.json"
            path.write_text('{"id": "1"}\n{"id": "2"}\n', encoding="utf-8")

            actual = list(JsonStreamReader.iter_records(path, chunk_size=5))

        self.assertEqual([{"id": "1"}, {"id": "2"}], actual)

    def test_reject_non_object_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.json"
            path.write_text('[{"id": "1"}, 2]', encoding="utf-8")

            with self.assertRaises(ValueError):
                list(JsonStreamReader.iter_records(path, chunk_size=5))


if __name__ == "__main__":
    unittest.main()
