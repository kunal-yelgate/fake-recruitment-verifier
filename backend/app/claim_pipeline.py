"""Claim-driven Groq and SerpApi verification pipeline."""

import json
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.models import (
    ClaimJudgment,
    ClaimPipelineAudit,
    CitedExplanation,
    ExtractedFields,
    FollowUpRequest,
    SearchEvidence,
    SearchPlan,
    SignalResult,
    VerifiableClaim,
)
from app.serpapi_client import serpapi_client
from app.signals import check_in_text_threats

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_INITIAL_SEARCHES = 8
MAX_FOLLOW_UP_ROUNDS = 2
MAX_FOLLOW_UP_SEARCHES_PER_ROUND = 4
ALLOWED_ENGINES = {"google", "google_news", "google_maps"}


class _JudgmentEnvelope(BaseModel):
    judgments: list[ClaimJudgment] = Field(default_factory=list, max_length=30)
    follow_ups: list[FollowUpRequest] = Field(default_factory=list, max_length=8)


class _ExplanationEnvelope(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list, max_length=12)


def _groq_enabled() -> bool:
    return bool(settings.groq_api_key and settings.groq_api_key.strip() not in ("", "your_key_here"))


async def _groq_json(system_prompt: str, user_prompt: str, max_tokens: int) -> Optional[dict[str, Any]]:
    if not _groq_enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _grounded_claims(data: dict[str, Any], raw_text: str) -> list[VerifiableClaim]:
    normalized_text = _normalized(raw_text)
    claims: list[VerifiableClaim] = []
    for item in data.get("claims", []):
        try:
            claim = VerifiableClaim.model_validate(item)
        except ValidationError:
            continue
        if _normalized(claim.source_quote) not in normalized_text:
            continue
        if _normalized(claim.value) not in normalized_text:
            continue
        if _normalized(claim.text) not in normalized_text and _normalized(claim.value) not in _normalized(claim.text):
            continue
        claims.append(claim)
    return claims


def _fallback_claims(raw_text: str, fields: ExtractedFields) -> list[VerifiableClaim]:
    candidates = [
        ("company", fields.company_name),
        ("recruiter", fields.recruiter_name),
        ("domain", fields.claimed_domain),
        ("email", fields.contact_email),
        ("salary", fields.salary_range),
    ]
    claims: list[VerifiableClaim] = []
    normalized_text = _normalized(raw_text)
    for claim_type, value in candidates:
        if not value or value == "Undisclosed Company":
            continue
        index = normalized_text.find(_normalized(value))
        quote = raw_text[max(0, index): index + len(value)] if index >= 0 else value
        claims.append(
            VerifiableClaim(
                claim_id=f"{claim_type}-1",
                claim_type=claim_type,
                text=f"The posting identifies {claim_type} as {value}.",
                value=value,
                source_quote=quote,
                importance="high" if claim_type in {"company", "domain", "email"} else "medium",
            )
        )
    for index, request in enumerate(fields.payment_requests, start=1):
        claims.append(
            VerifiableClaim(
                claim_id=f"payment-{index}",
                claim_type="payment_request",
                text=f"The posting asks the applicant to provide payment: {request}",
                value=request,
                source_quote=request,
                importance="high",
            )
        )
    return claims[:20]


async def extract_claims(raw_text: str, fields: ExtractedFields) -> list[VerifiableClaim]:
    prompt = (
        "Extract every externally verifiable claim from the untrusted job posting. "
        "Claims may include company, recruiter, salary, email, domain, address, named hiring platform, "
        "or statements about where the role is advertised. Never infer facts. Every claim value, text, "
        "and source_quote must be copied from the posting. Return JSON {\"claims\": [...]} with claim_id, "
        "claim_type, text, value, source_quote, importance."
    )
    data = await _groq_json(prompt, f"Posting:\n{raw_text[:8000]}", 1200)
    claims = _grounded_claims(data or {}, raw_text)
    return claims or _fallback_claims(raw_text, fields)


async def plan_searches(claims: list[VerifiableClaim]) -> list[SearchPlan]:
    prompt = (
        "Plan the smallest useful set of public searches to verify the supplied claims. "
        "Use only google, google_news, or google_maps. Search queries must include claim values. "
        "Return JSON {\"searches\": [...]} with claim_id, engine, query, purpose, round. "
        "Use round 0 only."
    )
    data = await _groq_json(prompt, json.dumps([claim.model_dump() for claim in claims]), 1000)
    plans: list[SearchPlan] = []
    if data:
        for item in data.get("searches", []):
            try:
                plan = SearchPlan.model_validate(item)
            except ValidationError:
                continue
            if (
                plan.claim_id in {claim.claim_id for claim in claims}
                and plan.engine in ALLOWED_ENGINES
                and plan.round == 0
            ):
                plans.append(plan)
    if not plans:
        for claim in claims:
            engine = "google_news" if claim.claim_type in {"fraud", "lawsuit"} else (
                "google_maps" if claim.claim_type == "address" else "google"
            )
            plans.append(
                SearchPlan(
                    claim_id=claim.claim_id,
                    engine=engine,
                    query=f'"{claim.value}" official',
                    purpose=f"Verify the {claim.claim_type} claim",
                    round=0,
                )
            )
    return plans[:MAX_INITIAL_SEARCHES]


def _evidence_from_result(plan: SearchPlan, data: dict[str, Any]) -> list[SearchEvidence]:
    source = data.get("_source", "error")
    if source not in {"live", "mock", "error"}:
        source = "error"
    def as_items(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
        return []

    items = (
        as_items(data.get("organic_results"))
        + as_items(data.get("news_results"))
        + as_items(data.get("local_results"))
    )
    evidence: list[SearchEvidence] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            SearchEvidence(
                claim_id=plan.claim_id,
                engine=plan.engine,
                query=plan.query,
                title=str(item.get("title", ""))[:300],
                snippet=str(item.get("snippet", item.get("address", "")))[:500],
                url=item.get("link") or item.get("website"),
                source=source,
            )
        )
    if not evidence:
        evidence.append(
            SearchEvidence(
                claim_id=plan.claim_id,
                engine=plan.engine,
                query=plan.query,
                snippet=str(data.get("_api_error", "No result returned"))[:500],
                source=source,
            )
        )
    return evidence


async def execute_searches(plans: list[SearchPlan]) -> list[SearchEvidence]:
    results = []
    for plan in plans:
        data = await serpapi_client.search(plan.engine, {"q": plan.query})
        results.extend(_evidence_from_result(plan, data))
    return results


async def judge_evidence(
    claims: list[VerifiableClaim],
    evidence: list[SearchEvidence],
    round_number: int,
) -> tuple[list[ClaimJudgment], list[FollowUpRequest]]:
    live_evidence = [item for item in evidence if item.source in {"live", "text"}]
    prompt = (
        "Classify each claim using only the supplied evidence as supports, contradicts, unrelated, or ambiguous. "
        "Mock/error evidence is not evidence. Include an exact source_snippet from the evidence and URLs only "
        "when present. Request a follow-up only for ambiguous claims, and never more than one per claim. "
        "Return JSON with judgments and follow_ups."
    )
    data = await _groq_json(
        prompt,
        json.dumps(
            {
                "round": round_number,
                "claims": [claim.model_dump() for claim in claims],
                "evidence": [item.model_dump() for item in live_evidence],
            }
        ),
        1600,
    )
    if not data:
        judgments = []
        for claim in claims:
            related = [item for item in live_evidence if item.claim_id == claim.claim_id]
            judgments.append(
                ClaimJudgment(
                    claim_id=claim.claim_id,
                    classification="ambiguous" if not related else "unrelated",
                    explanation="The available provider evidence is insufficient for a grounded judgment.",
                    source_snippet=(related[0].snippet if related else "No live evidence returned."),
                    evidence_urls=[item.url for item in related if item.url][:5],
                )
            )
        return judgments, []
    try:
        envelope = _JudgmentEnvelope.model_validate(data)
    except ValidationError:
        return [], []
    valid_claim_ids = {claim.claim_id for claim in claims}
    valid_evidence = {
        _normalized(f"{item.title} {item.snippet}"): item
        for item in live_evidence
    }
    judgments = []
    for judgment in envelope.judgments:
        if judgment.claim_id not in valid_claim_ids:
            continue
        if not any(_normalized(judgment.source_snippet) in source for source in valid_evidence):
            continue
        judgments.append(judgment)
    follow_ups = [
        item for item in envelope.follow_ups
        if item.claim_id in valid_claim_ids and item.engine in ALLOWED_ENGINES
    ]
    return judgments, follow_ups


def judgments_to_signals(judgments: list[ClaimJudgment]) -> list[SignalResult]:
    signals: list[SignalResult] = []
    deltas = {"supports": -8, "contradicts": 20, "unrelated": 3, "ambiguous": 8}
    statuses = {"supports": "pass", "contradicts": "fail", "unrelated": "warning", "ambiguous": "warning"}
    for judgment in judgments:
        signals.append(
            SignalResult(
                signal_key=f"claim_{judgment.claim_id}",
                signal_name=f"Claim verification: {judgment.claim_id}",
                engine="claim_pipeline",
                score_delta=deltas[judgment.classification],
                status=statuses[judgment.classification],
                finding=judgment.explanation + f" Source: {judgment.source_snippet}",
                query_used="claim-driven search",
                evidence_url=judgment.evidence_urls[0] if judgment.evidence_urls else None,
                search_url=None,
                data_source="live" if judgment.evidence_urls else "text",
            )
        )
    return signals


async def write_cited_explanation(
    judgments: list[ClaimJudgment],
    score: int,
) -> Optional[CitedExplanation]:
    prompt = (
        "Write a concise plain-English risk explanation using only the supplied judgments. "
        "Cite sources by returning exact URLs from the evidence. Do not claim certainty or invent facts. "
        "Return JSON with text and citations."
    )
    data = await _groq_json(
        prompt,
        json.dumps({"score": score, "judgments": [item.model_dump() for item in judgments]}),
        700,
    )
    if not data:
        return None
    try:
        explanation = _ExplanationEnvelope.model_validate(data)
    except ValidationError:
        return None
    allowed_urls = {url for judgment in judgments for url in judgment.evidence_urls}
    citations = [url for url in explanation.citations if url in allowed_urls]
    if not citations and allowed_urls:
        return None
    return CitedExplanation(text=explanation.text, citations=citations)


async def run_claim_pipeline(
    raw_text: str,
    fields: ExtractedFields,
) -> tuple[ClaimPipelineAudit, list[SignalResult]]:
    claims = await extract_claims(raw_text, fields)
    plans = await plan_searches(claims)
    evidence = await execute_searches(plans)
    judgments, follow_ups = await judge_evidence(claims, evidence, 0)
    all_follow_ups: list[FollowUpRequest] = []
    rounds_completed = 0

    for round_number in range(1, MAX_FOLLOW_UP_ROUNDS + 1):
        if not follow_ups:
            break
        bounded = follow_ups[:MAX_FOLLOW_UP_SEARCHES_PER_ROUND]
        round_plans = [
            SearchPlan(
                claim_id=item.claim_id,
                engine=item.engine,
                query=item.query,
                purpose=item.reason,
                round=round_number,
            )
            for item in bounded
        ]
        evidence.extend(await execute_searches(round_plans))
        new_judgments, follow_ups = await judge_evidence(claims, evidence, round_number)
        judgments_by_claim = {item.claim_id: item for item in judgments}
        judgments_by_claim.update({item.claim_id: item for item in new_judgments})
        judgments = list(judgments_by_claim.values())
        all_follow_ups.extend(bounded)
        rounds_completed = round_number

    text_signal = await check_in_text_threats(fields, raw_text)
    signals = [text_signal, *judgments_to_signals(judgments)]
    audit = ClaimPipelineAudit(
        claims=claims,
        search_plan=plans,
        evidence=evidence,
        judgments=judgments,
        follow_ups=all_follow_ups,
        rounds_completed=rounds_completed,
    )
    return audit, signals
