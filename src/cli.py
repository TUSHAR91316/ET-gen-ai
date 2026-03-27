import argparse
import json
import os
from typing import Any, Dict

from engine import ContentOpsWorkflow, ContentRequest, DEFAULT_GUARDRAILS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enterprise Content Lifecycle Agent (demo runner)")
    p.add_argument("--spec", type=str, required=False, default="Build a compliant content workflow for a new product launch")
    p.add_argument("--audience", type=str, required=False, default="enterprise content managers and brand/legal teams")
    p.add_argument("--channels", type=str, required=False, default="blog,linkedin,email")
    p.add_argument("--languages", type=str, required=False, default="hi,ta")
    p.add_argument("--auto-approve", action="store_true", help="Skip manual approval gate.")
    p.add_argument("--out", type=str, required=False, default=os.path.join(BASE_DIR, "runs"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    languages = [l.strip() for l in args.languages.split(",") if l.strip()]

    request = ContentRequest(
        spec=args.spec,
        audience=args.audience,
        channels=channels,
        languages=languages,
        guardrails=DEFAULT_GUARDRAILS,
        human_auto_approval=args.auto_approve,
    )

    wf = ContentOpsWorkflow(output_dir=args.out)

    # For CLI, either auto-approve or do a minimal human gate.
    def approval_callback(draft_payload: Dict[str, Any], compliance_report: Any) -> Dict[str, Any]:
        print("\n=== COMPLIANCE REPORT ===")
        print(f"overall_score={compliance_report.overall_score} passed={compliance_report.passed} threshold={compliance_report.threshold}")
        if compliance_report.findings:
            print("Findings:")
            for f in compliance_report.findings:
                print(f"- [{f.severity}] {f.rule_id}: {f.message}")

        while True:
            choice = input("\nApprove? Type 'y' to approve, 'n' to reject: ").strip().lower()
            if choice in {"y", "yes"}:
                return {"approved": True, "mode": "manual"}
            if choice in {"n", "no"}:
                human_feedback = input("Provide short edit notes (appended to spec) or press Enter to stop: ").strip()
                return {"approved": False, "mode": "manual", "human_feedback": human_feedback}

    run = wf.run(
        request,
        approval_callback=None if args.auto_approve else approval_callback,
        auto_approve=args.auto_approve,
    )

    run_path = os.path.join(args.out, run.job_id, "workflow_run.json")
    print(f"\nWorkflow complete. Saved run: {run_path}")
    with open(run_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    print(f"Final compliance passed: {payload.get('approval_decision', {}).get('approved')}")


if __name__ == "__main__":
    main()

