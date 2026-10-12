"""Nhận raw event từ Wazuh và chuyển vào hàng đợi xử lý của project."""

import json
import queue
import threading
from configparser import ConfigParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("project_config.conf")


def load_receiver_config():
    """Đọc cấu hình receiver riêng trong thư mục integration."""
    parser = ConfigParser()
    if not CONFIG_PATH.exists():
        return {"enabled": False}

    parser.read(CONFIG_PATH, encoding="utf-8")
    section = "wazuh_receiver"
    if not parser.has_section(section):
        return {"enabled": False}

    return {
        "enabled": parser.getboolean(section, "enabled", fallback=False),
        "host": parser.get(section, "host", fallback="0.0.0.0"),
        "port": parser.getint(section, "port", fallback=8765),
        "api_key": parser.get(section, "api_key", fallback=""),
        "max_body_bytes": parser.getint(
            section, "max_body_bytes", fallback=1_000_000
        ),
    }


class WazuhReceiver:
    """HTTP receiver chạy nền, không làm treo giao diện Tkinter."""

    def __init__(self, config=None):
        if config is None:
            config = load_receiver_config()
        self.enabled = bool(config.get("enabled", False))
        self.host = str(config.get("host", "127.0.0.1"))
        self.port = int(config.get("port", 8765))
        self.api_key = str(config.get("api_key", ""))
        self.max_body_bytes = int(config.get("max_body_bytes", 1_000_000))
        self._alerts = queue.Queue()
        self._server = None
        self._thread = None

    def start(self):
        """Mở cổng nhận log. Trả về True nếu receiver được khởi động."""
        if not self.enabled or self._server is not None:
            return False

        receiver = self

        class AlertHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != "/alerts":
                    self._reply(404, {"error": "Not found"})
                    return

                provided_key = self.headers.get("X-API-Key", "")
                if receiver.api_key and provided_key != receiver.api_key:
                    self._reply(401, {"error": "Invalid API key"})
                    return

                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                    if content_length <= 0 or content_length > receiver.max_body_bytes:
                        raise ValueError("Kích thước dữ liệu không hợp lệ.")

                    raw_body = self.rfile.read(content_length)
                    alert_data = json.loads(raw_body.decode("utf-8"))
                    if not isinstance(alert_data, dict):
                        raise ValueError("Event phải là một JSON object.")

                    receiver._alerts.put(alert_data)
                    self._reply(202, {"status": "accepted"})
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                    self._reply(400, {"error": str(error)})

            def log_message(self, _format, *_args):
                return

            def _reply(self, status_code, data):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer((self.host, self.port), AlertHandler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="wazuh-receiver",
            daemon=True,
        )
        self._thread.start()
        return True

    @property
    def is_running(self):
        """Cho biết receiver có đang mở cổng nhận log hay không."""
        return self._server is not None

    def get_pending(self):
        """Trả về các raw event đang chờ để MainWindow xử lý."""
        alerts = []
        while True:
            try:
                alerts.append(self._alerts.get_nowait())
            except queue.Empty:
                return alerts

    def stop(self):
        """Đóng receiver khi người dùng tắt ứng dụng."""
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
