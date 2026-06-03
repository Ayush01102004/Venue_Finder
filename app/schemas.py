from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class CategoryType(str, Enum):
    restaurant = "restaurant"
    cafe = "cafe"
    date_spot = "date_spot"


CATEGORY_TO_GOOGLE_TYPE: dict[CategoryType, list[str]] = {
    CategoryType.restaurant: ["restaurant"],
    CategoryType.cafe: ["cafe"],
    CategoryType.date_spot: [
        "restaurant",
        "cafe",
        "park",
        "tourist_attraction",
    ],
}


VALID_RADII = [5000, 10000, 15000, 25000]


class VenueRequest(BaseModel):
    lat: float
    lng: float
    radius: int
    type: CategoryType
    min_rating: float = 3.5

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float) -> float:
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, v: int) -> int:
        if v not in VALID_RADII:
            raise ValueError(
                f"Radius must be one of {VALID_RADII} metres"
            )
        return v

    @field_validator("min_rating")
    @classmethod
    def validate_min_rating(cls, v: float) -> float:
        if not (3.5 <= v <= 5.0):
            raise ValueError(
                "min_rating must be between 3.5 and 5.0"
            )
        return v


class Venue(BaseModel):
    name: str
    rating: float | None
    user_ratings_total: int | None = None
    address: str | None
    lat: float
    lng: float
    place_id: str

    # Google Places Photo URLs
    photos: list[str] = Field(default_factory=list)


class VenueResponse(BaseModel):
    venues: List[Venue]
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str