# Venue Finder API

A FastAPI-based microservice that discovers nearby venues using Google Places API.

The service supports:

* Restaurants
* Cafes
* Date Spots

and provides:

* Radius-based filtering
* Rating-based filtering
* Distance validation using Haversine formula
* Google Places pagination support
* FastAPI OpenAPI documentation
* Unit testing with Pytest

---

## Features

### Nearby Venue Search

Search venues around a given latitude and longitude.

### Radius Enforcement

Google Places treats radius as a hint.

This service applies an additional Haversine-distance check to ensure all returned venues are strictly inside the requested radius.

### Rating Filter

Supports filtering venues by minimum rating.

Example:

min_rating=4.5

Only venues with rating >= 4.5 will be returned.

### Category Support

* cafe
* restaurant
* date_spot

### Google Places Pagination

Automatically retrieves all available result pages from Google Places API.

---

## Tech Stack

* FastAPI
* Python 3.11+
* Pydantic v2
* HTTPX
* Google Places API
* Pytest

---

## Installation

Clone repository
```
git clone https://github.com/yourusername/venue-finder.git
cd venue-finder
```

Install dependencies

```
pip install -r requirements.txt
```

---

## Environment Variables

Create .env

```
GOOGLE_PLACES_API_KEY=YOUR_API_KEY
```

---

## Run Application

```
uvicorn main:app --reload
```

Application:

```
http://localhost:8000
```

Swagger:

```
http://localhost:8000/docs
```

Redoc:

```
http://localhost:8000/redoc
```

---

## Health Endpoint

GET /health

Response

```
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## Search Venues

GET /venues

Parameters

| Parameter  | Type   | Required |
| ---------- | ------ | -------- |
| lat        | float  | Yes      |
| lng        | float  | Yes      |
| radius     | int    | Yes      |
| type       | string | Yes      |
| min_rating | float  | No       |

Example

GET /venues?lat=22.3072&lng=73.1812&radius=5000&type=cafe&min_rating=4.0

---

## Supported Radius Values

5000

10000

15000

25000

---

## Example Response

```
{
  "venues": [
    {
      "name": "Coffee Culture",
      "rating": 4.7,
      "address": "Gotri Rd, Vadodara",
      "lat": 22.3075,
      "lng": 73.1815,
      "place_id": "ChIJtestplace123"
    }
  ],
  "total": 1
}
```

---

## Run Tests

```
pytest -v
```

---

## Project Structure

```
venue-finder
│
├── app
│   ├── main.py
│   ├── schemas.py
│   ├── venue_service.py
│   └── google_places.py
│
├── tests
│   └── test_main.py
│
├── frontend
│   └── Venue_Finder.html
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```
