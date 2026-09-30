"""Async HTTP client for SerpApi with SQLite query caching and demo mock fallback."""

import asyncio
import logging
from typing import Any, Dict, Optional
import httpx
from app.config import settings
from app.cache import cache

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.serpapi_key

    async def search(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a cached SerpApi search query across specified engine."""
        search_params = {"engine": engine, **params}

        # 1. Check local SQLite cache first (24h TTL)
        cached_result = cache.get(engine, search_params)
        if (
            cached_result is not None
            and not cached_result.get("_is_mock")
            and not cached_result.get("_api_error")
        ):
            cached_result.setdefault(
                "_source",
                "mock" if cached_result.get("_is_mock") else "error" if cached_result.get("_api_error") else "live",
            )
            return cached_result

        # 2. If no API key is provided, return simulated responses without caching them.
        if not self.api_key or self.api_key.strip() in ("", "your_serpapi_key_here"):
            mock_data = self._generate_mock_response(engine, params)
            mock_data["_source"] = "mock"
            return mock_data

        # 3. Call live SerpApi HTTP API
        request_params = {**search_params, "api_key": self.api_key}
        async with httpx.AsyncClient(timeout=15.0) as client:
            for attempt in range(3):
                try:
                    response = await client.get(SERPAPI_ENDPOINT, params=request_params)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("SerpApi response was not a JSON object")
                    data["_is_mock"] = False
                    data["_source"] = "live"
                    cache.set(engine, search_params, data)
                    return data
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 401 or (
                        exc.response.status_code < 500
                        and exc.response.status_code != 429
                    ):
                        return self._error_response(
                            engine, params, f"SerpApi HTTP {exc.response.status_code}"
                        )
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
                        continue
                    return self._error_response(
                        engine, params, f"SerpApi HTTP {exc.response.status_code}"
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
                        continue
                    return self._error_response(engine, params, type(exc).__name__)
                except (ValueError, httpx.HTTPError) as exc:
                    return self._error_response(engine, params, type(exc).__name__)

        return self._error_response(engine, params, "SerpApi request failed")

    def _error_response(
        self, engine: str, params: Dict[str, Any], message: str
    ) -> Dict[str, Any]:
        """Return an explicit provider error without leaking the API key."""
        logging.getLogger(__name__).warning("SerpApi provider failure: %s", message)
        error_data = self._generate_mock_response(engine, params)
        error_data["_api_error"] = message
        error_data["_source"] = "error"
        return error_data

    def _generate_mock_response(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic mock data when SERPAPI_KEY is not configured yet."""
        query = str(params.get("q", params.get("query", ""))).lower()

        # Check for typical scam indicators in the simulated query
        is_suspicious = any(
            term in query
            for term in [
                "telegram",
                "whatsapp",
                "check deposit",
                "equipment fee",
                "crypto",
                "amazon-careers.net",
                "apexglobal-staffing.org",
                "apex",
                "quickhiring",
                "work-from-home-instant",
                "hr-desk",
                "gmail.com",
                "scam",
                "fraud",
                "lawsuit",
                "complaints",
            ]
        )

        data: Dict[str, Any] = {"_is_mock": True, "search_parameters": params}

        if engine == "google_maps":
            if "google" in query or "microsoft" in query or "apple" in query or "stripe" in query:
                data["place_results"] = {
                    "title": params.get("q", "Corporate Headquarters"),
                    "address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
                    "rating": 4.6,
                    "reviews": 1824,
                    "verified": True,
                }
                data["local_results"] = [data["place_results"]]
            elif is_suspicious or "apex" in query or "global staffing" in query:
                data["local_results"] = []
            else:
                data["local_results"] = [
                    {
                        "title": params.get("q", "Company Office"),
                        "address": "100 Innovation Way, Suite 400",
                        "rating": 4.1,
                    }
                ]

        elif engine == "google_news":
            if is_suspicious:
                data["news_results"] = [
                    {
                        "title": "Alert: Job seekers warned about fake check employment scam impersonating recruiters",
                        "link": "https://www.ftc.gov/news-events/news/fake-job-scams",
                        "source": "FTC Consumer Alert",
                        "date": "2 days ago",
                    },
                    {
                        "title": "Victims lose thousands in remote data entry job fraud",
                        "link": "https://www.bbb.org/article/news-releases/remote-work-scams",
                        "source": "Better Business Bureau",
                        "date": "1 week ago",
                    },
                ]
            else:
                data["news_results"] = []

        else:  # engine == 'google'
            if "site:linkedin.com" in query:
                if is_suspicious or "apex" in query:
                    data["organic_results"] = []
                else:
                    data["organic_results"] = [
                        {
                            "title": f"Official Careers & People | LinkedIn",
                            "link": f"https://www.linkedin.com/company/{params.get('q', 'company').replace(' ', '-').lower()}",
                            "snippet": "Verified corporate profile on LinkedIn. View open roles, employee headcount and leadership.",
                        }
                    ]
            elif "official website" in query:
                # Lookalike vs official corporate website search
                if is_suspicious and ("amazon-careers" in query or "apex" in query):
                    data["organic_results"] = [
                        {
                            "title": "Warning: Beware of impostor career domains",
                            "link": "https://careers.verified-portal.com",
                            "snippet": "Beware of unverified third-party recruiters using similar names.",
                        }
                    ]
                else:
                    clean_name = query.replace("official website", "").replace('"', '').replace("inc.", "").replace("llc", "").strip()
                    company_slug = "".join(c for c in clean_name if c.isalnum()).lower() or "company"
                    data["organic_results"] = [
                        {
                            "title": f"{clean_name.title()} | Official Corporate Website",
                            "link": f"https://{company_slug}.com",
                            "snippet": f"Official verified website of {clean_name.title()}.",
                        }
                    ]
            elif "recruiter" in query or "talent" in query:
                if is_suspicious:
                    data["organic_results"] = []
                else:
                    data["organic_results"] = [
                        {
                            "title": f"Talent Acquisition & Leadership - {params.get('q', '')}",
                            "link": "https://www.linkedin.com/in/verified-recruiter",
                            "snippet": "Verified recruitment and human resources team member.",
                        }
                    ]
            elif '"' in query:  # Duplicate exact phrase check
                if is_suspicious:
                    data["organic_results"] = [
                        {"title": "Easy Remote Job $45/hr", "link": "https://forum.free-jobs-board.xyz/post/1049"},
                        {"title": "Immediate Hiring Data Entry", "link": "https://pastebin.com/raw/k93Jdx"},
                        {"title": "Telegram Job Chat Work From Home", "link": "https://telegra.ph/Job-Details-09"},
                        {"title": "Urgent Freelance Opening", "link": "https://workboard.online/job/4921"},
                        {"title": "Weekly payout guaranteed", "link": "https://classifieds-spam.net/ads/992"},
                    ]
                else:
                    data["organic_results"] = [
                        {
                            "title": "Careers at Official Portal",
                            "link": "https://careers.company.com/openings",
                            "snippet": "Official listing on verified company careers portal.",
                        }
                    ]
            else:
                clean_name = "".join(c for c in query if c.isalnum()).lower()[:15] or "company"
                data["organic_results"] = [
                    {
                        "title": f"Official Website - {params.get('q', '')}",
                        "link": f"https://{clean_name}.com",
                        "snippet": "Official corporate domain with SSL certificate and corporate directory.",
                    }
                ]

        return data


# Shared client instance
serpapi_client = SerpApiClient()
