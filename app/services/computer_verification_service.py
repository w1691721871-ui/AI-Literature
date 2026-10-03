"""Safe verification projection for existing controlled Computer results."""

from __future__ import annotations

from collections.abc import Mapping


class ComputerVerificationService:
    """Never treats an absent or failed verification as a success."""

    def verify_action_result(self, before: Mapping[str, object], after: Mapping[str, object], mission_goal: str = "") -> dict[str, object]:
        before_status = str(before.get("status") or "NOT_OBSERVED").upper()
        after_status = str(after.get("status") or after.get("verification") or "NOT_RUN").upper()
        if after_status in {"PASS", "SUCCESS", "COMPLETED"}:
            status, summary = "SUCCESS", "The approved action completed its existing verification checks."
        elif after_status in {"NOT_RUN", "WAITING_REVIEW", "WAITING_APPROVAL"}:
            status, summary = "NEEDS_REVIEW", "Verification is incomplete and requires human review."
        else:
            status, summary = "FAILED", "Verification did not pass; the controlled workflow must stop for review or rollback."
        return {
            "status": status,
            "before_state": before_status,
            "after_state": after_status,
            "goal_checked": bool(str(mission_goal).strip()),
            "summary": summary,
            "rollback_required": status == "FAILED",
            "boundary": "This is a verification summary over the existing fixed allow-list; it does not execute commands.",
        }
