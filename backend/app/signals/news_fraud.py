"""News fraud-mention signal."""

import urllib.parse

from app.models import ExtractedFields, SignalResult
from app.serpapi_client import serpapi_client

from .shared import _unavailable_search_signal


async def check_news_fraud(fields: ExtractedFields) -> SignalResult:
    """Check 5: Google News scan for scam, fraud, or lawsuit complaints with false-positive protection."""
    company = fields.company_name or ""
    if not company or company == "Undisclosed Company":
        return SignalResult(
            signal_key="news_fraud_mentions",
            signal_name="News Fraud & Scam Mentions",
            engine="google_news",
            score_delta=0,
            status="pass",
            finding="Company name not disclosed; news fraud check bypassed.",
            query_used="N/A",
            evidence_url=None,
            search_url=None,
        )

    query = f'"{company}" (scam OR fraud OR fake OR lawsuit OR complaint)'
    params = {"q": query}
    search_url = f"https://news.google.com/search?q={urllib.parse.quote_plus(query)}"

    data = await serpapi_client.search("google_news", params)
    unavailable = _unavailable_search_signal(data, "News Fraud & Scam Mentions", "google_news", query, search_url)
    if unavailable:
        unavailable.signal_key = "news_fraud_mentions"
        return unavailable
    news = data.get("news_results", [])

    if news and len(news) > 0:
        top_news = news[0]
        headline = top_news.get("title", "Fraud report")
        snippet = top_news.get("snippet", "")
        source = top_news.get("source", "News Alert")
        link = top_news.get("link") or search_url

        combined_text = (headline + " " + snippet).lower()

        # False positive check: Is the news about scams IMPERSONATING the company?
        impersonation_markers = [
            "warns",
            "warning",
            "targets",
            "impersonating",
            "impostor",
            "fake jobs impersonate",
            "protect against",
            "scam alert targeting",
            "beware of fake",
            "identity theft impersonating",
        ]
        if any(marker in combined_text for marker in impersonation_markers):
            return SignalResult(
                signal_key="news_fraud_mentions",
                signal_name="News Fraud & Scam Mentions",
                engine="google_news",
                score_delta=-5,
                status="pass",
                finding=f"Media alerts describe fake scams impersonating '{company}', but no direct fraud complaints against the official entity.",
                query_used=query,
                evidence_url=link,
                search_url=search_url,
            )

        return SignalResult(
            signal_key="news_fraud_mentions",
            signal_name="News Fraud & Scam Mentions",
            engine="google_news",
            score_delta=20,
            status="fail",
            finding=f'Public fraud complaints or scam alerts detected: "{headline}" ({source}).',
            query_used=query,
            evidence_url=link,
            search_url=search_url,
        )

    return SignalResult(
        signal_key="news_fraud_mentions",
        signal_name="News Fraud & Scam Mentions",
        engine="google_news",
        score_delta=-5,
        status="pass",
        finding=f"No negative press, regulatory enforcement, or scam complaints discovered in Google News for '{company}'.",
        query_used=query,
        evidence_url=None,
        search_url=search_url,
    )
