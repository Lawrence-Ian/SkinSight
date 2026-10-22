"""Nearby clinic and shop search using OpenStreetMap data."""

import asyncio
import logging
from math import atan2, cos, radians, sin, sqrt
from time import monotonic

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)
OVERPASS_ENDPOINTS = (
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
OVERPASS_REQUEST_TIMEOUTS = (12.0, 8.0, 8.0)
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
NOMINATIM_SEARCH_TERMS = {
    "clinic": ("clinic", "hospital"),
    "store": ("pharmacy", "beauty"),
}
NOMINATIM_REQUEST_INTERVAL = 1.1
NOMINATIM_CACHE_SECONDS = 300
MAX_RESULTS = 5
_nominatim_request_lock = asyncio.Lock()
_nominatim_last_request = 0.0
_nominatim_cache = {}


def get_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance between two coordinates in kilometers."""
    earth_radius_km = 6371
    lat_distance = radians(lat2 - lat1)
    lng_distance = radians(lng2 - lng1)
    haversine = (
        sin(lat_distance / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(lng_distance / 2) ** 2
    )
    return earth_radius_km * 2 * atan2(sqrt(haversine), sqrt(1 - haversine))


async def get_nominatim_places(lat: float, lng: float, radius_km: int, type_filter: str):
    """Search Nominatim as a rate-limited fallback when Overpass is unavailable."""
    global _nominatim_last_request

    cache_key = (round(lat, 4), round(lng, 4), radius_km, type_filter)
    cached = _nominatim_cache.get(cache_key)
    if cached and monotonic() - cached[0] < NOMINATIM_CACHE_SECONDS:
        return cached[1]

    latitude_delta = radius_km / 110.574
    longitude_delta = radius_km / (111.320 * max(cos(radians(lat)), 0.01))
    viewbox = ",".join(str(value) for value in (
        max(-180, lng - longitude_delta),
        min(90, lat + latitude_delta),
        min(180, lng + longitude_delta),
        max(-90, lat - latitude_delta),
    ))
    search_terms = []
    if type_filter in {"all", "clinic"}:
        search_terms.extend(NOMINATIM_SEARCH_TERMS["clinic"])
    if type_filter in {"all", "store"}:
        search_terms.extend(NOMINATIM_SEARCH_TERMS["store"])

    results = []
    seen = set()
    async with httpx.AsyncClient(
        headers={"User-Agent": "SkinSight/2.0 nearby-care map"},
    ) as client:
        for term in search_terms:
            async with _nominatim_request_lock:
                wait_seconds = NOMINATIM_REQUEST_INTERVAL - (monotonic() - _nominatim_last_request)
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                _nominatim_last_request = monotonic()
                response = await client.get(
                    NOMINATIM_ENDPOINT,
                    params={
                        "format": "jsonv2",
                        "q": term,
                        "viewbox": viewbox,
                        "bounded": 1,
                        "limit": 20,
                        "addressdetails": 1,
                        "extratags": 1,
                    },
                    timeout=httpx.Timeout(10.0, connect=5.0),
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Nominatim returned an invalid response")

            for element in payload:
                if not isinstance(element, dict):
                    continue
                osm_type = element.get("osm_type")
                osm_id = element.get("osm_id")
                key = (osm_type, osm_id)
                if osm_type not in {"node", "way", "relation"} or osm_id is None or key in seen:
                    continue
                seen.add(key)
                results.append(element)

    _nominatim_cache[cache_key] = (monotonic(), results)
    expired_keys = [
        key for key, (cached_at, _) in _nominatim_cache.items()
        if monotonic() - cached_at >= NOMINATIM_CACHE_SECONDS
    ]
    for key in expired_keys:
        _nominatim_cache.pop(key, None)
    if len(_nominatim_cache) > 256:
        _nominatim_cache.pop(next(iter(_nominatim_cache)))
    return results


@router.get("/nearby", response_model=dict)
async def get_nearby_places(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude"),
    radius_km: int = Query(5, description="Search radius in km"),
    type_filter: str = Query("all", description="Filter by 'clinic', 'store', or 'all'"),
):
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")
    if type_filter not in {"all", "clinic", "store"}:
        raise HTTPException(status_code=400, detail="Invalid type_filter")
    if not 1 <= radius_km <= 5:
        raise HTTPException(status_code=400, detail="radius_km must be between 1 and 5")

    queries = []
    radius_meters = radius_km * 1000
    if type_filter in {"all", "store"}:
        queries.append(f"""
          nwr(around:{radius_meters},{lat},{lng})["shop"~"^(beauty|chemist|cosmetics|health_food|pharmacy)$"];
          nwr(around:{radius_meters},{lat},{lng})["amenity"="pharmacy"];
          nwr(around:{radius_meters},{lat},{lng})["healthcare"="pharmacy"];
        """)
    if type_filter in {"all", "clinic"}:
        queries.append(f"""
          nwr(around:{radius_meters},{lat},{lng})["amenity"~"^(clinic|hospital|doctors)$"];
          nwr(around:{radius_meters},{lat},{lng})["healthcare"~"^(clinic|hospital|doctor)$"];
        """)
    overpass_query = f"[out:json][timeout:10];({''.join(queries)});out center tags;"

    elements = None
    last_error = None
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        headers={"User-Agent": "SkinSight/2.0 nearby-care map"},
    ) as client:
        for endpoint, timeout_seconds in zip(
            OVERPASS_ENDPOINTS,
            OVERPASS_REQUEST_TIMEOUTS,
        ):
            try:
                response = await client.post(
                    endpoint,
                    data={"data": overpass_query},
                    timeout=httpx.Timeout(timeout_seconds, connect=5.0),
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                    raise ValueError("Overpass returned an invalid response")
                elements = payload["elements"]
                break
            except Exception as exc:
                last_error = exc
                logger.warning("OpenStreetMap provider %s failed: %s", endpoint, exc)

    data_source = "openstreetmap"
    if elements is None:
        logger.warning("All Overpass providers failed; trying Nominatim")
        try:
            elements = await get_nominatim_places(
                lat,
                lng,
                radius_km,
                type_filter,
            )
            data_source = "openstreetmap-nominatim"
        except Exception as exc:
            logger.warning("Nominatim nearby search failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="OpenStreetMap search providers are temporarily unavailable or slow. Please retry shortly.",
                headers={"Retry-After": "30"},
            ) from exc

    clinics = []
    stores = []
    seen = set()
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            tags = {}
        is_nominatim = data_source == "openstreetmap-nominatim"
        point = element if is_nominatim else element.get("center", element)
        if not isinstance(point, dict):
            continue
        element_lat = point.get("lat")
        element_lng = point.get("lon")
        if is_nominatim:
            category = element.get("category")
            osm_place_type = element.get("type")
            is_clinic = (
                category in {"amenity", "healthcare"}
                and osm_place_type in {"clinic", "hospital", "doctor", "doctors"}
            )
            is_store = (
                category in {"amenity", "healthcare"} and osm_place_type == "pharmacy"
            ) or (
                category == "shop"
                and osm_place_type in {"beauty", "chemist", "cosmetics", "health_food", "pharmacy"}
            )
            if not is_clinic and not is_store:
                continue
            place_type = "clinic" if is_clinic else "store"
            tags = element.get("extratags", {})
            if not isinstance(tags, dict):
                tags = {}
        else:
            is_clinic = (
                tags.get("amenity") in {"clinic", "hospital", "doctors"}
                or tags.get("healthcare") in {"clinic", "hospital", "doctor"}
            )
            place_type = "clinic" if is_clinic else "store"
        if element_lat is None or element_lng is None:
            continue
        try:
            element_lat = float(element_lat)
            element_lng = float(element_lng)
        except (TypeError, ValueError):
            continue
        if not (-90 <= element_lat <= 90) or not (-180 <= element_lng <= 180):
            continue

        distance_km = get_distance(lat, lng, element_lat, element_lng)
        if distance_km >= radius_km:
            continue

        key = (
            place_type,
            element.get("osm_type") if is_nominatim else element.get("type"),
            element.get("osm_id") if is_nominatim else element.get("id"),
        )
        if key in seen:
            continue
        seen.add(key)

        address = element.get("display_name") if is_nominatim else None
        if not address:
            address_parts = [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:city") or tags.get("addr:town"),
            ]
            address = ", ".join(part for part in address_parts if part) or tags.get(
                "addr:full",
                "Address unavailable",
            )
        osm_type = element.get("osm_type") if is_nominatim else element.get("type")
        osm_id = element.get("osm_id") if is_nominatim else element.get("id")
        place = {
            "name": element.get("name") or tags.get("name") or (
                "Clinic or hospital" if is_clinic else "Skincare shop or pharmacy"
            ),
            "lat": element_lat,
            "lng": element_lng,
            "type": place_type,
            "desc": tags.get("description") or (
                "Clinic or hospital listed on OpenStreetMap."
                if is_clinic
                else "Skincare shop or pharmacy listed on OpenStreetMap."
            ),
            "distance_km": round(distance_km, 2),
            "address": address,
            "phone": tags.get("phone") or tags.get("contact:phone", "Phone unavailable"),
            "osm_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        }
        (clinics if is_clinic else stores).append(place)

    clinics.sort(key=lambda item: get_distance(lat, lng, item["lat"], item["lng"]))
    stores.sort(key=lambda item: get_distance(lat, lng, item["lat"], item["lng"]))
    return {
        "user_location": {"lat": lat, "lng": lng},
        "search_radius_km": radius_km,
        "data_source": data_source,
        "clinics": clinics[:MAX_RESULTS],
        "stores": stores[:MAX_RESULTS],
        "total_clinics": len(clinics),
        "total_stores": len(stores),
    }
