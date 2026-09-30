"""Unit tests for the weighted scoring engine."""

from app.models import SignalResult
from app.scoring import BASE_SCORE, calculate_risk_score


def make_signal(key: str, delta: int, status: str = "pass") -> SignalResult:
    return SignalResult(
        signal_key=key,
        signal_name=key.replace("_", " ").title(),
        engine="google",
        score_delta=delta,
        status=status,
        finding="Mock finding summary",
        query_used="mock query",
        evidence_url=None,
        search_url=None,
    )


def test_base_score_default():
    """Empty signals should yield neutral base score (50) -> Caution."""
    score, verdict, badge, summary = calculate_risk_score([])
    assert score == BASE_SCORE
    assert verdict == "Caution"
    assert badge == "warning"


def test_scam_threshold_trigger():
    """Signals pushing delta above +15 should result in >= 65 score -> Likely Scam."""
    signals = [
        make_signal("domain_match", 25, "fail"),
        make_signal("duplicate_posting", 18, "fail"),
    ]
    score, verdict, badge, summary = calculate_risk_score(signals)
    # 50 + 25 + 18 = 93
    assert score == 93
    assert verdict == "Likely Scam"
    assert badge == "danger"
    assert "High risk score" in summary
    assert "probability" not in summary.lower()


def test_legit_threshold_trigger():
    """Positive legitimacy signals reducing score below 35 -> Likely Legitimate."""
    signals = [
        make_signal("company_footprint", -15, "pass"),
        make_signal("linkedin_presence", -15, "pass"),
        make_signal("domain_match", -15, "pass"),
    ]
    score, verdict, badge, summary = calculate_risk_score(signals)
    # 50 - 15 - 15 - 15 = 5
    assert score == 5
    assert verdict == "Likely Legitimate"
    assert badge == "success"
    assert "Low risk score" in summary
    assert "cannot prove" in summary
    assert "probability" not in summary.lower()


def test_score_clamping_bounds():
    """Ensure score never exceeds 100 or drops below 0."""
    extreme_scam = [make_signal(f"signal_{i}", 30, "fail") for i in range(5)]
    score_max, _, _, _ = calculate_risk_score(extreme_scam)
    assert score_max == 100

    extreme_legit = [make_signal(f"signal_{i}", -40, "pass") for i in range(5)]
    score_min, _, _, _ = calculate_risk_score(extreme_legit)
    assert score_min == 0
