import asyncio
import os
from araya.agents.search_agent import SearchAgent
from araya.reporting.engine import ReportEngine
from araya.agents.state import ResearchState, Finding, Confidence
from datetime import datetime

async def test_search_and_report():
    # Mock state
    state: ResearchState = {
        "research_id": "test-123",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "research_plan": "Find information about NVIDIA's Q3 2024 results",
        "findings": [],
        "context_refs": [],
        "objective": "NVIDIA Q3 2024 Financial Performance",
        "search_results": [],
        "final_report": None,
        "report_metadata": {}
    }

    print("--- Testing Search Agent ---")
    search_agent = SearchAgent()
    # Mocking _search_web to avoid needing a real API key for this test
    async def mock_search_web(query):
        return [
            {"title": "NVIDIA Q3 Earnings", "url": "https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2024", "snippet": "NVIDIA reported revenue of $35.1 billion..."}
        ]
    search_agent._search_web = mock_search_web
    
    # Mocking _fetch_page to avoid real network call
    async def mock_fetch_page(url):
        return "NVIDIA reported revenue of $35.1 billion for the third quarter of fiscal 2024, up 94% from a year ago."
    search_agent._fetch_page = mock_fetch_page

    result = await search_agent.run(state, "Find NVIDIA's Q3 2024 revenue and growth rate")
    findings = result["findings"]
    print(f"Extracted {len(findings)} findings:")
    for f in findings:
        print(f" - {f['claim']} (Confidence: {f['confidence']})")

    print("\n--- Testing Report Engine ---")
    report_engine = ReportEngine()
    report_md = await report_engine.generate_report(state["objective"], findings)
    
    print("Generated Report Preview:")
    print(report_md[:500] + "...")
    
    # Save report to a file
    with open("/home/team/shared/araya-engine/test_report.md", "w") as f:
        f.write(report_md)
    print("\nFull report saved to test_report.md")

if __name__ == "__main__":
    # Ensure GOOGLE_API_KEY is set or mocked in the engine
    # In this environment, we might not have a real key, but LeadResearchAgent handles it
    asyncio.run(test_search_and_report())
