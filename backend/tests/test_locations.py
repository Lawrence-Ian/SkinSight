import asyncio
from math import pi

from app.api import locations


def test_nearby_search_returns_skincare_shops_and_only_places_under_radius(monkeypatch):
    inside_latitude = (4.99 / 6371) * (180 / pi)
    boundary_latitude = (5 / 6371) * (180 / pi)
    outside_latitude = (5.01 / 6371) * (180 / pi)
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": inside_latitude,
                "lon": 0,
                "tags": {"shop": "cosmetics", "name": "Skincare Store"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": boundary_latitude,
                "lon": 0,
                "tags": {"amenity": "clinic", "name": "Boundary Clinic"},
            },
            {
                "type": "node",
                "id": 3,
                "lat": outside_latitude,
                "lon": 0,
                "tags": {"healthcare": "clinic", "name": "Outside Clinic"},
            },
        ]
    }
    requested = {}

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def post(self, endpoint, data, timeout):
            requested["endpoint"] = endpoint
            requested["query"] = data["data"]
            requested["timeout"] = timeout.read
            return MockResponse()

    monkeypatch.setattr(locations.httpx, "AsyncClient", MockClient)

    result = asyncio.run(locations.get_nearby_places(
        lat=0,
        lng=0,
        radius_km=5,
        type_filter="all",
    ))

    assert result["search_radius_km"] == 5
    assert [place["name"] for place in result["stores"]] == ["Skincare Store"]
    assert result["clinics"] == []
    assert result["total_clinics"] == 0
    assert result["total_stores"] == 1
    assert result["stores"][0]["distance_km"] < 5
    assert 'cosmetics' in requested["query"]
    assert '["healthcare"="pharmacy"]' in requested["query"]
    assert "[timeout:10]" in requested["query"]
    assert requested["timeout"] == 12.0


def test_nearby_search_falls_back_to_another_overpass_endpoint(monkeypatch):
    calls = []

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"elements": []}

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def post(self, endpoint, data, timeout):
            calls.append(endpoint)
            if len(calls) == 1:
                raise locations.httpx.TimeoutException("Overpass timed out")
            return MockResponse()

    monkeypatch.setattr(locations.httpx, "AsyncClient", MockClient)

    result = asyncio.run(locations.get_nearby_places(
        lat=0,
        lng=0,
        radius_km=5,
        type_filter="all",
    ))

    assert len(calls) == 2
    assert result["clinics"] == []
    assert result["stores"] == []


def test_nearby_search_returns_retryable_service_error_when_all_providers_fail(monkeypatch):
    calls = []

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def post(self, endpoint, data, timeout):
            calls.append(endpoint)
            raise locations.httpx.TimeoutException("Overpass timed out")

        async def get(self, endpoint, params, timeout):
            raise locations.httpx.TimeoutException("Nominatim timed out")

    monkeypatch.setattr(locations.httpx, "AsyncClient", MockClient)

    try:
        asyncio.run(locations.get_nearby_places(
            lat=0,
            lng=0,
            radius_km=5,
            type_filter="all",
        ))
        assert False, "unavailable providers must not return successful empty results"
    except locations.HTTPException as error:
        assert error.status_code == 503
        assert error.headers["Retry-After"] == "30"
        assert "temporarily unavailable" in error.detail

    assert calls == list(locations.OVERPASS_ENDPOINTS)


def test_nearby_search_uses_nominatim_when_overpass_is_unavailable(monkeypatch):
    inside_latitude = (4.99 / 6371) * (180 / pi)
    boundary_latitude = (5 / 6371) * (180 / pi)
    query_terms = []

    class MockResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    class MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

        async def post(self, endpoint, data, timeout):
            raise locations.httpx.TimeoutException("Overpass timed out")

        async def get(self, endpoint, params, timeout):
            query_terms.append(params["q"])
            if params["q"] == "clinic":
                return MockResponse([
                    {
                        "osm_type": "way",
                        "osm_id": 10,
                        "lat": str(inside_latitude),
                        "lon": "0",
                        "category": "amenity",
                        "type": "clinic",
                        "name": "Nearby Clinic",
                        "display_name": "Nearby Clinic, Manila",
                        "extratags": {},
                    },
                    {
                        "osm_type": "way",
                        "osm_id": 11,
                        "lat": str(boundary_latitude),
                        "lon": "0",
                        "category": "amenity",
                        "type": "hospital",
                        "name": "Boundary Hospital",
                        "display_name": "Boundary Hospital, Manila",
                        "extratags": {},
                    },
                ])
            if params["q"] == "pharmacy":
                return MockResponse([
                    {
                        "osm_type": "node",
                        "osm_id": 20,
                        "lat": str(inside_latitude),
                        "lon": "0",
                        "category": "amenity",
                        "type": "pharmacy",
                        "name": "Nearby Pharmacy",
                        "display_name": "Nearby Pharmacy, Manila",
                        "extratags": {},
                    },
                ])
            return MockResponse([
                {
                    "osm_type": "node",
                    "osm_id": 30,
                    "lat": str(inside_latitude),
                    "lon": "0",
                    "category": "shop",
                    "type": "beauty",
                    "name": "Beauty Shop",
                    "display_name": "Beauty Shop, Manila",
                    "extratags": {},
                },
                {
                    "osm_type": "node",
                    "osm_id": 31,
                    "lat": str(inside_latitude),
                    "lon": "0",
                    "category": "shop",
                    "type": "copyshop",
                    "name": "Copy Shop",
                    "display_name": "Copy Shop, Manila",
                    "extratags": {},
                },
            ])

    monkeypatch.setattr(locations.httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(locations, "NOMINATIM_REQUEST_INTERVAL", 0)
    locations._nominatim_cache.clear()

    result = asyncio.run(locations.get_nearby_places(
        lat=0,
        lng=0,
        radius_km=5,
        type_filter="all",
    ))

    assert result["data_source"] == "openstreetmap-nominatim"
    assert [place["name"] for place in result["clinics"]] == ["Nearby Clinic"]
    assert {place["name"] for place in result["stores"]} == {"Nearby Pharmacy", "Beauty Shop"}
    assert all(place["distance_km"] < 5 for place in result["clinics"] + result["stores"])
    assert query_terms == ["clinic", "hospital", "pharmacy", "beauty"]
