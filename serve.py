#!/usr/bin/env python3
"""Serve public/ and the feedback board on 127.0.0.1:8791."""

import json
import os
import secrets
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent / "public"
DATA = ROOT / "data" / "feedback.json"
JS = ROOT / "data" / "feedback.js"
LOCK = threading.Lock()
MAX_NOTES = 2000
MAX_TEXT = 2000
MAX_NAME = 40
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def clean(value, limit, keep_lines):
    if not isinstance(value, str):
        value = ""
    chars = []
    for ch in value.replace("\r\n", "\n").replace("\r", "\n"):
        if ch == "\n":
            chars.append("\n" if keep_lines else " ")
            continue
        if ch == "\t":
            chars.append(" ")
            continue
        if ord(ch) < 32 or ord(ch) == 127:
            continue
        chars.append(ch)
    text = "".join(chars)
    text = text.strip() if keep_lines else " ".join(text.split())
    if len(text) > limit:
        return None
    return text


def load_notes():
    if not DATA.exists():
        return []
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, list):
        return None
    return data


def save_notes(notes):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(notes, ensure_ascii=False, indent=2) + "\n"
    tmp = DATA.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, DATA)
    js = "window.ZHISHI_FEEDBACK = " + json.dumps(notes, ensure_ascii=False, indent=2) + ";\n"
    tmp_js = JS.with_suffix(".js.tmp")
    tmp_js.write_text(js, encoding="utf-8")
    os.replace(tmp_js, JS)


def client_ip(handler):
    raw = ""
    if handler.client_address:
        raw = handler.client_address[0] or ""
    if raw.startswith("::ffff:"):
        raw = raw[7:]
    raw = raw.strip()
    if len(raw) > 64:
        raw = raw[:64]
    return raw


def static_file(url_path):
    raw = unquote(urlparse(url_path).path)
    if raw in ("", "/"):
        raw = "/index.html"
    rel = raw.lstrip("/")
    if not rel or rel.startswith(("/", "\\")) or "\\" in rel:
        return None
    candidate = (ROOT / rel).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    if any(part.startswith(".") for part in candidate.relative_to(ROOT).parts):
        return None
    if candidate.is_file():
        return candidate
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "Zhishi/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def end_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/feedback":
            with LOCK:
                notes = load_notes()
            if notes is None:
                self.end_json(500, {"error": "白板读不出来。"})
                return
            self.end_json(200, {"notes": notes, "ip": client_ip(self)})
            return
        file_path = static_file(self.path)
        if file_path is None:
            body = "没有这个文件。".encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(file_path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/api/feedback":
            self.end_json(404, {"error": "没有这个地址。"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 8192:
            self.end_json(400, {"error": "内容没送成。"})
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.end_json(400, {"error": "内容没送成。"})
            return
        if not isinstance(payload, dict):
            self.end_json(400, {"error": "内容没送成。"})
            return
        name = clean(payload.get("name", ""), MAX_NAME, False)
        text = clean(payload.get("text", ""), MAX_TEXT, True)
        if name is None:
            self.end_json(400, {"error": "称呼太长。"})
            return
        if text is None:
            self.end_json(400, {"error": "内容太长。"})
            return
        if not text:
            self.end_json(400, {"error": "写点内容再送。"})
            return
        note = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3),
            "name": name,
            "text": text,
            "ip": client_ip(self),
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        with LOCK:
            notes = load_notes()
            if notes is None:
                self.end_json(500, {"error": "白板读不出来。"})
                return
            notes.append(note)
            if len(notes) > MAX_NOTES:
                notes = notes[-MAX_NOTES:]
            try:
                save_notes(notes)
            except OSError:
                self.end_json(500, {"error": "白板没有写成。"})
                return
        self.end_json(200, {"notes": notes, "ip": client_ip(self)})


def main():
    host = "127.0.0.1"
    port = 8791
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
            continue
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
            continue
        sys.exit("用法：python3 serve.py [--host 127.0.0.1] [--port 8791]")
    if port == 8765:
        sys.exit("请换一个端口。")
    if not DATA.exists():
        save_notes([])
    httpd = ThreadingHTTPServer((host, port), Handler)
    print("书籍导航 http://%s:%s/" % (host, port), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
