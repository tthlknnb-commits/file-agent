from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from document_writer import read_docx, validate_docx, write_docx
from file_reader import read_paths
from file_search import search_paths

PROTOCOL_VERSION = "1.0"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

ERROR_CODES = {
    "AUTHENTICATION_REQUIRED",
    "AUTHENTICATION_FAILED",
    "SESSION_REQUIRED",
    "SESSION_NOT_FOUND",
    "AUTHORIZATION_REQUIRED",
    "INVALID_REQUEST",
    "PATH_NOT_FOUND",
    "NOT_A_FILE",
    "NOT_A_DIRECTORY",
    "UNSUPPORTED_EXTENSION",
    "READ_DENIED",
    "WRITE_DENIED",
    "SOURCE_OVERWRITE_BLOCKED",
    "OUTPUT_EXISTS",
    "INVALID_OUTPUT_PATH",
    "METHOD_NOT_FOUND",
    "INTERNAL_ERROR",
}

SUPPORTED = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".docx", ".xlsx", ".pdf"}


@dataclass
class Session:
    session_id: str
    authorized_paths: tuple[Path, ...]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create(self, authorized_paths: list[str], metadata: dict[str, Any] | None = None) -> Session:
        roots = tuple(_resolve_path(p) for p in authorized_paths)
        session = Session(secrets.token_urlsafe(24), roots, _utc_now(), metadata or {})
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def revoke(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


class BridgeError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        if code not in ERROR_CODES:
            code = "INTERNAL_ERROR"
        self.code = code
        self.message = message
        self.details = details or {}


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise BridgeError("INVALID_REQUEST", "path must be a non-empty string")
    return Path(raw).expanduser().resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _authorized(session: Session, raw_path: str) -> Path:
    path = _resolve_path(raw_path)
    if not any(_is_within(path, root) for root in session.authorized_paths):
        raise BridgeError("AUTHORIZATION_REQUIRED", "path is outside the authorized session scope")
    return path


def _ensure_readable(path: Path) -> None:
    if not path.exists():
        raise BridgeError("PATH_NOT_FOUND", f"path does not exist: {path}")
    if not os.access(path, os.R_OK):
        raise BridgeError("READ_DENIED", f"path is not readable: {path}")


def _ensure_writable(path: Path) -> None:
    parent = path.parent
    if parent.exists() and not os.access(parent, os.W_OK):
        raise BridgeError("WRITE_DENIED", f"output directory is not writable: {parent}")
    if not parent.exists():
        raise BridgeError("WRITE_DENIED", f"output directory does not exist: {parent}")


def _reject_source_overwrite(path: Path, source: str | None, overwrite: bool) -> None:
    if source and path == _resolve_path(source):
        raise BridgeError("SOURCE_OVERWRITE_BLOCKED", "output path is the source path; source files are never overwritten")
    if path.exists() and not overwrite:
        raise BridgeError("OUTPUT_EXISTS", "output exists and overwrite=false")


def _file_row(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "kind": "directory" if path.is_dir() else "file",
        "extension": path.suffix.lower(),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
    }


def dispatch(request: dict[str, Any], *, token: str, sessions: SessionStore, debug: bool = False) -> dict[str, Any]:
    request_id = request.get("id")
    try:
        if not isinstance(request_id, str) or not request_id:
            raise BridgeError("INVALID_REQUEST", "id must be a non-empty string")
        if request.get("protocol") not in (None, PROTOCOL_VERSION):
            raise BridgeError("INVALID_REQUEST", f"unsupported protocol version: {request.get('protocol')}")
        method = request.get("method")
        if not isinstance(method, str):
            raise BridgeError("INVALID_REQUEST", "method is required")

        if method == "agent.status":
            if not secrets.compare_digest(str(request.get("token", "")), token):
                raise BridgeError("AUTHENTICATION_FAILED", "invalid agent token")
            return _ok(request_id, {"protocol": PROTOCOL_VERSION, "agent": "AI Admin Office Local Agent", "status": "ready", "capabilities": sorted(["agent.status", "session.open", "session.close", "file.list", "file.search", "file.metadata", "file.read", "file.write", "file.copy", "file.create_directory", "document.read", "document.write"])})

        if not secrets.compare_digest(str(request.get("token", "")), token):
            raise BridgeError("AUTHENTICATION_FAILED", "invalid agent token")

        if method == "session.open":
            paths = request.get("authorized_paths")
            if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
                raise BridgeError("INVALID_REQUEST", "authorized_paths must be a non-empty list of paths")
            session = sessions.create(paths, request.get("metadata") if isinstance(request.get("metadata"), dict) else None)
            return _ok(request_id, {"session_id": session.session_id, "authorized_paths": [str(p) for p in session.authorized_paths], "created_at": session.created_at})

        session_id = request.get("session_id")
        if not isinstance(session_id, str):
            raise BridgeError("SESSION_REQUIRED", "session_id is required")
        session = sessions.get(session_id)
        if session is None:
            raise BridgeError("SESSION_NOT_FOUND", "session does not exist or has been revoked")

        if method == "session.close":
            sessions.revoke(session_id)
            return _ok(request_id, {"closed": True})
        if method == "file.list":
            path = _authorized(session, request["path"])
            _ensure_readable(path)
            if not path.is_dir():
                raise BridgeError("NOT_A_DIRECTORY", "file.list requires a directory")
            recursive = bool(request.get("recursive", False))
            iterator = path.rglob("*") if recursive else path.iterdir()
            rows = [_file_row(p) for p in iterator if p.is_file() and p.suffix.lower() in SUPPORTED]
            return _ok(request_id, {"path": str(path), "files": rows})
        if method == "file.metadata":
            path = _authorized(session, request["path"])
            _ensure_readable(path)
            return _ok(request_id, _file_row(path))
        if method == "file.read":
            path = _authorized(session, request["path"])
            _ensure_readable(path)
            if path.is_dir():
                raise BridgeError("NOT_A_FILE", "file.read requires a file")
            evidence = read_paths([str(path)], recursive=False)
            if not evidence:
                raise BridgeError("UNSUPPORTED_EXTENSION", f"unsupported file type: {path.suffix}")
            return _ok(request_id, {"evidence": [e.__dict__ for e in evidence]})
        if method == "file.search":
            path = _authorized(session, request["path"])
            _ensure_readable(path)
            query = request.get("query")
            if not isinstance(query, str) or not query.strip():
                raise BridgeError("INVALID_REQUEST", "query is required")
            hits = search_paths([str(path)], query, recursive=bool(request.get("recursive", True)))
            return _ok(request_id, {"hits": [h.__dict__ for h in hits]})
        if method == "file.create_directory":
            path = _authorized(session, request["path"])
            if path.exists() and not path.is_dir():
                raise BridgeError("NOT_A_DIRECTORY", "target exists and is not a directory")
            path.mkdir(parents=True, exist_ok=True)
            return _ok(request_id, {"path": str(path), "created": True})
        if method == "file.copy":
            import shutil
            source = _authorized(session, request["source"])
            target = _authorized(session, request["target"])
            _ensure_readable(source)
            if target == source:
                raise BridgeError("SOURCE_OVERWRITE_BLOCKED", "source and target are identical")
            if target.exists() and not bool(request.get("overwrite", False)):
                raise BridgeError("OUTPUT_EXISTS", "target exists and overwrite=false")
            _ensure_writable(target)
            shutil.copy2(source, target)
            return _ok(request_id, {"source": str(source), "target": str(target)})
        if method in {"file.write", "document.write"}:
            target = _authorized(session, request["path"])
            source = request.get("source_path")
            _reject_source_overwrite(target, source, bool(request.get("overwrite", False)))
            if target.suffix.lower() not in SUPPORTED:
                raise BridgeError("UNSUPPORTED_EXTENSION", f"unsupported output type: {target.suffix}")
            _ensure_writable(target)
            if method == "document.write":
                payload = request.get("document")
                if not isinstance(payload, dict):
                    raise BridgeError("INVALID_REQUEST", "document.write requires a document object")
                write_docx(payload, target, overwrite=bool(request.get("overwrite", False)))
                validation = validate_docx(target)
                if not validation["valid"]:
                    raise BridgeError("INTERNAL_ERROR", "written DOCX failed validation", validation)
                return _ok(request_id, {"path": str(target), "validation": validation})
            data = request.get("content")
            if not isinstance(data, str):
                raise BridgeError("INVALID_REQUEST", "file.write requires string content")
            if target.exists() and not request.get("overwrite", False):
                raise BridgeError("OUTPUT_EXISTS", "output exists and overwrite=false")
            target.write_text(data, encoding=request.get("encoding", "utf-8"))
            return _ok(request_id, {"path": str(target), "size": target.stat().st_size})
        if method == "document.read":
            path = _authorized(session, request["path"])
            _ensure_readable(path)
            if path.suffix.lower() != ".docx":
                raise BridgeError("UNSUPPORTED_EXTENSION", "document.read currently requires .docx")
            return _ok(request_id, read_docx(path))
        raise BridgeError("METHOD_NOT_FOUND", f"unsupported method: {method}")
    except BridgeError as exc:
        error = {"code": exc.code, "message": exc.message}
        if exc.details:
            error["details"] = exc.details
        return {"id": request_id, "ok": False, "data": None, "error": error}
    except Exception as exc:
        error = {"code": "INTERNAL_ERROR", "message": "internal bridge error"}
        if debug:
            error["debug"] = repr(exc)
        return {"id": request_id, "ok": False, "data": None, "error": error}


def _ok(request_id: str, data: Any) -> dict[str, Any]:
    return {"id": request_id, "ok": True, "data": data, "error": None}


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "AIAdminOfficeLocalBridge/1.0"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/request":
            self._send(404, {"id": None, "ok": False, "data": None, "error": {"code": "METHOD_NOT_FOUND", "message": "endpoint not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            request = json.loads(raw.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            token = self.server.bridge_token  # type: ignore[attr-defined]
            response = dispatch(request, token=token, sessions=self.server.sessions, debug=self.server.debug)  # type: ignore[attr-defined]
            self._send(200, response)
        except Exception:
            self._send(400, {"id": None, "ok": False, "data": None, "error": {"code": "INVALID_REQUEST", "message": "invalid JSON request"}})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str, port: int, token: str, debug: bool = False) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), BridgeHandler)
    server.bridge_token = token  # type: ignore[attr-defined]
    server.sessions = SessionStore()  # type: ignore[attr-defined]
    server.debug = debug  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Admin Office Windows Cloud↔Local File Bridge")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address; default is localhost only")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=os.environ.get("AI_ADMIN_BRIDGE_TOKEN"), help="Bearer-equivalent bridge token")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    token = args.token or base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    print(json.dumps({"event": "bridge_ready", "host": args.host, "port": args.port, "protocol": PROTOCOL_VERSION, "token": token}, ensure_ascii=False), flush=True)
    server = create_server(args.host, args.port, token, args.debug)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
