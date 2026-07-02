from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import unquote

COMBINED_LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[^"]+"\s+'
    r"(?P<status>\d{3})\s+\S+"
)
SQLI_PATTERN = re.compile(
    r"(?:'\s*(?:or|and)\b|union\s+(?:all\s+)?select\b|--|/\*|\bdrop\s+table\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LogEvent:
    ip: str
    timestamp: datetime
    method: str
    path: str
    status: int


@dataclass(frozen=True)
class AnalysisResult:
    summary: dict
    events: list[dict]


def parse_access_log(text: str) -> list[LogEvent]:
    events: list[LogEvent] = []
    for line in text.splitlines():
        match = COMBINED_LOG_PATTERN.match(line.strip())
        if not match:
            continue
        try:
            timestamp = datetime.strptime(
                match.group("timestamp"), "%d/%b/%Y:%H:%M:%S %z"
            )
        except ValueError:
            continue
        events.append(
            LogEvent(
                ip=match.group("ip")[:45],
                timestamp=timestamp,
                method=match.group("method"),
                path=unquote(match.group("path")),
                status=int(match.group("status")),
            )
        )
    return events


def _max_frequency_in_window(
    events: list[LogEvent], window_seconds: int
) -> int:
    ordered = sorted(events, key=lambda event: event.timestamp)
    start = 0
    maximum = 0
    for end, event in enumerate(ordered):
        while (
            event.timestamp - ordered[start].timestamp
        ).total_seconds() > window_seconds:
            start += 1
        maximum = max(maximum, end - start + 1)
    return maximum


def analyze_events(
    source_events: Iterable[LogEvent],
    *,
    brute_force_threshold: int,
    enumeration_threshold: int,
    window_seconds: int,
) -> AnalysisResult:
    events = list(source_events)
    detections: list[dict] = []
    suspicious_counts: Counter[str] = Counter()

    sqli_by_ip: dict[str, list[LogEvent]] = defaultdict(list)
    brute_by_ip: dict[str, list[LogEvent]] = defaultdict(list)
    missing_by_ip: dict[str, list[LogEvent]] = defaultdict(list)
    for event in events:
        if SQLI_PATTERN.search(unquote(event.path)):
            sqli_by_ip[event.ip].append(event)
        if event.method == "POST" and event.path.split("?", 1)[0].rstrip("/") == "/auth/login":
            brute_by_ip[event.ip].append(event)
        if event.status == 404:
            missing_by_ip[event.ip].append(event)

    for ip, matches in sqli_by_ip.items():
        frequency = len(matches)
        suspicious_counts[ip] += frequency
        detections.append(
            {
                "type": "sql_injection",
                "ip": ip,
                "severity": "high",
                "frequency": frequency,
            }
        )
    for ip, matches in brute_by_ip.items():
        frequency = _max_frequency_in_window(matches, window_seconds)
        if frequency > brute_force_threshold:
            suspicious_counts[ip] += frequency
            detections.append(
                {
                    "type": "brute_force",
                    "ip": ip,
                    "severity": "high",
                    "frequency": frequency,
                }
            )
    for ip, matches in missing_by_ip.items():
        frequency = _max_frequency_in_window(matches, window_seconds)
        if frequency > enumeration_threshold:
            suspicious_counts[ip] += frequency
            detections.append(
                {
                    "type": "enumeration_404",
                    "ip": ip,
                    "severity": "medium",
                    "frequency": frequency,
                }
            )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    detections.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 3),
            -item["frequency"],
            item["ip"],
            item["type"],
        )
    )
    return AnalysisResult(
        summary={
            "total_events": len(events),
            "detections": len(detections),
            "top_suspicious_ips": [
                {"ip": ip, "count": count}
                for ip, count in suspicious_counts.most_common(5)
            ],
        },
        events=detections,
    )
