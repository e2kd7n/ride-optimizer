"""
Tests for cron/log_triage.py (#550) — parsing, clustering, fingerprinting,
and severity/label selection for the weekly error-log triage job.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cron import log_triage


def _line(ts, logger, level, message):
    return f"{ts} - {logger} - {level} - {message}"


class TestNormalizeAndFingerprint:
    def test_strips_volatile_numbers(self):
        a = log_triage.normalize_message("Failed after 12.345 seconds (attempt 3)")
        b = log_triage.normalize_message("Failed after 98.1 seconds (attempt 7)")
        assert a == b

    def test_strips_uuids(self):
        a = log_triage.normalize_message("request 123e4567-e89b-12d3-a456-426614174000 failed")
        b = log_triage.normalize_message("request 00000000-0000-0000-0000-000000000000 failed")
        assert a == b

    def test_different_messages_produce_different_fingerprints(self):
        fp1 = log_triage.compute_fingerprint("cron.daily_analysis", "error at line <n>")
        fp2 = log_triage.compute_fingerprint("cron.daily_analysis", "error at line <n>!")
        assert fp1 != fp2

    def test_same_key_produces_stable_fingerprint(self):
        fp1 = log_triage.compute_fingerprint("cron.x", "same message")
        fp2 = log_triage.compute_fingerprint("cron.x", "same message")
        assert fp1 == fp2


class TestParseEntries:
    def test_parses_matching_lines_within_lookback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_triage, "LOG_DIR", tmp_path)
        now = datetime.now()
        recent = now.strftime("%Y-%m-%d %H:%M:%S")
        (tmp_path / "cron_system_health.log").write_text(
            _line(recent, "cron.system_health", "ERROR", "Failed to check disk space: boom") + "\n"
            "not a log line, should be ignored\n"
            + _line(recent, "cron.system_health", "INFO", "healthy, should be ignored") + "\n"
        )
        entries = log_triage.parse_entries(now - timedelta(days=7))
        assert len(entries) == 1
        assert entries[0]["level"] == "ERROR"
        assert entries[0]["logger"] == "cron.system_health"

    def test_excludes_lines_before_cutoff(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_triage, "LOG_DIR", tmp_path)
        now = datetime.now()
        old = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        (tmp_path / "cron_system_health.log").write_text(
            _line(old, "cron.system_health", "ERROR", "stale error") + "\n"
        )
        entries = log_triage.parse_entries(now - timedelta(days=7))
        assert entries == []

    def test_ignores_aggregate_cron_log(self, tmp_path, monkeypatch):
        # cron.log duplicates every per-job log line (see module docstring) —
        # it must not be scanned or occurrence counts double.
        monkeypatch.setattr(log_triage, "LOG_DIR", tmp_path)
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        (tmp_path / "cron.log").write_text(
            _line(ts, "cron.system_health", "ERROR", "should not be counted") + "\n"
        )
        entries = log_triage.parse_entries(now - timedelta(days=7))
        assert entries == []

    def test_sanitizes_pii_in_message(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_triage, "LOG_DIR", tmp_path)
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        (tmp_path / "cron_daily_analysis.log").write_text(
            _line(ts, "cron.daily_analysis", "ERROR", "failed near 41.878123, -87.629812") + "\n"
        )
        entries = log_triage.parse_entries(now - timedelta(days=7))
        assert "41.878123" not in entries[0]["message"]


class TestCluster:
    def _entries(self, count, level="ERROR", logger="cron.x", message="boom", start=None):
        start = start or datetime.now()
        return [
            {
                "timestamp": start + timedelta(minutes=i),
                "logger": logger,
                "level": level,
                "message": message,
                "source_file": "cron_x.log",
            }
            for i in range(count)
        ]

    def test_below_min_occurrences_is_dropped(self):
        candidates = log_triage.cluster(self._entries(2, level="ERROR"))
        assert candidates == []

    def test_meets_min_occurrences_is_kept(self):
        candidates = log_triage.cluster(self._entries(3, level="ERROR"))
        assert len(candidates) == 1
        assert candidates[0]["occurrences"] == 3

    def test_critical_single_occurrence_is_kept(self):
        candidates = log_triage.cluster(self._entries(1, level="CRITICAL"))
        assert len(candidates) == 1

    def test_distinct_loggers_do_not_merge(self):
        entries = self._entries(3, logger="cron.a") + self._entries(3, logger="cron.b")
        candidates = log_triage.cluster(entries)
        assert len(candidates) == 2

    def test_first_and_last_seen_span_the_cluster(self):
        start = datetime(2026, 1, 1, 0, 0, 0)
        candidates = log_triage.cluster(self._entries(3, start=start))
        assert candidates[0]["first_seen"] == start.isoformat()
        assert candidates[0]["last_seen"] == (start + timedelta(minutes=2)).isoformat()


class TestSeverityAndOutput:
    def _candidate(self, level="ERROR", occurrences=3):
        return {
            "fingerprint": "abc123",
            "level": level,
            "logger": "cron.x",
            "occurrences": occurrences,
            "first_seen": "2026-01-01T00:00:00",
            "last_seen": "2026-01-01T00:10:00",
            "excerpt": "boom",
            "source_file": "cron_x.log",
        }

    def test_error_below_ten_is_p2(self):
        assert log_triage.severity_for(self._candidate(level="ERROR", occurrences=5)) == "P2-medium"

    def test_error_at_or_above_ten_is_p1(self):
        assert log_triage.severity_for(self._candidate(level="ERROR", occurrences=10)) == "P1-high"

    def test_warning_is_p3(self):
        assert log_triage.severity_for(self._candidate(level="WARNING", occurrences=50)) == "P3-low"

    def test_build_output_embeds_fingerprint_marker(self):
        output = log_triage.build_output(self._candidate())
        assert "<!-- auto-log-triage:fingerprint=abc123 -->" in output["body"]
        assert output["labels"] == ["bug", "P2-medium", "auto-log-triage"]

    def test_main_emits_one_json_line_per_candidate(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(log_triage, "LOG_DIR", tmp_path)
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        lines = "\n".join(
            _line(ts, "cron.system_health", "ERROR", "disk check failed") for _ in range(3)
        )
        (tmp_path / "cron_system_health.log").write_text(lines + "\n")

        assert log_triage.main() == 0
        out_lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
        assert len(out_lines) == 1
        parsed = json.loads(out_lines[0])
        assert parsed["occurrences"] == 3
        assert "auto-log-triage" in parsed["labels"]
