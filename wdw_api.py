"""
WDW Dining Availability API Client

Disney does not publish an official public API, but their dining finder
uses an internal REST API that can be queried directly.

HOW TO FIND / VERIFY THE CURRENT ENDPOINT
------------------------------------------
If you are getting unexpected errors, the endpoint URL may have changed.
To locate the current one:
  1. Open https://disneyworld.disney.go.com/dining/ in Chrome/Edge.
  2. Open DevTools (F12) → Network tab → filter by "Fetch/XHR".
  3. Choose a restaurant, date, and party size to trigger a search.
  4. Look for a request whose URL contains "availability" or "dining".
  5. Update AVAILABILITY_URL below with the new path, and adjust
     _build_params() if the parameter names differ.
  6. You can also inspect the response JSON to update parse_availability().
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoint configuration
# ---------------------------------------------------------------------------

DISNEY_BASE = "https://disneyworld.disney.go.com"

# Primary endpoint — used by the WDW dining finder (reverse-engineered).
# Override via the env var DISNEYRES_AVAILABILITY_URL if needed.
AVAILABILITY_URL = os.getenv(
    "DISNEYRES_AVAILABILITY_URL",
    f"{DISNEY_BASE}/dine-vas/api/getAvailability",
)

# Guest-token endpoint (no auth required)
_TOKEN_URL = f"{DISNEY_BASE}/profile-api/authentication/get-client-token"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": f"{DISNEY_BASE}/dining/",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


class WDWDiningAPI:
    """
    Thin wrapper around the WDW dining availability endpoint.

    A single requests.Session is reused across calls so cookies and
    keep-alive connections are maintained automatically.
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(_DEFAULT_HEADERS)
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        # Seed the session with a cookie-bearing response from the main site.
        self._init_session()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_availability(
        self,
        restaurant_id: str,
        date: str,
        party_size: int,
        start_time: str = "08:00",
        end_time: str = "21:00",
    ) -> dict[str, Any]:
        """
        Query the WDW dining availability endpoint.

        Attempts authenticated requests using the Disney guest token, trying
        both POST (JSON body) and GET (query params) methods.

        Parameters
        ----------
        restaurant_id : str
            WDW facility/entity ID (e.g. "90002822" for Be Our Guest).
        date : str
            Reservation date in ``YYYY-MM-DD`` format.
        party_size : int
            Number of guests (1–20).
        start_time : str
            Earliest desired slot in ``HH:MM`` 24-hour format.
        end_time : str
            Latest desired slot in ``HH:MM`` 24-hour format.

        Returns
        -------
        dict
            Raw JSON payload returned by Disney's API.

        Raises
        ------
        requests.HTTPError
            For 4xx / 5xx responses.
        requests.ConnectionError
            If the host is unreachable.
        ValueError
            If the response body is not valid JSON.
        """
        self._refresh_token()
        payload = self._build_params(
            restaurant_id, date, party_size, start_time, end_time
        )

        # Try each (method, url) combination until one succeeds.
        attempts = [
            ("GET",  AVAILABILITY_URL),
            ("POST", AVAILABILITY_URL),
        ]

        last_exc: Exception | None = None
        for method, url in attempts:
            try:
                response = self._request(method, url, payload)
            except requests.HTTPError as exc:
                last_exc = exc
                status = exc.response.status_code if exc.response is not None else 0
                # 405 = wrong method, try next; anything else → raise immediately
                if status in (405, 403):
                    logger.debug("%s %s → %s, retrying …", method, url, status)
                    continue
                raise
            except Exception:
                raise

            try:
                return response.json()
            except ValueError as exc:
                logger.error(
                    "Non-JSON response (%s): %s",
                    response.status_code,
                    response.text[:600],
                )
                raise ValueError(
                    f"Disney API returned a non-JSON response (HTTP {response.status_code}). "
                    "The endpoint may have changed — see wdw_api.py for instructions."
                ) from exc

        raise ValueError(
            "All direct API attempts failed (405/403).  "
            "The endpoint likely requires stronger authentication. "
            "Run with --verbose to see details, or see wdw_api.py for instructions."
        ) from last_exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_availability(
        self,
        restaurant_id: str,
        date: str,
        party_size: int,
        start_time: str = "08:00",
        end_time: str = "21:00",
    ) -> dict[str, Any]:
        """
        Query the WDW dining availability endpoint.

        Tries POST (JSON body) first, then falls back to GET (query params)
        if the server rejects POST.  This covers the range of method styles
        Disney has used across API versions.

        Parameters
        ----------
        restaurant_id : str
            WDW facility/entity ID (e.g. "90002822" for Be Our Guest).
        date : str
            Reservation date in ``YYYY-MM-DD`` format.
        party_size : int
            Number of guests (1–20).
        start_time : str
            Earliest desired slot in ``HH:MM`` 24-hour format.
        end_time : str
            Latest desired slot in ``HH:MM`` 24-hour format.

        Returns
        -------
        dict
            Raw JSON payload returned by Disney's API.

        Raises
        ------
        requests.HTTPError
            For 4xx / 5xx responses.
        requests.ConnectionError
            If the host is unreachable.
        ValueError
            If the response body is not valid JSON.
        """
        payload = self._build_params(
            restaurant_id, date, party_size, start_time, end_time
        )

        # Try each (method, url) combination until one succeeds.
        attempts = [
            ("POST", AVAILABILITY_URL),
            ("GET",  AVAILABILITY_URL),
        ]

        last_exc: Exception | None = None
        for method, url in attempts:
            try:
                response = self._request(method, url, payload)
            except requests.HTTPError as exc:
                last_exc = exc
                status = exc.response.status_code if exc.response is not None else 0
                # 405 = wrong method, try next; anything else → raise immediately
                if status == 405:
                    logger.debug("%s %s → 405, retrying with next attempt", method, url)
                    continue
                raise
            except Exception:
                raise

            try:
                return response.json()
            except ValueError as exc:
                logger.error(
                    "Non-JSON response (%s): %s",
                    response.status_code,
                    response.text[:600],
                )
                raise ValueError(
                    f"Disney API returned a non-JSON response (HTTP {response.status_code}). "
                    "The endpoint may have changed — see wdw_api.py for instructions."
                ) from exc

        # All attempts failed with 405
        raise ValueError(
            "The WDW dining API returned 405 (Method Not Allowed) for every "
            "attempt.  The endpoint URL or required HTTP method may have "
            "changed.  See the HOW TO FIND / VERIFY section at the top of "
            "wdw_api.py for instructions."
        ) from last_exc

    def has_availability(self, data: Any) -> bool:
        """Return True if *data* indicates at least one bookable slot."""
        return len(self.parse_availability(data)) > 0

    def parse_availability(self, data: Any) -> list[dict[str, Any]]:
        """
        Extract bookable time slots from a raw API response.

        Disney's response format has changed several times over the years;
        this method handles the most common shapes without being fragile.

        Returns a (possibly empty) list of dicts, each with at minimum a
        ``"time"`` key and optionally ``"mealPeriod"``, ``"partySize"``,
        etc.
        """
        if data is None:
            return []

        # Shape 1 — top-level list of slot objects
        if isinstance(data, list):
            return [s for s in data if isinstance(s, dict)]

        if not isinstance(data, dict):
            return []

        # Explicit "no availability" flag
        if data.get("hasAvailability") is False or data.get("available") is False:
            return []

        # Explicit "has availability" flag with no embedded slots
        if data.get("hasAvailability") is True or data.get("available") is True:
            # Try to extract slots anyway; fall back to a sentinel dict
            slots = self._extract_slots(data)
            return slots if slots else [{"time": "Available — check Disney site", "mealPeriod": ""}]

        return self._extract_slots(data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _refresh_token(self) -> None:
        """Fetch/refresh the Disney guest token and set it on the session."""
        import time as _time
        if self._token and _time.time() < self._token_expires_at:
            return  # Still valid
        try:
            resp = self._session.get(
                _TOKEN_URL,
                headers={"skip-intercept": "true"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            expires_in = int(data.get("expires_in", 1800))
            self._token_expires_at = _time.time() + expires_in - 60  # 60 s buffer
            if self._token:
                self._session.headers["Authorization"] = f"BEARER {self._token}"
                logger.debug("Refreshed Disney guest token (expires in %ds)", expires_in)
        except Exception as exc:
            logger.warning("Could not obtain guest token: %s", exc)

    def _request(
        self, method: str, url: str, payload: dict[str, str]
    ) -> requests.Response:
        """
        Execute an HTTP request, trying JSON body for POST and query
        string for GET.  Raises ``requests.HTTPError`` on non-2xx status.
        """
        logger.debug("%s %s  payload=%s", method, url, payload)
        if method == "POST":
            response = self._session.post(url, json=payload, timeout=30)
        else:
            response = self._session.get(url, params=payload, timeout=30)

        if not response.ok:
            logger.warning(
                "HTTP %s from %s %s — body: %s",
                response.status_code,
                method,
                url,
                response.text[:600],
            )
            response.raise_for_status()

        return response

    @staticmethod
    def _build_params(
        restaurant_id: str,
        date: str,
        party_size: int,
        start_time: str,
        end_time: str,
    ) -> dict[str, str]:
        return {
            "id": restaurant_id,
            "type": "RESTAURANT",
            "partySize": str(party_size),
            "searchDate": date,
            "startTime": start_time,
            "endTime": end_time,
        }

    def _init_session(self) -> None:
        """
        Load the Disney dining page to prime session cookies.
        Failures are non-fatal — we log and continue.
        """
        try:
            resp = self._session.get(
                f"{DISNEY_BASE}/dining/",
                timeout=15,
                allow_redirects=True,
            )
            logger.debug("Session init: HTTP %s", resp.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Session init failed (non-fatal): %s", exc)

    @staticmethod
    def _extract_slots(data: dict[str, Any]) -> list[dict[str, Any]]:
        """Walk common response shapes and collect time-slot dicts."""
        slots: list[dict[str, Any]] = []

        # Shape: {"availability": {"DINNER": {"times": [...]}}}
        # Shape: {"availability": {"DINNER": [...]}}
        # Shape: {"availability": [...]}
        avail = data.get("availability")
        if isinstance(avail, list):
            for item in avail:
                if isinstance(item, dict):
                    slots.append(item)
                elif isinstance(item, str):
                    slots.append({"time": item})
        elif isinstance(avail, dict):
            for period, period_data in avail.items():
                if isinstance(period_data, dict):
                    raw_times = period_data.get("times") or period_data.get("offers") or []
                elif isinstance(period_data, list):
                    raw_times = period_data
                else:
                    continue
                for t in raw_times:
                    if isinstance(t, str):
                        slots.append({"time": t, "mealPeriod": period})
                    elif isinstance(t, dict):
                        t.setdefault("mealPeriod", period)
                        slots.append(t)

        # Shape: top-level "times" / "slots" / "offers" / "timeSlots"
        if not slots:
            for key in ("times", "slots", "offers", "timeSlots", "reservations"):
                raw = data.get(key)
                if isinstance(raw, list):
                    for t in raw:
                        if isinstance(t, str):
                            slots.append({"time": t})
                        elif isinstance(t, dict):
                            slots.append(t)
                    if slots:
                        break

        return slots
