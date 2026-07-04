from collections import defaultdict
from typing import List, Dict, Any


def aggregate_run_results(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rolls up individual test results into per-category pass rates."""
    total_scanned = len(findings)
    total_breaches = 0
    critical_alerts = 0

    by_category: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"scanned": 0, "passed": 0, "failed": 0})

    for finding in findings:
        category_name = finding["category"]
        was_breached = finding["is_violation"]
        severity_level = finding["severity"].lower()

        by_category[category_name]["scanned"] += 1

        if was_breached:
            by_category[category_name]["failed"] += 1
            total_breaches += 1
            if severity_level in {"critical", "high"}:
                critical_alerts += 1
        else:
            by_category[category_name]["passed"] += 1

    for _category, breakdown in by_category.items():
        breakdown["pass_rate"] = round((breakdown["passed"] / breakdown["scanned"]) * 100, 2)

    return {
        "meta": {
            "total_scanned": total_scanned,
            "total_breaches": total_breaches,
            "critical_alerts": critical_alerts,
            "overall_pass_rate": round(((total_scanned - total_breaches) / total_scanned) * 100, 2) if total_scanned > 0 else 100.0
        },
        "categories": dict(by_category),
        "raw_details": findings
    }