from datetime import datetime, timezone

from app.services.siem_engine import (
    LogEvent,
    analyze_events,
    parse_access_log,
)


def test_parser_accepts_nginx_and_apache_combined_and_decodes_url() -> None:
    text = (
        '198.51.100.7 - - [20/Jun/2026:22:10:00 +0000] '
        '"GET /search?q=%27%20OR%201%3D1-- HTTP/1.1" 200 42 '
        '"-" "pytest"\n'
        '203.0.113.8 - bob [20/Jun/2026:22:11:00 +0000] '
        '"POST /auth/login HTTP/1.1" 401 12 "-" "curl"'
    )

    events = parse_access_log(text)

    assert len(events) == 2
    assert events[0].ip == "198.51.100.7"
    assert "' OR 1=1--" in events[0].path
    assert events[1].method == "POST"
    assert events[1].status == 401


def test_parser_skips_invalid_timestamp_and_continues() -> None:
    text = (
        '198.51.100.5 - - [not-a-date] '
        '"GET /broken HTTP/1.1" 200 12 "-" "pytest"\n'
        '198.51.100.6 - - [20/Jun/2026:22:12:00 +0000] '
        '"GET /valid HTTP/1.1" 200 13 "-" "pytest"'
    )

    events = parse_access_log(text)

    assert len(events) == 1
    assert events[0].ip == "198.51.100.6"
    assert events[0].path == "/valid"


def test_engine_detects_sqli_bruteforce_and_enumeration_grouped_by_ip() -> None:
    now = datetime(2026, 6, 20, 22, 0, tzinfo=timezone.utc)
    events = [
        LogEvent("198.51.100.1", now, "GET", "/?q=UNION%20SELECT", 200),
        *[
            LogEvent("198.51.100.2", now, "POST", "/auth/login", 401)
            for _ in range(4)
        ],
        *[
            LogEvent("198.51.100.3", now, "GET", f"/missing/{i}", 404)
            for i in range(4)
        ],
    ]

    result = analyze_events(
        events,
        brute_force_threshold=3,
        enumeration_threshold=3,
        window_seconds=60,
    )

    assert {item["type"] for item in result.events} == {
        "sql_injection",
        "brute_force",
        "enumeration_404",
    }
    brute = next(item for item in result.events if item["type"] == "brute_force")
    assert brute["ip"] == "198.51.100.2"
    assert brute["frequency"] == 4
    assert brute["severity"] == "high"
    assert result.summary["top_suspicious_ips"][0]["count"] >= 4


def test_detections_sort_by_severity_before_frequency() -> None:
    now = datetime(2026, 6, 20, 22, 0, tzinfo=timezone.utc)
    events = [
        LogEvent("198.51.100.1", now, "GET", "/?q=' OR 1=1--", 200),
        *[
            LogEvent("198.51.100.2", now, "GET", f"/missing/{i}", 404)
            for i in range(6)
        ],
    ]

    result = analyze_events(
        events,
        brute_force_threshold=3,
        enumeration_threshold=3,
        window_seconds=60,
    )

    assert [
        (item["severity"], item["frequency"], item["ip"], item["type"])
        for item in result.events
    ] == [
        ("high", 1, "198.51.100.1", "sql_injection"),
        ("medium", 6, "198.51.100.2", "enumeration_404"),
    ]
