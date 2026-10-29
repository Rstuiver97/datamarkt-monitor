"""Collectors: elk haalt data op uit één gratis bron."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger("marktmonitor")

USER_AGENT = "datamarkt-monitor/1.0 (+https://github.com; non-commercial labour-market research)"


class Http:
    """Kleine wrapper met retries, backoff en een vaste User-Agent."""

    def __init__(self, timeout: int = 30, retries: int = 3, pause: float = 0.5):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.timeout = timeout
        self.retries = retries
        self.pause = pause
        self.calls = 0

    def get(self, url: str, params: dict | None = None, expect_json: bool = True):
        last_exc = None
        for attempt in range(self.retries):
            try:
                self.calls += 1
                r = self.s.get(url, params=params, timeout=self.timeout)
                if r.status_code == 404:
                    return None
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"{r.status_code} for {r.url}")
                r.raise_for_status()
                time.sleep(self.pause)
                return r.json() if expect_json else r.text
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
        log.warning("Ophalen mislukt: %s (%s)", url, last_exc)
        return None
