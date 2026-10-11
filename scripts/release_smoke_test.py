"""Read-only smoke test for a deployed ResearchOS v200 Golden Demo.

The command creates no user, Mission, Evidence, Review, Artifact, corpus, or
index. It is safe to run repeatedly against the public API after deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXPECTED_RELEASE = "researchos-demo-v200"
EXPECTED_FRONTEND_VERSION = "v200"


def _get_json(url: str, token: str = "") -> tuple[dict[str, Any] | None, str | None]:
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        request = Request(url, headers=headers)
        with urlopen(request, timeout=15) as response:  # nosec B310 - operator supplies the release API URL
            if response.status != 200:
                return None, f"HTTP {response.status}"
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None, None
    except HTTPError as error:
        return None, f"HTTP {error.code}"
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return None, type(error).__name__


def _report(name: str, passed: bool, detail: str) -> bool:
    print(f"{name}: {'PASS' if passed else 'FAIL'} — {detail}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only ResearchOS public-release smoke test")
    parser.add_argument("--api-url", default=os.getenv("RESEARCHOS_API_URL", ""), help="public API base URL")
    parser.add_argument("--expected-release", default=EXPECTED_RELEASE)
    parser.add_argument("--expected-frontend-version", default=EXPECTED_FRONTEND_VERSION)
    parser.add_argument(
        "--admin-session-token",
        default=os.getenv("RESEARCHOS_ADMIN_SESSION_TOKEN", ""),
        help="optional compatibility-admin bearer token for protected diagnostics",
    )
    args = parser.parse_args()

    api_url = args.api_url.strip().rstrip("/")
    if not api_url:
        print("release URL: FAIL — supply --api-url or RESEARCHOS_API_URL")
        return 2
    if not api_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        print("release URL: FAIL — public API URLs must use HTTPS")
        return 2

    health, health_error = _get_json(f"{api_url}/health")
    version, version_error = _get_json(f"{api_url}/api/version")
    readiness, readiness_error = _get_json(f"{api_url}/api/release/demo-readiness")
    diagnostics, diagnostics_error = _get_json(
        f"{api_url}/researchos/diagnostics", args.admin_session_token.strip()
    )

    checks: list[bool] = []
    checks.append(_report("health", bool(health and health.get("status") == "ok"), health_error or "API health is ok"))
    version_ok = bool(
        version
        and version.get("release") == args.expected_release
        and version.get("frontend_version") == args.expected_frontend_version
        and version.get("commit")
        and version.get("commit") != "not-configured"
        and version.get("status") == "ok"
    )
    checks.append(_report("release identity", version_ok, version_error or (
        f"release={version.get('release')}, frontend={version.get('frontend_version')}, "
        f"commit={version.get('commit')}, environment={version.get('environment')}"
    )))
    checks.append(_report("demo readiness", bool(readiness and readiness.get("overall") == "PASS"), readiness_error or (
        f"overall={readiness.get('overall')}, workspace={readiness.get('demo_workspace_id')}"
    )))
    if args.admin_session_token.strip():
        counts = diagnostics.get("counts", {}) if diagnostics else {}
        diagnostics_ok = bool(
            diagnostics
            and diagnostics.get("overall") == "PASS"
            and int(counts.get("papers", 0) or 0) > 0
            and int(counts.get("chunks", 0) or 0) > 0
            and int(counts.get("embedded_chunks", 0) or 0) > 0
        )
        diagnostics_detail = diagnostics_error or (
            f"overall={diagnostics.get('overall')}, papers={counts.get('papers', 0)}, "
            f"chunks={counts.get('chunks', 0)}, embeddings={counts.get('embedded_chunks', 0)}"
        )
    else:
        # Final architecture convergence keeps /researchos compatibility
        # diagnostics outside the public Demo surface. The public readiness
        # endpoint above verifies real corpus data; this check verifies that
        # the legacy diagnostic endpoint is not anonymously exposed.
        diagnostics_ok = diagnostics_error in {"HTTP 401", "HTTP 403"}
        diagnostics_detail = diagnostics_error or "diagnostics unexpectedly returned public data"
    checks.append(_report("research diagnostics access", diagnostics_ok, diagnostics_detail))

    passed = all(checks)
    print(f"\nRELEASE SMOKE TEST: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
