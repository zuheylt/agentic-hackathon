"""Terminal logging utilities with ASCII separators."""

import sys


SEPARATOR = "=" * 60
THIN_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title.upper()}")
    print(SEPARATOR)


def subsection(title: str) -> None:
    print(f"\n{THIN_SEP}")
    print(f"  >> {title}")
    print(THIN_SEP)


def log(label: str, message: str) -> None:
    print(f"  [{label}] {message}")


def result(label: str, value: str) -> None:
    print(f"  [{label}] => {value}")


def vote_line(agent: str, approved: bool, confidence: float, reason: str) -> None:
    verdict = "APPROVED ✓" if approved else "REJECTED ✗"
    print(f"  [{agent}] {verdict}  (confidence: {confidence:.0%})")
    print(f"           Reason: {reason}")


def decision_banner(status: str, consensus: bool) -> None:
    print(f"\n{SEPARATOR}")
    if consensus:
        print(f"  FINAL DECISION: {status}")
    else:
        print(f"  FINAL DECISION: {status}  (no consensus)")
    print(SEPARATOR)
