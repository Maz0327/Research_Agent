"""Test script for v2 API integrations."""
import os
import sys
from loguru import logger

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_exa():
    """Test Exa.ai client initialization and basic search."""
    try:
        from backend.integrations.exa_client import ExaSearchClient
        client = ExaSearchClient()
        logger.info("✅ Exa client initialized successfully")

        # Try a simple search
        result = client.search("artificial intelligence", num_results=3)
        logger.info(f"✅ Exa search successful: {len(result.get('results', []))} results")
        return True
    except Exception as e:
        logger.error(f"❌ Exa client failed: {e}")
        return False

def test_brave():
    """Test Brave Search client."""
    try:
        from backend.integrations.brave_search_client import BraveSearchClient
        client = BraveSearchClient()
        logger.info("✅ Brave Search client initialized successfully")

        # Try a simple search
        result = client.search("python programming", count=3)
        logger.info(f"✅ Brave search successful: {len(result.get('results', []))} results")
        return True
    except Exception as e:
        logger.error(f"❌ Brave Search client failed: {e}")
        return False

def test_jina():
    """Test Jina Reader client."""
    try:
        from backend.integrations.jina_reader_client import JinaReaderClient
        client = JinaReaderClient()
        logger.info("✅ Jina Reader client initialized successfully")

        # Try extracting a simple page
        result = client.extract("https://example.com")
        logger.info(f"✅ Jina extraction successful: {len(result.get('content', ''))} chars")
        return True
    except Exception as e:
        logger.error(f"❌ Jina Reader client failed: {e}")
        return False

def test_claimbuster():
    """Test ClaimBuster client."""
    try:
        from backend.integrations.claimbuster_client import ClaimBusterClient
        client = ClaimBusterClient()
        logger.info("✅ ClaimBuster client initialized successfully")

        # Try scoring a claim
        result = client.score_claims(["The sky is blue"])
        logger.info(f"✅ ClaimBuster scoring successful: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ ClaimBuster client failed: {e}")
        return False

def test_google_factcheck():
    """Test Google Fact Check client."""
    try:
        from backend.integrations.google_factcheck_client import GoogleFactCheckClient
        client = GoogleFactCheckClient()
        logger.info("✅ Google Fact Check client initialized successfully")

        # Try searching for fact-checks
        result = client.search("climate change", page_size=3)
        logger.info(f"✅ Google Fact Check search successful: {len(result.get('fact_checks', []))} results")
        return True
    except Exception as e:
        logger.error(f"❌ Google Fact Check client failed: {e}")
        return False

def test_gdelt():
    """Test GDELT client."""
    try:
        from backend.integrations.gdelt_client import GDELTClient
        client = GDELTClient()
        logger.info("✅ GDELT client initialized successfully")

        # Try searching for news
        result = client.search_articles("technology", max_records=3)
        logger.info(f"✅ GDELT search successful: {len(result.get('articles', []))} articles")
        return True
    except Exception as e:
        logger.error(f"❌ GDELT client failed: {e}")
        return False

def test_semantic_scholar():
    """Test Semantic Scholar client."""
    try:
        from backend.integrations.semantic_scholar_client import SemanticScholarClient
        client = SemanticScholarClient()
        logger.info("✅ Semantic Scholar client initialized successfully")

        # Try searching for papers
        result = client.search("machine learning", limit=3)
        logger.info(f"✅ Semantic Scholar search successful: {len(result.get('papers', []))} papers")
        return True
    except Exception as e:
        logger.error(f"❌ Semantic Scholar client failed: {e}")
        return False

def test_whisper():
    """Test Whisper client initialization only (don't download/transcribe)."""
    try:
        from backend.integrations.whisper_client import WhisperTranscriptionClient
        client = WhisperTranscriptionClient()
        logger.info("✅ Whisper client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Whisper client failed: {e}")
        return False

def main():
    """Run all API tests."""
    logger.info("=" * 60)
    logger.info("Testing v2 API Integrations")
    logger.info("=" * 60)

    results = {
        "Exa.ai": test_exa(),
        "Brave Search": test_brave(),
        "Jina Reader": test_jina(),
        "ClaimBuster": test_claimbuster(),
        "Google Fact Check": test_google_factcheck(),
        "GDELT": test_gdelt(),
        "Semantic Scholar": test_semantic_scholar(),
        "Whisper": test_whisper(),
    }

    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    for api, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {api}")

    passed = sum(results.values())
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} APIs passed")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
