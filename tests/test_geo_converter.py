"""Unit tests for Geographical Coordinate Converter."""

import pytest
from backend.intelligent_control.geo_converter import (
    GeoPoint,
    GeoCoordinateConverter,
    haversine_distance_m,
    initial_bearing_deg,
)


def test_geopoint_and_haversine():
    # New Delhi to Bengaluru
    delhi = GeoPoint(lat=28.6139, lon=77.2090)
    bengaluru = GeoPoint(lat=12.9716, lon=77.5946)

    dist = haversine_distance_m(delhi, bengaluru)
    # Approximate straight line distance ~1740 km
    assert 1700_000 < dist < 1780_000

    brng = initial_bearing_deg(delhi, bengaluru)
    # Heading south-south-east (~175-185 degrees)
    assert 170.0 < brng < 190.0


def test_roundtrip_gps_to_enu():
    # Kaziranga National Park reference
    origin = GeoPoint(lat=26.5775, lon=93.1711, alt=12.0)
    converter = GeoCoordinateConverter(origin_gps=origin, scale_factor=1.0)

    # Convert origin
    x0, y0, z0 = converter.gps_to_enu(origin)
    assert pytest.approx(x0, abs=1e-3) == 0.0
    assert pytest.approx(y0, abs=1e-3) == 0.0
    assert pytest.approx(z0, abs=1e-3) == 12.0

    # Convert nearby point (~500m north, ~300m east)
    test_pt = GeoPoint(lat=26.5820, lon=93.1741, alt=15.0)
    x, y, z = converter.gps_to_enu(test_pt)

    assert x > 0.0
    assert y > 0.0
    assert z == 15.0

    # Invert back to GPS
    recovered_gps = converter.enu_to_gps(x, y, z)
    assert pytest.approx(recovered_gps.lat, abs=1e-5) == test_pt.lat
    assert pytest.approx(recovered_gps.lon, abs=1e-5) == test_pt.lon
    assert pytest.approx(recovered_gps.alt, abs=1e-2) == test_pt.alt


def test_fit_converter():
    pts = [
        GeoPoint(lat=20.0, lon=78.0),
        GeoPoint(lat=20.1, lon=78.1),
        GeoPoint(lat=20.2, lon=78.2),
    ]
    conv, ox, oy, w, h = GeoCoordinateConverter.fit_converter_for_route(pts, target_grid_size=100.0)
    assert conv is not None
    assert w > 0
    assert h > 0
