import io
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from neops_remote_lab import server
from neops_remote_lab.models import DeviceInfoDto
from neops_remote_lab.netlab.lab_manager import LabManager

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures & stubs
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_server_state() -> Generator[None, None, None]:
    """Ensure clean session/queue state before and after every test."""
    server._SESSION_QUEUE.clear()
    server._SESSIONS.clear()
    yield
    server._SESSION_QUEUE.clear()
    server._SESSIONS.clear()


@pytest.fixture(autouse=True)
def _patch_lab_manager(monkeypatch: pytest.MonkeyPatch) -> type["LabManager"]:
    """Lightweight subclass of the real LabManager so interface changes break tests."""

    class _StubLabManager(LabManager):
        """In-memory implementation that overrides _start/_terminate_current only."""

        _DUMMY_DEVICES: ClassVar[list[DeviceInfoDto]] = [
            type(
                "DummyDevice",
                (),
                {
                    "name": "r1",
                    "raw": {
                        "mgmt": {"ipv4": "192.0.2.1"},
                        "ansible_user": "tester",
                        "ansible_ssh_pass": "test",
                        "ansible_network_os": "ios",
                    },
                },
            )(),
            type(
                "DummyDevice",
                (),
                {
                    "name": "r2",
                    "ip": "192.0.2.2",
                    "username": "tester",
                    "device_type": "ios",
                    "raw": {
                        "mgmt": {"ipv4": "192.0.2.2"},
                        "ansible_user": "tester",
                        "ansible_ssh_pass": "test",
                        "ansible_network_os": "ios",
                    },
                },
            )(),
        ]

        # Override heavy operations --------------------------------------------------
        @classmethod
        def _start(cls, topo: Path) -> list[DeviceInfoDto]:  # type: ignore[override]
            # Simulate an instant startup with dummy devices
            cls._current_topo = topo.resolve() if topo else Path("dummy.yml")
            workdir = Path(tempfile.mkdtemp(prefix="neops_lab_stub_"))
            cls._handle = cls._Handle(workdir, list(cls._DUMMY_DEVICES))
            return cls._handle.devices

        @classmethod
        def _terminate_current(cls, reason: str | None = None) -> None:  # type: ignore[override]
            cls._handle = None
            cls._current_topo = None
            if reason:
                server._log.debug("Stub lab terminated (reason=%s)", reason)

    # Patch the real LabManager symbol in server.py with our subclass
    monkeypatch.setattr(server, "LabManager", _StubLabManager)
    return _StubLabManager


@pytest.fixture
def client() -> TestClient:
    return TestClient(server.app)


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────


def _create_session(client: TestClient) -> str:
    """Utility that creates a new session and returns the ID."""
    resp = client.post("/session")
    assert resp.status_code == 201
    return resp.json()["session_id"]


def _get_status(client: TestClient, sid: str) -> dict[str, Any]:
    return client.get(f"/session/{sid}").json()


# ──────────────────────────────────────────────────────────────────────────────
# Tests - Session queueing & lifecycle
# ──────────────────────────────────────────────────────────────────────────────


def test_first_session_is_active(client: TestClient) -> None:
    sid = _create_session(client)
    stat = _get_status(client, sid)
    assert stat["status"].lower() == "active"
    assert stat["position"] == 0  # active session is position 0 in queue


def test_second_session_waits(client: TestClient) -> None:
    sid1 = _create_session(client)
    sid2 = _create_session(client)

    stat1 = _get_status(client, sid1)
    stat2 = _get_status(client, sid2)

    assert stat1["status"].lower() == "active"
    assert stat1["position"] == 0  # Active session is position 0
    assert stat2["status"].lower() == "waiting"
    assert stat2["position"] == 1


def test_end_of_active_session_promotes_next(client: TestClient) -> None:
    sid1 = _create_session(client)
    sid2 = _create_session(client)

    # End the ACTIVE session - should promote sid2
    resp = client.delete(f"/session/{sid1}")
    assert resp.status_code == 204

    stat2 = _get_status(client, sid2)
    assert stat2["status"].lower() == "active"
    assert stat2["position"] == 0  # Active session is now position 0


def test_heartbeat_updates_timestamp(client: TestClient) -> None:
    sid = _create_session(client)
    before = server._SESSIONS[sid].last_seen_at
    # heartbeat endpoint requires header
    resp = client.post("/session/heartbeat", headers={server.HEADER_SESSION_ID: sid})
    assert resp.status_code == 204
    after = server._SESSIONS[sid].last_seen_at
    assert after >= before


def test_invalid_session_returns_404(client: TestClient) -> None:
    resp = client.get("/session/not-a-real-id")
    assert resp.status_code == 404


# Active session endpoint
def test_get_active_session_when_exists(client: TestClient) -> None:
    sid = _create_session(client)
    resp = client.get("/active-session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert data["status"].lower() == "active"
    assert data["position"] == 0


def test_get_active_session_when_none_exists(client: TestClient) -> None:
    resp = client.get("/active-session")
    assert resp.status_code == 404


def test_get_active_session_with_queue(client: TestClient) -> None:
    sid1 = _create_session(client)
    _create_session(client)  # second session waiting
    resp = client.get("/active-session")
    data = resp.json()
    assert data["session_id"] == sid1
    assert data["position"] == 0


def test_get_active_session_after_promotion(client: TestClient) -> None:
    sid1 = _create_session(client)
    sid2 = _create_session(client)
    client.delete(f"/session/{sid1}")
    data = client.get("/active-session").json()
    assert data["session_id"] == sid2
    assert data["position"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Tests - Lab management endpoints (with stubbed LabManager)
# ──────────────────────────────────────────────────────────────────────────────


def _sample_topo_bytes() -> bytes:
    return b"---\nname: sample\nversion: 1\n"


def test_acquire_and_release_lab(client: TestClient) -> None:
    sid = _create_session(client)

    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reused"] is False
    assert body["devices"]  # list of one or more devices

    # Lab status should now report running
    resp = client.get("/lab", headers={server.HEADER_SESSION_ID: sid})
    assert resp.status_code == 200
    assert resp.json()["running"] is True

    # Release lab
    resp = client.post("/lab/release", headers={server.HEADER_SESSION_ID: sid})
    assert resp.status_code == 204


@pytest.mark.usefixtures("_patch_lab_manager")
def test_acquire_returns_423_when_busy(client: TestClient) -> None:
    # Session acquires lab with reuse=True
    sid = _create_session(client)
    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    assert resp.status_code == 200  # First acquire succeeds

    # Same session tries to acquire a DIFFERENT topology (should force teardown, but lab is busy)
    # Let's modify the stub to simulate this better
    if _patch_lab_manager._handle is not None:
        _patch_lab_manager._handle.ref = 2  # Make it look like multiple refs are holding the lab

    files = [
        (
            "topology",
            ("different-topo.yml", io.BytesIO(b"---\nname: different\nversion: 1\n"), "text/plain"),
        )
    ]
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "false"},
    )
    assert resp.status_code == 423


# ──────────────────────────────────────────────────────────────────────────────
# Additional test scenarios for thorough coverage
# ──────────────────────────────────────────────────────────────────────────────


def test_acquire_wrong_extension_returns_400(client: TestClient) -> None:
    sid = _create_session(client)
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=[
            (
                "topology",
                ("topology.txt", io.BytesIO(b"dummy"), "text/plain"),
            )
        ],
        data={"reuse": "true"},
    )
    assert resp.status_code == 400


def test_waiting_session_cannot_acquire_lab(client: TestClient) -> None:
    # Create ACTIVE + WAITING sessions
    _create_session(client)
    waiting_sid = _create_session(client)
    assert _get_status(client, waiting_sid)["status"].lower() == "waiting"

    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: waiting_sid},
        files=files,
        data={"reuse": "true"},
    )
    # WAITING sessions are rejected with 423 (lab locked)
    assert resp.status_code == 423


def test_destroy_lab_force_false_conflict(client: TestClient) -> None:
    sid = _create_session(client)
    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    # acquire
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    assert resp.status_code == 200

    # destroy with force=false while ref_count>0 -> 409
    resp = client.delete(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        params={"force": "false"},
    )
    assert resp.status_code == 409


def test_destroy_lab_force_true_success(client: TestClient) -> None:
    sid = _create_session(client)
    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    assert resp.status_code == 200

    resp = client.delete(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        params={"force": "true"},
    )
    assert resp.status_code == 202


def test_list_devices_returns_devices(client: TestClient) -> None:
    sid = _create_session(client)
    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        )
    ]
    client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    resp = client.get("/lab/devices", headers={server.HEADER_SESSION_ID: sid})
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)
    assert len(devices) >= 1
    # Check for new API format with name and raw fields
    device = devices[0]
    assert {"name", "raw"}.issubset(device.keys())
    # Verify raw contains the expected netlab inspect structure
    raw = device["raw"]
    assert "mgmt" in raw
    assert "ipv4" in raw["mgmt"]
    assert "ansible_user" in raw
    assert "ansible_network_os" in raw


def test_release_lab_without_running_returns_404(client: TestClient) -> None:
    sid = _create_session(client)
    resp = client.post("/lab/release", headers={server.HEADER_SESSION_ID: sid})
    assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# File structure preservation test
# ──────────────────────────────────────────────────────────────────────────────


def test_upload_preserves_folder_structure(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Uploading files with sub-directories should be saved with the same layout."""

    # Monkeypatch server._tmp_upload_dir to a deterministic path inside tmp_path
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()

    monkeypatch.setattr(server, "_tmp_upload_dir", lambda: upload_root)

    sid = _create_session(client)

    files = [
        (
            "topology",
            ("topology.yml", io.BytesIO(_sample_topo_bytes()), "text/plain"),
        ),
        (
            "extra_files",
            ("configs/init.cfg", io.BytesIO(b"dummy"), "text/plain"),
        ),
        (
            "extra_files",
            ("templates/template.j2", io.BytesIO(b"dummy"), "text/plain"),
        ),
    ]

    resp = client.post(
        "/lab",
        headers={server.HEADER_SESSION_ID: sid},
        files=files,
        data={"reuse": "true"},
    )
    assert resp.status_code in (200, 423, 409)  # Depending on stubbed LabManager state

    # Assert that the files exist with the correct nested structure
    assert (upload_root / "topology.yml").exists()
    assert (upload_root / "configs" / "init.cfg").exists()
    assert (upload_root / "templates" / "template.j2").exists()
