from __future__ import annotations

import json
import urllib.request
import uuid
from typing import Any


class LocalBridgeClient:
    """Transport client for a configured bridge endpoint.

    The endpoint must be explicitly supplied by the deployment (normally a
    secure connector/tunnel to the Windows agent). This client never chooses
    a local filesystem path on its own.
    """

    def __init__(self, endpoint: str, token: str, timeout: float = 30.0) -> None:
        if not endpoint.startswith("https://") and not endpoint.startswith("http://127.0.0.1") and not endpoint.startswith("http://localhost"):
            raise ValueError("bridge endpoint must use HTTPS or explicitly target localhost")
        self.endpoint = endpoint.rstrip("/") + "/v1/request"
        self.token = token
        self.timeout = timeout

    def request(self, method: str, *, session_id: str | None = None, **params: Any) -> dict[str, Any]:
        payload = {"id": str(uuid.uuid4()), "protocol": "1.0", "method": method, "token": self.token, **params}
        if session_id is not None:
            payload["session_id"] = session_id
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.endpoint, data=body, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict) or "ok" not in result or "id" not in result or "error" not in result:
            raise RuntimeError("invalid bridge response")
        return result

    def status(self) -> dict[str, Any]:
        return self.request("agent.status")

    def open_session(self, authorized_paths: list[str], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("session.open", authorized_paths=authorized_paths, metadata=metadata or {})
