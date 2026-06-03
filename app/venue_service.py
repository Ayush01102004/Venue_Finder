import asyncio
import logging
import math
from typing import Any

from app.google_places import GooglePlacesClient
from app.schemas import (
    CATEGORY_TO_GOOGLE_TYPE,
    CategoryType,
    Venue,
    VenueResponse,
)

logger = logging.getLogger(__name__)


def _haversine(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """
    Return the great-circle distance in metres
    between two coordinates.
    """
    R = 6_371_000
    p = math.pi / 180

    a = (
        math.sin((lat2 - lat1) * p / 2) ** 2
        + math.cos(lat1 * p)
        * math.cos(lat2 * p)
        * math.sin((lng2 - lng1) * p / 2) ** 2
    )

    return R * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )


def _parse_venue(
    place: dict[str, Any],
) -> Venue | None:
    try:
        loc = place["geometry"]["location"]

        return Venue(
            name=place.get("name", "Unknown"),
            rating=place.get("rating"),
            user_ratings_total=place.get("user_ratings_total"),
            address=place.get("vicinity"),
            lat=loc["lat"],
            lng=loc["lng"],
            place_id=place["place_id"],
            photos=[],
        )

    except (KeyError, TypeError) as exc:
        logger.warning(
            "Skipping malformed place record: %s",
            exc,
        )
        return None


class VenueService:
    def __init__(
        self,
        places_client: GooglePlacesClient,
    ) -> None:
        self._places = places_client

    async def find_venues(
        self,
        lat: float,
        lng: float,
        radius: int,
        category: CategoryType,
        min_rating: float = 3.5,
    ) -> VenueResponse:
        google_types = CATEGORY_TO_GOOGLE_TYPE[category]

        raw = await self._places.nearby_search(
            lat=lat,
            lng=lng,
            radius=radius,
            place_types=google_types,
        )

        venues: list[Venue] = []

        for place in raw:
            venue = _parse_venue(place)

            if venue:
                venues.append(venue)

        # Hard-enforce radius —
        # Google's boundary is a hint, not a guarantee
        before = len(venues)

        venues = [
            v
            for v in venues
            if _haversine(
                lat,
                lng,
                v.lat,
                v.lng,
            )
            <= radius
        ]

        filtered = before - len(venues)

        if filtered:
            logger.info(
                "Radius post-filter removed %d venue(s) outside %dm",
                filtered,
                radius,
            )

        # Filter by minimum rating
        venues = [
            v
            for v in venues
            if (
                v.rating
                if v.rating is not None
                else -1
            )
            >= min_rating
        ]

        # Fetch up to 5 photos per venue using Place Details API
        photo_tasks = [
            self._places.fetch_photo_urls(
                venue.place_id,
                max_photos=5,
            )
            for venue in venues
        ]

        photo_results = await asyncio.gather(
            *photo_tasks,
            return_exceptions=True,
        )

        for venue, photos in zip(
            venues,
            photo_results,
            strict=False,
        ):
            if isinstance(photos, Exception):
                logger.warning(
                    "Failed fetching photos for place_id=%s",
                    venue.place_id,
                )
                venue.photos = []
            else:
                venue.photos = photos

        # Sort by rating descending
        venues.sort(
            key=lambda v: v.rating or 0.0,
            reverse=True,
        )

        return VenueResponse(
            venues=venues,
            total=len(venues),
        )