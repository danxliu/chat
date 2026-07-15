"""Geolocation tools powered by OpenRouteService (OpenStreetMap data).

Requires ORS_API_KEY in .env — sign up free at https://openrouteservice.org
"""

import logging
from typing import Literal

import openrouteservice

from config import settings

# Profile type shared by get_directions and distance_matrix
DirectionsProfile = Literal[
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "cycling-road",
    "cycling-mountain",
    "cycling-electric",
    "foot-walking",
    "foot-hiking",
    "wheelchair",
]

# Distance matrix API supports a narrower set of profiles
MatrixProfile = Literal[
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
]

# POI category names mapped to ORS category group IDs (see CATEGORY_MAP below)
Category = Literal[
    "restaurant",
    "cafe",
    "hotel",
    "hospital",
    "pharmacy",
    "bank",
    "atm",
    "parking",
    "park",
    "museum",
    "shopping",
    "school",
    "sport",
    "sights",
    "accommodation",
    "religious",
    "church",
    "temple",
    "food",
    "bar",
    "leisure",
    "entertainment",
    "gym",
    "natural",
    "transport",
    "services",
    "shop",
    "education",
    "university",
    "financial",
    "public",
    "healthcare",
    "tourism",
    "attraction",
]

logger = logging.getLogger(__name__)

# Map user-friendly category names to ORS category group IDs
CATEGORY_MAP: dict[str, int] = {
    "sights": 100,
    "museum": 100,
    "accommodation": 120,
    "hotel": 120,
    "religious": 130,
    "church": 130,
    "temple": 130,
    "food": 150,
    "restaurant": 150,
    "cafe": 150,
    "bar": 150,
    "leisure": 160,
    "entertainment": 160,
    "sport": 190,
    "gym": 190,
    "natural": 200,
    "park": 200,
    "transport": 220,
    "parking": 220,
    "services": 260,
    "shopping": 330,
    "shop": 330,
    "education": 360,
    "school": 360,
    "university": 360,
    "financial": 390,
    "bank": 390,
    "atm": 390,
    "public": 420,
    "healthcare": 560,
    "hospital": 560,
    "pharmacy": 560,
    "tourism": 580,
    "attraction": 580,
}

# Travel profiles available for routing
VALID_PROFILES = {
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "cycling-road",
    "cycling-mountain",
    "cycling-electric",
    "foot-walking",
    "foot-hiking",
    "wheelchair",
}


def _get_client():
    """Return an ORS client, or None if no API key configured."""
    if not settings.ors_api_key:
        return None
    return openrouteservice.Client(key=settings.ors_api_key)


def _resolve_profile(profile: str) -> str:
    """Normalize a user-provided profile string to a valid ORS profile."""
    profile = profile.strip().lower()
    if profile in VALID_PROFILES:
        return profile
    # Fuzzy matching for common aliases
    aliases = {
        "driving": "driving-car",
        "car": "driving-car",
        "truck": "driving-hgv",
        "cycling": "cycling-regular",
        "bike": "cycling-regular",
        "bicycle": "cycling-regular",
        "walking": "foot-walking",
        "walk": "foot-walking",
        "hiking": "foot-hiking",
        "hike": "foot-hiking",
    }
    return aliases.get(profile, "driving-car")


def _resolve_category(category: str) -> int | None:
    """Convert a user-friendly category name to an ORS category_group_id."""
    return CATEGORY_MAP.get(category.strip().lower())


def search_location(query: str, country: str = "") -> str:
    """
    Find the geographic coordinates (latitude/longitude) of an address or place name.

    Use this to look up coordinates for any location before doing routing, distance
    calculations, or nearby searches. Returns one or more matching locations with
    coordinates and confidence scores.

    Args:
        query (str): The address or place name to search for (e.g., "Times Square, New York").
        country (str): Optional country code to narrow results (e.g., "DE", "US", "FR").
    """
    client = _get_client()
    if client is None:
        return "Error: ORS_API_KEY not configured. Add your free OpenRouteService API key to the .env file."

    try:
        params: dict = {"text": query, "size": 5}
        if country:
            params["country"] = country.upper()

        results = client.pelias_search(**params)

        features = results.get("features", [])
        if not features:
            return f"No locations found for '{query}'."

        lines = [f"### Search Results for '{query}':"]
        for feat in features[:5]:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [])
            label = props.get("label", props.get("name", "Unknown"))
            confidence = props.get("confidence", 0)
            if coords:
                lines.append(
                    f"- **{label}**\n"
                    f"  Coordinates: ({coords[1]:.5f}, {coords[0]:.5f}) — "
                    f"confidence: {confidence:.0%}"
                )

        return "\n".join(lines)

    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"ORS geocoding error: {e}")
        return f"Error: OpenRouteService API error — {e}"
    except Exception as e:
        logger.exception("Unexpected geocoding error")
        return f"Error during geocoding: {e}"


def reverse_geocode(lat: float, lon: float) -> str:
    """
    Convert geographic coordinates (latitude, longitude) to a human-readable address.

    Use this to find what's at a specific location — for example, after getting
    coordinates from another tool or when the user provides raw coordinates.

    Args:
        lat (float): Latitude (e.g., 40.7580).
        lon (float): Longitude (e.g., -73.9855).
    """
    client = _get_client()
    if client is None:
        return "Error: ORS_API_KEY not configured. Add your free OpenRouteService API key to the .env file."

    try:
        results = client.pelias_reverse(point=(lon, lat), size=3)

        features = results.get("features", [])
        if not features:
            return f"No address found for coordinates ({lat}, {lon})."

        lines = [f"### Reverse Geocode for ({lat}, {lon}):"]
        for feat in features[:3]:
            props = feat.get("properties", {})
            label = props.get("label", "Unknown location")
            layer = props.get("layer", "unknown")
            lines.append(f"- **{label}** (type: {layer})")

        return "\n".join(lines)

    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"ORS reverse geocoding error: {e}")
        return f"Error: OpenRouteService API error — {e}"
    except Exception as e:
        logger.exception("Unexpected reverse geocoding error")
        return f"Error during reverse geocoding: {e}"


def get_directions(
    origin: str,
    destination: str,
    profile: DirectionsProfile = "driving-car",
) -> str:
    """
    Get the distance and travel time between two locations.

    Use this when asked about distance, travel time, or directions between places.
    Accepts both addresses (which will be geocoded first) and coordinate strings.
    Returns a human-readable summary including distance, duration, and a step-by-step
    route description.

    Args:
        origin (str): Starting point — an address or "lon,lat" (e.g., "Berlin, Germany" or "13.38,52.52").
        destination (str): End point — an address or "lon,lat".
        profile (DirectionsProfile): Travel mode (see allowed values).
    """
    client = _get_client()
    if client is None:
        return "Error: ORS_API_KEY not configured. Add your free OpenRouteService API key to the .env file."

    profile = _resolve_profile(profile)

    try:
        # Parse origin — could be address or "lon,lat"
        origin_coords = _parse_coords_or_geocode(client, origin)
        dest_coords = _parse_coords_or_geocode(client, destination)

        if origin_coords is None:
            return f"Error: Could not resolve origin '{origin}' to coordinates."
        if dest_coords is None:
            return (
                f"Error: Could not resolve destination '{destination}' to coordinates."
            )

        routes = client.directions(
            coordinates=[origin_coords, dest_coords],
            profile=profile,
            format="json",
            instructions=True,
        )

        route_data = routes.get("routes", [])
        if not route_data:
            return f"No route found between '{origin}' and '{destination}' using {profile}."

        route = route_data[0]
        summary = route.get("summary", {})
        distance_km = summary.get("distance", 0) / 1000
        duration_min = summary.get("duration", 0) / 60

        lines = [
            f"### Route: {origin} → {destination}",
            f"- **Mode:** {profile}",
            f"- **Distance:** {distance_km:.2f} km ({distance_km * 0.621371:.2f} mi)",
            f"- **Duration:** {duration_min:.0f} min ({_format_duration(duration_min)})",
        ]

        # Include turn-by-turn summary (condensed)
        segments = route.get("segments", [])
        if segments:
            steps = segments[0].get("steps", [])
            if steps:
                lines.append("\n**Step-by-step:**")
                for i, step in enumerate(steps[:10], 1):
                    instruction = step.get("instruction", "")
                    step_dist = step.get("distance", 0)
                    step_dur = step.get("duration", 0)
                    lines.append(
                        f"{i}. {instruction} "
                        f"({step_dist:.0f}m, {step_dur / 60:.1f} min)"
                    )
                if len(steps) > 10:
                    lines.append(f"... and {len(steps) - 10} more steps")

        return "\n".join(lines)

    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"ORS directions error: {e}")
        return f"Error: OpenRouteService API error — {e}"
    except Exception as e:
        logger.exception("Unexpected directions error")
        return f"Error getting directions: {e}"


def search_nearby(
    lat: float,
    lon: float,
    radius: int = 500,
    category: Category = "restaurant",
) -> str:
    """
    Find points of interest near a given location using OpenStreetMap data.

    Use this when asked about what's nearby, such as "find restaurants near me"
    or "what hotels are close to this address". Returns a list of places with
    names and distances.

    Args:
        lat (float): Latitude of the search center.
        lon (float): Longitude of the search center.
        radius (int): Search radius in meters (default 500, max 2000).
        category (Category): Type of place (see allowed values).
    """
    client = _get_client()
    if client is None:
        return "Error: ORS_API_KEY not configured. Add your free OpenRouteService API key to the .env file."

    category_id = _resolve_category(category)
    if category_id is None:
        valid_cats = sorted(set(CATEGORY_MAP.keys()))
        return (
            f"Unknown category '{category}'. Valid categories: {', '.join(valid_cats)}"
        )

    radius = max(100, min(radius, 2000))  # Clamp 100m–2000m

    try:
        results = client.places(
            request="pois",
            geojson={
                "type": "Point",
                "coordinates": [lon, lat],
            },
            buffer=radius,
            filter_category_group_ids=[category_id],
            limit=10,
            sortby="distance",
        )

        features = results.get("features", [])
        if not features:
            return (
                f"No '{category}' found within {radius}m of ({lat}, {lon}). "
                f"Try a larger radius or a different category."
            )

        lines = [f"### Nearby '{category}' within {radius}m of ({lat}, {lon}):"]
        for feat in features[:10]:
            props = feat.get("properties", {})
            dist = props.get("distance", 0)
            name = props.get("name") or props.get("osm_tags", {}).get("name", "Unnamed")
            lines.append(f"- **{name}** — {dist:.0f}m away")

        return "\n".join(lines)

    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"ORS POI search error: {e}")
        return f"Error: OpenRouteService API error — {e}"
    except Exception as e:
        logger.exception("Unexpected POI search error")
        return f"Error searching nearby: {e}"


def distance_matrix(
    locations: str,
    profile: MatrixProfile = "driving-car",
) -> str:
    """
    Calculate travel durations and distances between multiple locations.

    Use this to compare travel times or find the nearest of several options.
    Accepts a semicolon-separated list of coordinates in "lon,lat" format.

    Args:
        locations (str): Semicolon-separated coordinates, e.g., "13.38,52.52;13.41,52.52;13.37,52.53".
        profile (MatrixProfile): Travel mode (see allowed values).
    """
    client = _get_client()
    if client is None:
        return "Error: ORS_API_KEY not configured. Add your free OpenRouteService API key to the .env file."

    profile = _resolve_profile(profile)

    try:
        # Parse location string
        coords: list[tuple[float, float]] = []
        for loc in locations.split(";"):
            loc = loc.strip()
            if not loc:
                continue
            parts = loc.split(",")
            if len(parts) >= 2:
                coords.append((float(parts[0].strip()), float(parts[1].strip())))

        if len(coords) < 2:
            return (
                "Error: At least 2 locations required. "
                "Provide semicolon-separated 'lon,lat' pairs."
            )

        result = client.distance_matrix(
            locations=coords,
            profile=profile,
            metrics=["duration", "distance"],
        )

        durations = result.get("durations", [])
        distances = result.get("distances", [])

        if not durations:
            return "Error: No matrix data returned."

        n = len(coords)
        label = [f"Loc {i + 1}" for i in range(n)]

        lines = [
            f"### Distance Matrix ({profile}, {n} locations)",
            "\n**Durations (minutes):**",
        ]
        lines.append("| From \\ To | " + " | ".join(label) + " |")
        lines.append("|" + "---|" * (n + 1))
        for i in range(n):
            row = [f"{d / 60:.0f}" if d else "—" for d in durations[i]]
            lines.append(f"| {label[i]} | " + " | ".join(row) + " |")

        if distances:
            lines.append("\n**Distances (km):**")
            lines.append("| From \\ To | " + " | ".join(label) + " |")
            lines.append("|" + "---|" * (n + 1))
            for i in range(n):
                row = [f"{d / 1000:.2f}" if d else "—" for d in distances[i]]
                lines.append(f"| {label[i]} | " + " | ".join(row) + " |")

        return "\n".join(lines)

    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"ORS matrix error: {e}")
        return f"Error: OpenRouteService API error — {e}"
    except Exception as e:
        logger.exception("Unexpected matrix error")
        return f"Error computing distance matrix: {e}"


# ── helpers ──────────────────────────────────────────────────────────────────


def _parse_coords_or_geocode(client, text: str) -> tuple[float, float] | None:
    """Parse text as 'lon,lat' or geocode it as an address. Returns (lon, lat)."""
    try:
        parts = text.split(",")
        if len(parts) == 2:
            lon = float(parts[0].strip())
            lat = float(parts[1].strip())
            if -180 <= lon <= 180 and -90 <= lat <= 90:
                return (lon, lat)
    except (ValueError, IndexError):
        pass

    # Fall back to geocoding
    r = client.pelias_search(text=text, size=1)
    features = r.get("features", [])
    if features:
        coords = features[0].get("geometry", {}).get("coordinates", [])
        if len(coords) == 2:
            return (coords[0], coords[1])
    return None


def _format_duration(minutes: float) -> str:
    """Format minutes as 'Xh Ym' or 'Ym'."""
    h = int(minutes // 60)
    m = int(minutes % 60)
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"
