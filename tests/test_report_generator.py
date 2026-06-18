"""
Unit tests for report_generator module.
"""
import json
import csv
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from xml.etree import ElementTree as ET

from src.report_generator import ReportGenerator


def _make_config(unit_system='metric'):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'units.system': unit_system,
    }.get(key, default)
    return config


def _make_route(activity_id=1, name="Test Route", distance=5000.0,
                duration=1200, timestamp="2024-01-01T08:00:00"):
    route = Mock()
    route.activity_id = activity_id
    route.activity_name = name
    route.distance = distance
    route.duration = duration
    route.timestamp = timestamp
    return route


def _make_group(group_id="route_1", direction="home_to_work", frequency=5,
                coordinates=None, routes=None):
    group = Mock()
    group.id = group_id
    group.direction = direction
    group.frequency = frequency
    group.is_plus_route = False
    group.name = "Test Route Group"
    rep = Mock()
    rep.coordinates = coordinates or [(40.71, -74.00), (40.75, -73.98)]
    group.representative_route = rep
    group.routes = routes or [_make_route(i) for i in range(frequency)]
    return group


def _make_metrics(avg_duration=1200.0, avg_distance=5000.0, avg_speed=4.17,
                  avg_elevation=50.0):
    m = Mock()
    m.avg_duration = avg_duration
    m.avg_distance = avg_distance
    m.avg_speed = avg_speed
    m.avg_elevation = avg_elevation
    return m


def _minimal_results(**overrides):
    results = {
        'config': _make_config(),
        'ranked_routes': [],
        'statistics': {},
        'recommendations': {},
    }
    results.update(overrides)
    return results


class TestSanitizeActivityName:
    def test_removes_template_injection(self):
        assert ReportGenerator._sanitize_activity_name("Hello {{world}}") == "Hello world"

    def test_removes_angle_brackets(self):
        assert "<script>" not in ReportGenerator._sanitize_activity_name("<script>alert(1)</script>")

    def test_removes_bracketed_pii(self):
        result = ReportGenerator._sanitize_activity_name("Commute to [Acme Corp]")
        assert "Acme Corp" not in result

    def test_removes_parenthesized_pii(self):
        result = ReportGenerator._sanitize_activity_name("Ride (with John)")
        assert "John" not in result

    def test_truncates_long_names(self):
        long_name = "A" * 200
        result = ReportGenerator._sanitize_activity_name(long_name)
        assert len(result) <= 100

    def test_empty_name_returns_unnamed(self):
        assert ReportGenerator._sanitize_activity_name("") == "Unnamed Activity"
        assert ReportGenerator._sanitize_activity_name(None) == "Unnamed Activity"


class TestRouteToDict:
    def test_converts_route_fields(self):
        rg = ReportGenerator(_minimal_results())
        route = _make_route(activity_id=42, name="Morning Ride",
                            distance=10000.0, duration=2400,
                            timestamp="2024-06-15T07:30:00")
        result = rg._route_to_dict(route)
        assert result['id'] == 42
        assert result['name'] == "Morning Ride"
        assert result['distance'] == 10000.0
        assert result['moving_time'] == 2400
        assert result['start_date'] == "2024-06-15T07:30:00"


class TestPreparePdfHtml:
    def test_removes_onclick(self):
        rg = ReportGenerator(_minimal_results())
        html = '<button onclick="refreshReport()">Refresh</button>'
        result = rg._prepare_pdf_html(html)
        assert 'onclick' not in result

    def test_adds_pdf_styles(self):
        rg = ReportGenerator(_minimal_results())
        html = '<html><head></head><body>Test</body></html>'
        result = rg._prepare_pdf_html(html)
        assert '@page' in result
        assert 'A4' in result


class TestExportJson:
    def test_exports_valid_json(self, tmp_path):
        optimizer = Mock()
        optimizer.metrics = {"r1": _make_metrics()}

        group = _make_group("r1")
        results = _minimal_results(
            ranked_routes=[(group, 85.0, {'time': 90, 'distance': 80})],
            optimizer=optimizer,
        )
        rg = ReportGenerator(results)
        out = tmp_path / "routes.json"
        rg._export_json(str(out))

        data = json.loads(out.read_text())
        assert 'routes' in data
        assert len(data['routes']) == 1
        assert data['routes'][0]['id'] == 'r1'
        assert data['routes'][0]['score'] == 85.0


class TestExportCsv:
    def test_exports_valid_csv(self, tmp_path):
        optimizer = Mock()
        optimizer.metrics = {"r1": _make_metrics()}

        group = _make_group("r1")
        results = _minimal_results(
            ranked_routes=[(group, 85.0, {'weather': 60, 'safety': 70, 'efficiency': 80})],
            optimizer=optimizer,
        )
        rg = ReportGenerator(results)
        out = tmp_path / "routes.csv"
        rg._export_csv(str(out))

        with open(out) as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2  # header + 1 data row
        assert rows[0][0] == 'Route ID'


class TestExportGpx:
    def test_exports_valid_gpx(self, tmp_path):
        group = _make_group("r1", coordinates=[(40.71, -74.00), (40.72, -73.99)])
        results = _minimal_results(
            ranked_routes=[(group, 85.0, {})],
        )
        rg = ReportGenerator(results)
        out = tmp_path / "routes.gpx"
        rg._export_gpx(str(out))

        tree = ET.parse(str(out))
        root = tree.getroot()
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        routes = root.findall('gpx:rte', ns)
        assert len(routes) == 1
        points = routes[0].findall('gpx:rtept', ns)
        assert len(points) == 2

    def test_skips_group_without_coordinates(self, tmp_path):
        group = _make_group("r1")
        group.representative_route = None
        results = _minimal_results(
            ranked_routes=[(group, 85.0, {})],
        )
        rg = ReportGenerator(results)
        out = tmp_path / "routes.gpx"
        rg._export_gpx(str(out))

        tree = ET.parse(str(out))
        root = tree.getroot()
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        assert len(root.findall('gpx:rte', ns)) == 0


class TestExportData:
    def test_creates_all_three_formats(self, tmp_path):
        optimizer = Mock()
        optimizer.metrics = {"r1": _make_metrics()}
        group = _make_group("r1")
        results = _minimal_results(
            ranked_routes=[(group, 85.0, {'weather': 60, 'safety': 70, 'efficiency': 80})],
            optimizer=optimizer,
        )
        rg = ReportGenerator(results)
        base = str(tmp_path / "export")
        rg.export_data(base)

        assert (tmp_path / "export_routes.json").exists()
        assert (tmp_path / "export_routes.csv").exists()
        assert (tmp_path / "export_routes.gpx").exists()
