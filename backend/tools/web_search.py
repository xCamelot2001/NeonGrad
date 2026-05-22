"""
web_search.py — Tavily-powered company research tool (Phase 3).
"""
import asyncio
import os

_client = None


def _get_tavily():
    global _client
    if _client is None:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set in backend/.env. "
                "Get a free key at https://app.tavily.com and add it."
            )
        _client = TavilyClient(api_key=api_key)
    return _client


async def search_company(company_name: str) -> str:
    """
    Search for company info and return a concise research summary.
    Runs the sync Tavily client in a thread so it doesn't block the event loop.
    Returns a plain-text summary ready to drop into prompts.
    """
    try:
        client = _get_tavily()
        results = await asyncio.to_thread(
            client.search,
            f"{company_name} company mission culture tech stack values recent news",
            max_results=5,
            search_depth="advanced",
        )

        snippets = []
        for r in results.get("results", []):
            content = (r.get("content") or "").strip()
            if content:
                snippets.append(f"• {content[:450]}")

        if not snippets:
            return f"No detailed research found for {company_name}."

        return f"Company research for {company_name}:\n" + "\n".join(snippets[:5])

    except RuntimeError:
        raise  # propagate missing-key errors so the agent can surface them
    except Exception as exc:
        # Non-fatal: agent continues without research
        return f"Company research unavailable ({exc}). Proceeding without it."
