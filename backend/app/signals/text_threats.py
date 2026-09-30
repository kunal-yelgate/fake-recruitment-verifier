"""In-posting threat-pattern signal."""

from app.models import ExtractedFields, SignalResult


async def check_in_text_threats(fields: ExtractedFields, raw_text: str = "") -> SignalResult:
    """Check 1: Internal NLP & Regex scanner for explicit in-posting fraud patterns."""
    text_lower = raw_text.lower()
    threats_found = []

    # Check 1: Check Deposit / Upfront Hardware Fraud
    check_deposit_keywords = [
        "check deposit",
        "deposit check",
        "cashier check",
        "upfront check",
        "purchase equipment",
        "purchase hardware",
        "buy hardware",
        "buy equipment",
        "wire transfer",
        "western union",
        "moneygram",
    ]
    matched_checks = [kw for kw in check_deposit_keywords if kw in text_lower]
    if matched_checks:
        threats_found.append(f"Check deposit / equipment purchase trap detected ('{matched_checks[0]}')")

    # Check 2: Unverified Instant Messaging Redirects for Interviewing
    chat_redirect_keywords = [
        "telegram",
        "@hr",
        "@recruiter",
        "wa.me",
        "whatsapp",
        "signal app",
        "google chat",
        "hangouts",
    ]
    matched_chats = [kw for kw in chat_redirect_keywords if kw in text_lower]
    if matched_chats:
        threats_found.append(f"Unverified chat interview redirect ('{matched_chats[0]}')")

    # Common India-specific advance-payment and messaging-only patterns.
    india_fee_keywords = [
        "registration fee",
        "security deposit",
        "refundable deposit",
        "verification fee",
        "training fee",
    ]
    matched_india_fees = [kw for kw in india_fee_keywords if kw in text_lower]
    if matched_india_fees:
        threats_found.append(f"Recruitment fee or deposit request ('{matched_india_fees[0]}')")
    messaging_only = ("whatsapp" in text_lower or "telegram" in text_lower) and not fields.contact_email and not fields.claimed_domain
    if messaging_only:
        channel = "WhatsApp" if "whatsapp" in text_lower else "Telegram"
        threats_found.append(f"{channel}-only contact without a verifiable company channel")

    # Check 3: Non-standard Payouts / Crypto
    crypto_keywords = ["bitcoin", "usdt", "crypto", "gift card"]
    matched_crypto = [kw for kw in crypto_keywords if kw in text_lower]
    if matched_crypto:
        threats_found.append(f"Non-standard cryptocurrency / gift card payment request ('{matched_crypto[0]}')")

    # Check 4: Unrealistic Pay-for-Effort Ratio
    if any(title in text_lower for title in ["data entry", "administrative assistant", "clerk", "typist"]):
        if any(rate in text_lower for rate in ["$40", "$45", "$50", "$55", "$60", "$70"]) and (
            "no experience" in text_lower or "immediate" in text_lower
        ):
            threats_found.append("Unrealistic pay rate ($40+/hr) for low-skill entry position")

    if len(threats_found) >= 2 or any(
        "check deposit" in t.lower() or "chat interview" in t.lower() for t in threats_found
    ):
        reasons = "; ".join(threats_found)
        return SignalResult(
            signal_key="text_threat_signals",
            signal_name="In-Posting Threat Patterns",
            engine="nlp_regex",
            score_delta=25,
            status="fail",
            finding=f"Critical Fraud Alert: Posting contains explicit scam signatures: {reasons}.",
            query_used="In-text NLP Threat Pattern Scan",
            evidence_url=None,
            search_url=None,
            data_source="text",
        )
    elif len(threats_found) == 1:
        return SignalResult(
            signal_key="text_threat_signals",
            signal_name="In-Posting Threat Patterns",
            engine="nlp_regex",
            score_delta=10,
            status="warning",
            finding=f"Caution: Posting contains potential threat pattern: {threats_found[0]}.",
            query_used="In-text NLP Threat Pattern Scan",
            evidence_url=None,
            search_url=None,
            data_source="text",
        )

    return SignalResult(
        signal_key="text_threat_signals",
        signal_name="In-Posting Threat Patterns",
        engine="nlp_regex",
        score_delta=-10,
        status="pass",
        finding="No in-text scam signatures, check deposit traps, or unverified chat redirects detected.",
        query_used="In-text NLP Threat Pattern Scan",
        evidence_url=None,
        search_url=None,
        data_source="text",
    )
