#!/usr/bin/env python3
"""Run one repeatable, synthetic-only Stage 20 judging walkthrough against a local SkillScope API.

The API is unauthenticated in the prototype. By default this script refuses non-loopback hosts.
Do not use it with a publicly reachable server or with real student data.
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from typing import Any


def request_json(base_url: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 8.0) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(base_url.rstrip("/") + path, data=body, headers=headers, method="GET" if body is None else "POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            return json.loads(data.decode("utf-8")) if data else None
    except HTTPError as exc:
        detail = exc.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {exc.code} for {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach the local SkillScope API at {base_url}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="SkillScope API base URL (default localhost:8000)")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--allow-remote", action="store_true", help="Explicitly permit a non-loopback API host; discouraged because the demo API is unauthenticated")
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if not parsed.scheme in {"http", "https"} or not parsed.netloc:
        parser.error("--base-url must be an http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error("--base-url must not include credentials, query parameters, or fragments")
    host = (parsed.hostname or "").casefold()
    if host not in {"localhost", "127.0.0.1", "::1"} and not args.allow_remote:
        parser.error("Refusing a non-loopback host. Run locally or pass --allow-remote only after evaluating the risk.")
    try:
        status = request_json(args.base_url, "/api/system/persistence", timeout=args.timeout)
        if status.get("status") != "ready" or not status.get("persistent_store"):
            raise RuntimeError("Database is not ready. Run the documented database initialization command first.")
        fixtures = status.get("demo_fixtures", [])
        required_ages = {"10_14", "15_17", "18_plus"}
        if {item.get("age_band") for item in fixtures} != required_ages or len(fixtures) != 3:
            raise RuntimeError("Expected exactly three registered synthetic fixtures for 10–14, 15–17, and 18+.")
        if any(not item.get("synthetic") or item.get("data_classification") != "synthetic_demo" for item in fixtures):
            raise RuntimeError("A demo profile is not explicitly marked synthetic. Refusing to proceed.")
        teen = next(item for item in fixtures if item["age_band"] == "15_17")
        profile_id = teen["profile_id"]
        before = request_json(args.base_url, f"/api/discovery-loop/{profile_id}?preference=balanced", timeout=args.timeout)
        challenge_id = before["next_challenge"]["challenge_id"]
        challenge = request_json(args.base_url, f"/api/challenges/{challenge_id}", timeout=args.timeout)
        observations = [
            {
                "criterion_id": criterion["criterion_id"],
                "score": min(1, int(criterion.get("max_score", 2))),
                "observation": f"SYNTHETIC DEMO ONLY: visible example observation for {criterion['label']}.",
            }
            for criterion in challenge["rubric"]
        ]
        submission = request_json(args.base_url, f"/api/challenges/{challenge_id}/submissions", {
            "profile_id": profile_id,
            "output": "SYNTHETIC DEMO ONLY: example output created for the Stage 20 walkthrough. No real student work is represented.",
            "rubric_observations": observations,
            "enjoyment": 4,
            "difficulty_reported": 3,
            "confidence": 3,
            "willingness_to_continue": 4,
            "reflection": "SYNTHETIC DEMO ONLY: the example activity was interesting; a different activity should be tried next.",
            "hypothesis_interpretation": "contextual_or_mixed",
        }, timeout=args.timeout)
        after = request_json(args.base_url, f"/api/discovery-loop/{profile_id}?preference=balanced", timeout=args.timeout)
        if not submission.get("evidence_created_id"):
            raise RuntimeError("Challenge returned no linked evidence item.")
        if after["evidence_count"] != before["evidence_count"] + 1:
            raise RuntimeError("Evidence ledger count did not increase by exactly one.")
        if after["next_challenge"]["challenge_id"] == challenge_id:
            raise RuntimeError("The next step did not change after a completed activity.")
        output = {
            "notice": "SYNTHETIC DEMO ONLY — no real student or child data used.",
            "fixture_modes": [
                {"age_band": item["age_band"], "profile_id": item["profile_id"],
                 "evidence_count": item["evidence_count"], "challenge_submission_count": item["challenge_submission_count"]}
                for item in fixtures
            ],
            "selected_fixture": "synthetic age 15–17 explore-and-validate example",
            "mode": before["mode"],
            "current_goal": before.get("current_goal"),
            "challenge_completed": {"challenge_id": challenge_id, "title": next(v["title"] for v in challenge["age_variants"] if v["age_band"] == "15_17"),
                                    "evidence_status": submission["evidence_status"], "objective_score": submission["objective_score"]},
            "evidence_count_before": before["evidence_count"],
            "evidence_count_after": after["evidence_count"],
            "next_step_before": {"challenge_id": challenge_id, "reason_code": before["next_challenge"]["reason_code"]},
            "next_step_after": {"challenge_id": after["next_challenge"]["challenge_id"], "reason_code": after["next_challenge"]["reason_code"],
                                "why_this_now": after["next_challenge"]["why_this_now"]},
            "what_changed": after["what_changed"],
            "result": "PASS: synthetic challenge persisted, ledger incremented, next step changed explainably.",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (RuntimeError, KeyError, IndexError, ValueError) as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
