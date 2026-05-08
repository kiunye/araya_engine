import uuid
import json
import re
import logging
from typing import List, Dict, Any, Optional

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from araya.agents.state import ResearchState
from araya.agents.models import Finding, Confidence
from araya.agents.lead_agent import get_model
from araya.core.config import settings

logger = logging.getLogger(__name__)


class SearchAgent:
    def __init__(self):
        self.model = get_model("gemini-1.5-flash")
        self.serper_api_key = settings.SERPER_API_KEY if hasattr(settings, 'SERPER_API_KEY') else None
        self._http_client = None

    async def run(self, state: ResearchState) -> Dict[str, Any]:
        objective = state.get("objective", "")
        plan = state.get("plan", [])

        research_instruction = objective
        if plan:
            pending_tasks = [p.description for p in plan if p.status == "pending"]
            if pending_tasks:
                research_instruction = f"{objective}\nPending tasks: {'; '.join(pending_tasks)}"

        queries = await self._generate_search_queries(research_instruction)

        search_results = []
        for query in queries:
            results = await self._search_web(query)
            search_results.extend(results)

        findings = []
        for result in search_results[:5]:
            url = result.get("url")
            if url:
                content = await self._fetch_page(url)
                if content:
                    extracted_findings = await self._extract_facts(content, objective, url)
                    findings.extend(extracted_findings)

        logger.info(f"SearchAgent extracted {len(findings)} findings from {len(search_results)} results")
        return {"findings": findings}

    async def _generate_search_queries(self, instruction: str) -> List[str]:
        system_prompt = (
            "You are an expert at information retrieval. "
            "Given a research instruction, generate 3-5 specific search queries "
            "that would help gather the required information. "
            "Return only the queries, one per line."
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=instruction)
        ]
        response = await self.model.ainvoke(messages)
        queries = [q.strip() for q in response.content.split("\n") if q.strip()]
        return queries[:5]

    async def _search_web(self, query: str) -> List[Dict[str, Any]]:
        if self.serper_api_key:
            return await self._search_serper(query)
        logger.info(f"Searching (no Serper key): {query}")
        return []

    async def _search_serper(self, query: str) -> List[Dict[str, Any]]:
        try:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient()
            response = await self._http_client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5},
                headers={"X-API-KEY": self.serper_api_key},
                timeout=settings.HTTP_SEARCH_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            return results
        except Exception as e:
            logger.error(f"Serper search failed for '{query}': {e}")
            return []

    async def _fetch_page(self, url: str) -> Optional[str]:
        try:
            from araya.ingestor.web import WebIngestor
            web_ingestor = WebIngestor()
            research_obj = await web_ingestor.ingest(url)
            return research_obj.content
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            try:
                if self._http_client is None:
                    self._http_client = httpx.AsyncClient()
                response = await self._http_client.get(url, timeout=settings.HTTP_FETCH_TIMEOUT, follow_redirects=True)
                response.raise_for_status()
                text = re.sub(r'<[^>]+>', ' ', response.text)
                text = re.sub(r'\s+', ' ', text)
                return text.strip()[:5000]
            except Exception as e2:
                logger.warning(f"HTTP fallback also failed for {url}: {e2}")
                return None

    async def _extract_facts(self, content: str, objective: str, url: str) -> List[Finding]:
        system_prompt = (
            "You are a Fact Extraction Agent. Your goal is to extract specific, verifiable "
            "claims and statistics from the provided content that are relevant to the objective. "
            "For each finding, provide: claim, excerpt, and confidence level (high, medium, low). "
            "Format the output as a JSON list of objects with keys: claim, excerpt, confidence."
        )
        prompt = f"Objective: {objective}\n\nContent:\n{content[:5000]}"
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]

        try:
            response = await self.model.ainvoke(messages)
            match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                findings = []
                for item in data:
                    confidence_str = item.get("confidence", "medium").lower()
                    confidence = Confidence.MEDIUM
                    if confidence_str == "high":
                        confidence = Confidence.HIGH
                    elif confidence_str == "low":
                        confidence = Confidence.LOW

                    finding = Finding(
                        id=f"finding_{uuid.uuid4().hex[:8]}",
                        claim=item.get("claim", ""),
                        source_url=url,
                        source_excerpt=item.get("excerpt", ""),
                        confidence=confidence,
                        metadata={"credibility_score": self.rate_source_credibility(url)}
                    )
                    findings.append(finding)
                return findings
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error parsing search findings: {e}")

        return []

    async def close(self):
        """Close the HTTP client to free up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def rate_source_credibility(self, url: str) -> float:
        high_cred = [".gov", ".edu", "reuters.com", "bloomberg.com", "wsj.com", "nvidia.com"]
        for domain in high_cred:
            if domain in url:
                return 0.9
        return 0.5
