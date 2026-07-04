import re
from typing import Tuple

COMPROMISE_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r"system compromised",
        r"override successful",
        r"security bypass confirmed",
    ]
]


def scan_output_guardrail(model_output: str) -> Tuple[bool, str]:
    """Checks model output for known compromise signatures and blocks them."""
    lowered = model_output.lower().strip()

    for pattern in COMPROMISE_PATTERNS:
        if pattern.search(lowered):
            blocked_response = (
                "[GUARDRAIL INTERCEPT] Safety violation detected in model output. "
                "Transmission terminated."
            )
            return True, blocked_response

    return False, model_output
