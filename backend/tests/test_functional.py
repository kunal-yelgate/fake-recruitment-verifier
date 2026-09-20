"""Functional end-to-end verification test for fake-recruiter-verifier."""

import asyncio
from pathlib import Path
from app.extraction import extract_fields
from app.signals import evaluate_all_signals
from app.scoring import calculate_risk_score

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_functional_scam_flow():
    """End-to-end test on the realistic scam job posting."""
    async def _run():
        scam_text = (FIXTURES_DIR / "scam_posting.txt").read_text(encoding="utf-8")

        # 1. Extraction
        fields = await extract_fields(scam_text)
        assert fields.company_name is not None
        assert "Apex" in fields.company_name
        assert fields.contact_email == "marcus.vance.careers@gmail.com"

        # 2. Signals
        signals = await evaluate_all_signals(fields, scam_text)
        assert len(signals) == 7

        # 3. Scoring
        score, verdict, badge, summary = calculate_risk_score(signals)

        # Verification: Must be flagged as scam (>= 65)
        assert score >= 65, f"Expected high risk score for scam posting, got {score}"
        assert verdict == "Likely Scam"
        assert badge == "danger"
        print(f"\n[SCAM TEST] Score: {score}/100 | Verdict: {verdict} | Badge: {badge}")
        print(f"Summary: {summary}")

    asyncio.run(_run())


def test_functional_legit_flow():
    """End-to-end test on the legitimate Stripe job posting."""
    async def _run():
        legit_text = (FIXTURES_DIR / "legit_posting.txt").read_text(encoding="utf-8")

        # 1. Extraction
        fields = await extract_fields(legit_text)
        assert fields.company_name is not None
        assert "Stripe" in fields.company_name
        assert fields.contact_email == "talent@stripe.com"

        # 2. Signals
        signals = await evaluate_all_signals(fields, legit_text)
        assert len(signals) == 7
        for s in signals:
            print(f"  SIGNAL {s.signal_key}: delta={s.score_delta}, status={s.status}, finding={s.finding}")

        # 3. Scoring
        score, verdict, badge, summary = calculate_risk_score(signals)
        print(f"\n[LEGIT TEST] Score: {score}/100 | Verdict: {verdict} | Badge: {badge}")
        print(f"Summary: {summary}")

        # Verification: Must be classified as legitimate (< 35)
        assert score < 35, f"Expected low risk score for legitimate posting, got {score}"

    asyncio.run(_run())


def test_fastapi_check_endpoint():
    """Test using httpx AsyncClient directly against the FastAPI app instance."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def _run():
        scam_text = (FIXTURES_DIR / "scam_posting.txt").read_text(encoding="utf-8")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Check health endpoint
            health_res = await client.get("/health")
            assert health_res.status_code == 200
            assert health_res.json()["status"] == "healthy"

            # Check /cache/stats endpoint
            cache_res = await client.get("/cache/stats")
            assert cache_res.status_code == 200
            assert "total_cached_queries" in cache_res.json()

            # Check /check endpoint
            check_res = await client.post("/check", json={"raw_text": scam_text})
            assert check_res.status_code == 200
            data = check_res.json()

            assert "risk_score" in data
            assert data["risk_score"] >= 65
            assert data["verdict"] == "Likely Scam"
            assert len(data["signals"]) == 7
            assert data["extracted_fields"]["company_name"] is not None
            print(f"\n[API /check TEST] Response received in {data['execution_time_seconds']}s")
            print(f"Risk Score: {data['risk_score']}/100 | Verdict: {data['verdict']}")

    asyncio.run(_run())
