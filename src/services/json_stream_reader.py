"""Duyệt từng bản ghi JSON mà không nạp toàn bộ file vào RAM.

KỸ THUẬT: streaming parser theo chunk cho JSON Array và JSON Lines.
VẤN ĐỀ: file Wazuh có thể hàng trăm MB, đọc toàn bộ dễ treo giao diện/hết RAM.
TÁC DỤNG: mỗi lần chỉ giữ một phần nhỏ và yield từng record cho bước sau.
"""

import json
from pathlib import Path


class JsonStreamReader:
    """Hỗ trợ JSON Array lớn và JSON Lines theo cách streaming."""

    DEFAULT_CHUNK_SIZE = 1024 * 1024
    MAX_RECORD_CHARS = 16 * 1024 * 1024

    @classmethod
    def iter_records(cls, file_path, chunk_size=DEFAULT_CHUNK_SIZE):
        """Nhận diện định dạng rồi yield từng dictionary theo cách streaming."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {path}")
        if chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0.")

        with path.open("r", encoding="utf-8-sig") as handle:
            first_chunk = handle.read(chunk_size)
            if not first_chunk.strip():
                raise ValueError("File dữ liệu đang rỗng.")

            first_position = cls._first_content_position(first_chunk)
            first_character = first_chunk[first_position]

            if first_character == "[":
                yield from cls._iter_json_array(
                    handle,
                    first_chunk,
                    first_position + 1,
                    chunk_size,
                )
                return

            if first_character == "{":
                yield from cls._iter_json_lines(handle, first_chunk, chunk_size)
                return

            raise ValueError("Dữ liệu phải là JSON Array hoặc JSON Lines.")

    @staticmethod
    def detect_format(file_path):
        """Trả về json_array hoặc json_lines từ ký tự đầu tiên."""
        path = Path(file_path)
        with path.open("r", encoding="utf-8-sig") as handle:
            while True:
                character = handle.read(1)
                if character == "":
                    raise ValueError("File dữ liệu đang rỗng.")
                if character.isspace():
                    continue
                if character == "[":
                    return "json_array"
                if character == "{":
                    return "json_lines"
                raise ValueError("Không nhận diện được định dạng JSON.")

    @staticmethod
    def _first_content_position(text):
        """Tìm vị trí ký tự không phải khoảng trắng đầu tiên trong chunk."""
        for position, character in enumerate(text):
            if not character.isspace():
                return position
        raise ValueError("File dữ liệu đang rỗng.")

    @classmethod
    def _iter_json_array(cls, handle, buffer, position, chunk_size):
        """Giải mã nối tiếp từng object trong một JSON Array lớn."""
        decoder = json.JSONDecoder()
        reached_end = False
        record_number = 0

        while True:
            while True:
                while position < len(buffer) and (
                    buffer[position].isspace() or buffer[position] == ","
                ):
                    position += 1

                if position < len(buffer):
                    break

                if reached_end:
                    raise ValueError("JSON Array thiếu ký tự kết thúc ].")

                buffer = handle.read(chunk_size)
                position = 0
                reached_end = buffer == ""

            if buffer[position] == "]":
                return

            while True:
                try:
                    record, end_position = decoder.raw_decode(buffer, position)
                    break
                except json.JSONDecodeError as error:
                    if reached_end:
                        raise ValueError(
                            f"JSON không hợp lệ gần bản ghi {record_number + 1}."
                        ) from error

                    remaining = buffer[position:]
                    if len(remaining) > cls.MAX_RECORD_CHARS:
                        raise ValueError(
                            f"Bản ghi {record_number + 1} vượt quá giới hạn cho phép."
                        ) from error

                    next_chunk = handle.read(chunk_size)
                    reached_end = next_chunk == ""
                    buffer = remaining + next_chunk
                    position = 0

            record_number += 1
            if not isinstance(record, dict):
                raise ValueError(f"Bản ghi {record_number} không phải JSON object.")

            yield record
            position = end_position

            if position >= chunk_size:
                buffer = buffer[position:]
                position = 0

    @staticmethod
    def _iter_json_lines(handle, first_chunk, chunk_size):
        """Đọc và giải mã từng dòng độc lập của định dạng JSON Lines."""
        pending = first_chunk
        line_number = 0

        while True:
            next_chunk = handle.read(chunk_size)
            reached_end = next_chunk == ""
            pending += next_chunk
            lines = pending.splitlines(keepends=True)

            if not reached_end and lines and not lines[-1].endswith(("\n", "\r")):
                pending = lines.pop()
            else:
                pending = ""

            for line in lines:
                line_number += 1
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"JSON Lines không hợp lệ tại dòng {line_number}."
                    ) from error
                if not isinstance(record, dict):
                    raise ValueError(f"Dòng {line_number} không phải JSON object.")
                yield record

            if reached_end:
                return
