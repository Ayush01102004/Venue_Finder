import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACE_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"


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
        Call Google Places Nearby Search for each requested type,
        following next_page_token pagination to retrieve beyond
        the 20-result per-page cap.

        Returns a deduplicated list of raw place records.
        """
        seen: set[str] = set()
        results: list[dict[str, Any]] = []

        for place_type in place_types:
            params: dict[str, Any] = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "key": self._api_key,
            }

            while True:
                try:
                    response = await self._client.get(
                        PLACES_NEARBY_URL,
                        params=params,
                    )
                    response.raise_for_status()

                except httpx.HTTPError as exc:
                    logger.error(
                        "Google Places HTTP error: %s",
                        exc,
                    )
                    raise GooglePlacesError(
                        f"HTTP error contacting Google Places: {exc}"
                    ) from exc

                payload = response.json()
                status = payload.get("status")

                if status not in ("OK", "ZERO_RESULTS"):
                    logger.error(
                        "Google Places API status=%s",
                        status,
                    )
                    raise GooglePlacesError(
                        f"Google Places API returned status '{status}'"
                    )

                for place in payload.get("results", []):
                    place_id = place.get("place_id")

                    if place_id and place_id not in seen:
                        seen.add(place_id)
                        results.append(place)

                next_token = payload.get("next_page_token")

                if not next_token:
                    break

                await asyncio.sleep(2)

                params = {
                    "pagetoken": next_token,
                    "key": self._api_key,
                }

        return results

    async def fetch_photo_urls(
        self,
        place_id: str,
        max_photos: int = 5,
    ) -> list[str]:
        """
        Fetch photo references from Place Details API.

        Unlike Nearby Search, Place Details often returns
        many more photos for a venue.
        """

        try:
            response = await self._client.get(
                PLACE_DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "name,photos",
                    "key": self._api_key,
                },
            )

            response.raise_for_status()

        except httpx.HTTPError as exc:
            logger.error(
                "Google Place Details HTTP error: %s",
                exc,
            )
            return []

        payload = response.json()

        if payload.get("status") != "OK":
            logger.warning(
                "Place Details returned status=%s for place_id=%s",
                payload.get("status"),
                place_id,
            )
            return []

        photos = (
            payload.get("result", {})
            .get("photos", [])[:max_photos]
        )

        return [
            (
                f"{PLACE_PHOTO_URL}"
                f"?maxwidth=1200"
                f"&photo_reference={photo['photo_reference']}"
                f"&key={self._api_key}"
            )
            for photo in photos
            if "photo_reference" in photo
        ]

    def build_photo_urls_from_place(
        self,
        place: dict[str, Any],
        max_photos: int = 5,
    ) -> list[str]:
        """
        Fallback method using Nearby Search photos only.
        """

        photos = place.get("photos", [])[:max_photos]

        return [
            (
                f"{PLACE_PHOTO_URL}"
                f"?maxwidth=1200"
                f"&photo_reference={photo['photo_reference']}"
                f"&key={self._api_key}"
            )
            for photo in photos
            if "photo_reference" in photo
        ]

    async def aclose(self) -> None:
        await self._client.aclose()