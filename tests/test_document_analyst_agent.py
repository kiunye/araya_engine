"""
Tests for Document Analyst Agent.
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from araya.agents.document_analyst_agent import DocumentAnalystAgent, DocumentAnalystResult

def test_initialization():
    """Test that the agent can be initialized."""
    agent = DocumentAnalystAgent()
    assert agent is not None
    assert agent.pdf_ingestor is not None
    assert agent.audio_ingestor is not None
    assert agent.image_ingestor is not None
    print("✓ Agent initialization test passed")

def test_parse_instruction():
    """Test instruction parsing."""
    agent = DocumentAnalystAgent()
    
    # Test PDF parsing
    path, type_, obj = agent._parse_instruction("Analyze pdf at /docs/report.pdf for financial analysis")
    assert path == "/docs/report.pdf"
    assert type_ == "pdf"
    assert obj == "financial analysis"
    
    # Test audio parsing
    path, type_, obj = agent._parse_instruction("Transcribe audio from /recordings/meeting.mp3 for key decisions")
    assert path == "/recordings/meeting.mp3"
    assert type_ == "audio"
    
    # Test image parsing
    path, type_, obj = agent._parse_instruction("Describe image at /screenshots/dashboard.png for UI analysis")
    assert path == "/screenshots/dashboard.png"
    assert type_ == "image"
    
    print("✓ Instruction parsing test passed")

def test_error_result():
    """Test error result creation."""
    agent = DocumentAnalystAgent()
    result = agent._error_result("Test error message")
    
    assert result["findings"] == []
    assert result["research_objects"] == []
    assert "errors" in result
    
    print("✓ Error result test passed")

def test_document_analyst_result_type():
    """Test that DocumentAnalystResult TypedDict works correctly."""
    result: DocumentAnalystResult = {
        "findings": [],
        "research_objects": [],
        "analysis_summary": "Test summary"
    }
    assert result["analysis_summary"] == "Test summary"
    print("✓ DocumentAnalystResult TypedDict test passed")

if __name__ == "__main__":
    test_initialization()
    test_parse_instruction()
    test_error_result()
    test_document_analyst_result_type()
    print("\n✅ All tests passed!")