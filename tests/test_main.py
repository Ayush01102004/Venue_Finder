"""
test_main.py
------------
Pytest test suite for the Venue Finder FastAPI service.

Run:
    pytest test_main.py -v
"""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.google_places import GooglePlacesError
from app.main import app, get_places_client
from app.schemas import VALID_RADII

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PLACE = {
    "place_id": "ChIJtestplace123",
    "name": "Coffee Culture",
    "rating": 4.7,
    "vicinity": "Gotri Rd, Vadodara",
    "geometry": {"location": {"lat": 22.3075, "lng": 73.1815}},
}


@pytest.fixture()
def mock_places_client() -> MagicMock:
    client = MagicMock()
    client.nearby_search = AsyncMock(return_value=[SAMPLE_PLACE])
    return client


@pytest.fixture()
def api_client(mock_places_client: MagicMock) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_places_client] = lambda: mock_places_client
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self, api_client: TestClient) -> None:
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, api_client: TestClient) -> None:
        data = api_client.get("/health").json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
# Successful venue search
# ---------------------------------------------------------------------------

class TestVenueSearch:
    def test_returns_200(self, api_client: TestClient) -> None:
        response = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        )
        assert response.status_code == 200

    def test_returns_venue_list(self, api_client: TestClient) -> None:
        data = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        ).json()
        assert "venues" in data
        assert "total" in data
        assert data["total"] == len(data["venues"])

    def test_venue_fields(self, api_client: TestClient) -> None:
        venues = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        ).json()["venues"]
        assert len(venues) == 1
        venue = venues[0]
        for field in ("name", "rating", "address", "lat", "lng", "place_id"):
            assert field in venue, f"Missing field: {field}"

    def test_venue_values(self, api_client: TestClient) -> None:
        venue = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        ).json()["venues"][0]
        assert venue["name"] == "Coffee Culture"
        assert venue["rating"] == 4.7
        assert venue["place_id"] == "ChIJtestplace123"

    def test_restaurant_category(self, api_client: TestClient) -> None:
        response = api_client.get(
            "/venues",
            params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "restaurant"},
        )
        assert response.status_code == 200

    def test_date_spot_category(self, api_client: TestClient) -> None:
        response = api_client.get(
            "/venues",
            params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "date_spot"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invalid radius
# ---------------------------------------------------------------------------

class TestInvalidRadius:
    @pytest.mark.parametrize(
        "bad_radius",
        [
            0,
            500,
            999,
            1500,
            2500,
            4000,
            6000,
            12000,
            18000,
            30000,
            -1,
            4999,
        ],
    )
    def test_invalid_radius_returns_422(
        self,
        api_client: TestClient,
        bad_radius: int,
    ) -> None:
        response = api_client.get(
            "/venues",
            params={
                "lat": 22.3072,
                "lng": 73.1812,
                "radius": bad_radius,
                "type": "cafe",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("good_radius", VALID_RADII)
    def test_valid_radii_accepted(
        self,
        api_client: TestClient,
        good_radius: int,
    ) -> None:
        response = api_client.get(
            "/venues",
            params={
                "lat": 22.3072,
                "lng": 73.1812,
                "radius": good_radius,
                "type": "cafe",
            },
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Google API failure
# ---------------------------------------------------------------------------

class TestGoogleAPIFailure:
    def test_google_error_returns_502(self, api_client: TestClient, mock_places_client: MagicMock) -> None:
        mock_places_client.nearby_search = AsyncMock(
            side_effect=GooglePlacesError("REQUEST_DENIED")
        )
        response = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        )
        assert response.status_code == 502

    def test_google_error_detail_in_response(
        self, api_client: TestClient, mock_places_client: MagicMock
    ) -> None:
        mock_places_client.nearby_search = AsyncMock(
            side_effect=GooglePlacesError("OVER_QUERY_LIMIT")
        )
        data = api_client.get(
            "/venues", params={"lat": 22.3072, "lng": 73.1812, "radius": 5000, "type": "cafe"}
        ).json()
        assert "detail" in data
