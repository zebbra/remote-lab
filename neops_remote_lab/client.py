from __future__ import annotations

import logging
import os
import pathlib
import time
from typing import Any

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import DeviceInfoDto, SessionState

_log = logging.getLogger(__name__)


class RemoteLabClient:
    """A session-aware client for the remote lab manager."""

    def __init__(
        self,
        base_url: str,
        request_timeout: int = 30,  # Short timeout for quick operations
        session_timeout: int = 600,  # Session queue timeout
        lab_acquisition_timeout: int = 600,  # Long timeout for lab setup (10 minutes)
    ):
        self.base_url = base_url or os.getenv("REMOTE_LAB_URL")
        if not self.base_url:
            raise ValueError("base_url must be provided either as parameter or REMOTE_LAB_URL environment variable")
        self.request_timeout = request_timeout
        self.session_timeout = session_timeout
        self.lab_acquisition_timeout = lab_acquisition_timeout

        _log.info("RemoteLabClient initializing with base_url=%s", self.base_url)
        _log.info(
            "Timeouts: request=%ds, session=%ds, lab_acquisition=%ds",
            request_timeout,
            session_timeout,
            lab_acquisition_timeout,
        )

        self._session = self._create_http_session()
        # if token or os.getenv("REMOTE_LAB_TOKEN"):
        #     self._session.headers["Authorization"] = f"Bearer {token or os.getenv('REMOTE_LAB_TOKEN')}"

        self.session_id = self._create_session()
        self._session.headers["X-Session-ID"] = self.session_id

        self._wait_for_active_session(session_timeout)
        _log.info("Client successfully initialized with session %s.", self.session_id[:8])

    def _create_http_session(self) -> requests.Session:
        """Create and configure a requests.Session object."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "RemoteLabClient/1.0",
                "Connection": "keep-alive",
            }
        )

        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "OPTIONS", "DELETE"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=5,
            pool_maxsize=10,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _url(self, path: str) -> str:
        if not self.base_url:
            raise ValueError("base_url cannot be None")
        return f"{self.base_url.rstrip('/')}{path}"

    def _make_request(self, method: str, url: str, **kwargs: Any) -> Response:
        """Make an HTTP request and handle exceptions."""
        _log.debug("=> %s %s", method, url)
        try:
            response = self._session.request(method, url, **kwargs)
            _log.debug("<= %s %s - %d", method, url, response.status_code)
            return response
        except requests.exceptions.RequestException as e:
            _log.error("Request failed: %s %s: %s", method, url, e)
            raise

    def _create_session(self) -> str:
        _log.info("Creating new session...")
        resp = self._make_request("POST", self._url("/session"), timeout=self.request_timeout)
        resp.raise_for_status()
        data = resp.json()
        session_id = data["session_id"]
        position = data["position"]
        _log.info("Created session %s at queue position %d", session_id[:8], position)
        return session_id

    def _wait_for_active_session(self, timeout: int) -> None:
        _log.info("Waiting for session %s to become active (timeout=%ds)...", self.session_id[:8], timeout)
        start_time = time.monotonic()
        retries = 0
        max_retries = 10

        while time.monotonic() - start_time < timeout:
            elapsed = time.monotonic() - start_time
            try:
                resp = self._make_request("GET", self._url(f"/session/{self.session_id}"), timeout=self.request_timeout)
                resp.raise_for_status()
                data = resp.json()
                if data["status"] == SessionState.ACTIVE.value:
                    _log.info("Session %s is active after %.1fs.", self.session_id[:8], elapsed)
                    return

                retries = 0  # Reset retries on success
                position = data.get("position", -1)
                _log.info(
                    "Session %s is in queue at position %d (elapsed=%.1fs).", self.session_id[:8], position, elapsed
                )
                time.sleep(5)

            except requests.exceptions.RequestException as e:
                elapsed = time.monotonic() - start_time
                is_http_error = isinstance(e, requests.exceptions.HTTPError)
                if is_http_error and e.response and e.response.status_code < 500:
                    _log.error("Received non-retriable HTTP error after %.1fs: %s", elapsed, e)
                    raise

                retries += 1
                if retries > max_retries:
                    _log.error("Exceeded max retries (%d) waiting for session after %.1fs.", max_retries, elapsed)
                    raise e

                backoff = min(2**retries, 30)
                _log.warning("Waiting for session failed after %.1fs (%s). Retrying in %ds...", elapsed, e, backoff)
                time.sleep(backoff)

        elapsed = time.monotonic() - start_time
        raise TimeoutError(f"Session did not become active within {timeout} seconds (elapsed: {elapsed:.1f}s)")

    def acquire(self, topology: pathlib.Path, reuse: bool) -> list[DeviceInfoDto]:
        _log.info("Starting lab acquisition for %s (reuse=%s)", topology.name, reuse)

        with topology.open("rb") as f:
            files = {"topology": (topology.name, f, "application/x-yaml")}
            data = {"reuse": str(reuse).lower()}

            while True:
                try:
                    _log.info("Acquiring lab %s (timeout=%ds)...", topology.name, self.lab_acquisition_timeout)

                    resp = self._make_request(
                        "POST",
                        self._url("/lab"),
                        files=files,
                        data=data,
                        timeout=self.lab_acquisition_timeout,
                    )

                    if resp.status_code == 423:  # HTTP 423 Locked
                        _log.debug("Lab busy, retrying in 5s...")
                        time.sleep(5)
                        continue

                    resp.raise_for_status()
                    _log.info("Lab acquired successfully.")
                    break

                except requests.exceptions.RequestException as e:
                    _log.error("Request failed: %s", e)
                    raise

        response_data = resp.json()
        devices = [DeviceInfoDto(**d) for d in response_data["devices"]]
        _log.info("Lab acquisition complete: %d devices", len(devices))
        return devices

    def release(self) -> None:
        _log.info("Releasing lab for session %s", self.session_id[:8])
        try:
            resp = self._make_request("POST", self._url("/lab/release"), timeout=self.request_timeout)
            # Note: release may return 404 if no lab is running, which is fine
            if resp.status_code not in (204, 404):
                resp.raise_for_status()
            _log.info("Lab released successfully")
        except Exception as e:
            _log.error("Failed to release lab: %s", e)

    def destroy(self, force: bool = True) -> None:
        _log.info("Destroying lab for session %s (force=%s)", self.session_id[:8], force)
        try:
            resp = self._make_request(
                "DELETE", self._url("/lab"), params={"force": str(force).lower()}, timeout=self.request_timeout
            )
            # Note: destroy may return various codes depending on lab state
            if resp.status_code not in (202, 204):
                resp.raise_for_status()
            _log.info("Lab destroyed successfully")
        except Exception as e:
            _log.error("Failed to destroy lab: %s", e)

    def close(self) -> None:
        """End the session and release all resources."""
        if self.session_id and self.session_id != "":
            _log.info("Closing session %s", self.session_id[:8])
            try:
                resp = self._make_request(
                    "DELETE", self._url(f"/session/{self.session_id}"), timeout=self.request_timeout
                )
                if resp.status_code not in (204, 404):
                    resp.raise_for_status()
                _log.info("Closed session %s successfully", self.session_id[:8])
            except requests.exceptions.RequestException as e:
                _log.warning("Failed to close session %s (server may be down): %s", self.session_id[:8], e)
            finally:
                self.session_id = ""
        else:
            _log.debug("No session to close")
