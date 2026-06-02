import asyncio
import httpx
from typing import Any
import logging

logger = logging.getLogger(__name__)

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"


class GooglePlacesError(Exception):
    """Raised when Google Places API returns an error."""


class GooglePlacesClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def nearby_search(
        self,
        lat: float,
        lng: float,
        radius: int,
        place_types: list[str],
    ) -> list[dict[str, Any]]:
        """
        Call Google Places Nearby Search for each requested type, following
        next_page_token pagination to retrieve beyond the 20-result per-page cap.
        Returns a deduplicated list of raw place records.
        """
        seen: set[str] = set()
        results: list[dict[str, Any]] = []

        for place_type in place_types:
            # Initial query params
            params: dict[str, Any] = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "key": self._api_key,
            }

            # Fetch all pages for this type (Google caps at 20/page, up to 3 pages = 60 results)
            while True:
                try:
                    response = await self._client.get(PLACES_NEARBY_URL, params=params)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.error("Google Places HTTP error: %s", exc)
                    raise GooglePlacesError(f"HTTP error contacting Google Places: {exc}") from exc

                payload = response.json()
                status = payload.get("status")

                if status not in ("OK", "ZERO_RESULTS"):
                    logger.error("Google Places API status=%s", status)
                    raise GooglePlacesError(
                        f"Google Places API returned status '{status}'"
                    )

                for place in payload.get("results", []):
                    pid = place.get("place_id")
                    if pid and pid not in seen:
                        seen.add(pid)
                        results.append(place)

                next_token = payload.get("next_page_token")
                if not next_token:
                    break

                # Google requires a short delay before next_page_token becomes valid
                await asyncio.sleep(2)
                params = {"pagetoken": next_token, "key": self._api_key}

        return results

    async def aclose(self) -> None:
        await self._client.aclose()