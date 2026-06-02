import os
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.google_places import GooglePlacesClient, GooglePlacesError
from app.schemas import (
    CategoryType,
    HealthResponse,
    VALID_RADII,
    VenueResponse,
)
from app.venue_service import VenueService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

_places_client: GooglePlacesClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _places_client

    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")

    print(f"GOOGLE_PLACES_API_KEY: {'set' if api_key else 'not set'}")

    if not api_key:
        logger.warning("GOOGLE_PLACES_API_KEY is not set – requests will fail")

    _places_client = GooglePlacesClient(api_key=api_key)

    logger.info("GooglePlacesClient initialised")

    yield

    if _places_client:
        await _places_client.aclose()

    logger.info("GooglePlacesClient closed")


app = FastAPI(
    title="Venue Finder",
    description="Find nearby restaurants, cafes and date spots using Google Places.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def get_places_client() -> GooglePlacesClient:
    if _places_client is None:
        raise RuntimeError("GooglePlacesClient has not been initialised")

    return _places_client


def get_venue_service(
    client: Annotated[GooglePlacesClient, Depends(get_places_client)],
) -> VenueService:
    return VenueService(places_client=client)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(
        status="ok",
        version=app.version,
    )


@app.get("/venues", response_model=VenueResponse, tags=["venues"])
async def get_venues(
    lat: Annotated[
        float,
        Query(
            description="Latitude of the search origin",
            ge=-90,
            le=90,
        ),
    ],
    lng: Annotated[
        float,
        Query(
            description="Longitude of the search origin",
            ge=-180,
            le=180,
        ),
    ],
    radius: Annotated[
        int,
        Query(
            description=f"Search radius in metres. Allowed values: {VALID_RADII}",
        ),
    ],
    type: Annotated[
        CategoryType,
        Query(description="Venue category"),
    ],
    min_rating: Annotated[
        float,
        Query(
            description="Minimum rating filter (3.5–5.0)",
            ge=3.5,
            le=5.0,
        ),
    ] = 3.5,
    service: Annotated[
        VenueService,
        Depends(get_venue_service),
    ] = None,
) -> VenueResponse:
    """
    Return venues near the given coordinates filtered by category.
    """

    if radius not in VALID_RADII:
        raise HTTPException(
            status_code=422,
            detail=f"radius must be one of {VALID_RADII}",
        )

    try:
        result = await service.find_venues(
            lat=lat,
            lng=lng,
            radius=radius,
            category=type,
            min_rating=min_rating,
        )

    except GooglePlacesError as exc:
        logger.error("Google Places error: %s", exc)

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    logger.info(
        (
            "venues query lat=%.4f lng=%.4f "
            "radius=%d type=%s min_rating=%.1f → %d results"
        ),
        lat,
        lng,
        radius,
        type,
        min_rating,
        result.total,
    )

    return result


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def generic_handler(request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )