"""Perplexity AI API client for research map and source discovery."""
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import httpx
from httpx import HTTPStatusError, RequestError
from loguru import logger

from backend.config import require_perplexity, MissingRequiredSettingError
from backend.models.job_config import JobConfig
from backend.models.source import SourceItem, SourceType
from backend.utils.error_handling import sanitize_error_message

# Constants
PERPLEXITY_API_TIMEOUT = 60.0  # seconds - increased for complex queries
PERPLEXITY_DEFAULT_MODEL = "sonar"  # Updated to current Perplexity API model (Jan 2025)
MAX_KEY_TERMS = 20
MAX_ANGLES = 10


def _perplexity_search(query: str, model: str = PERPLEXITY_DEFAULT_MODEL) -> dict:
    """
    Make a search request to Perplexity API.
    
    Args:
        query: Search query string
        model: Perplexity model to use
        
    Returns:
        API response as dict
        
    Raises:
        MissingRequiredSettingError: If Perplexity API key is missing
        httpx.HTTPError: If API request fails
    """
    settings = require_perplexity()
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.perplexity_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a research assistant. Provide URLs and citations for your answers.",
            },
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
        "max_tokens": 4000,
    }
    
    logger.debug(f"Perplexity query: {query[:100]}...")
    
    try:
        with httpx.Client(timeout=PERPLEXITY_API_TIMEOUT) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Log specific HTTP errors with status codes
        error_detail = f"HTTP {e.response.status_code}"
        try:
            error_body = e.response.json()
            if isinstance(error_body, dict):
                error_msg = error_body.get('error', {}).get('message', '') or e.response.text[:200]
                error_detail += f": {error_msg}"
        except Exception:
            error_detail += f": {e.response.text[:200]}"
        sanitized_error = sanitize_error_message(RuntimeError(error_detail), include_type=False)
        logger.error(f"Perplexity API HTTP error: {sanitized_error}")
        raise RuntimeError(f"Perplexity API request failed: {sanitized_error}") from e
    except RequestError as e:
        # Network/connection errors
        sanitized_error = sanitize_error_message(e, include_type=False)
        logger.error(f"Perplexity API request error: {sanitized_error}")
        raise RuntimeError(f"Perplexity API request failed: {sanitized_error}") from e


def _extract_urls_from_response(response: dict) -> list[dict]:
    """
    Extract URLs and citations from Perplexity API response.
    
    Args:
        response: Perplexity API response dict
        
    Returns:
        List of dicts with 'url', 'title', and optionally 'snippet'
    """
    urls = []
    
    # Perplexity responses may include citations in the response content
    # and also in a 'citations' field
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    # Extract URLs from content using regex
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
    found_urls = re.findall(url_pattern, content)
    
    # Also check citations if available
    citations = response.get("citations", [])
    
    seen = set()
    for url in found_urls + citations:
        url = url.strip().rstrip('.,;:!?)')
        if url and url not in seen and _is_valid_source_url(url):
            seen.add(url)
            urls.append({"url": url, "title": None, "snippet": None})
    
    return urls


def _is_valid_source_url(url: str) -> bool:
    """
    Check if URL is valid for our source types.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Filter out obvious non-content URLs
    invalid_patterns = [
        r'^https?://(www\.)?(google|facebook|twitter|x\.com|linkedin|instagram)\.',
        r'^https?://[^/]+/search\?',
        r'^https?://[^/]+/results\?',
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return False
    
    return True


def _classify_source_type(url: str) -> SourceType:
    """
    Classify URL into source type.
    
    Args:
        url: URL string
        
    Returns:
        SourceType enum value
    """
    url_lower = url.lower()
    
    # Government sources
    if any(domain in url_lower for domain in ['.gov', '.mil', 'archives.gov']):
        return SourceType.GOV
    
    # Academic sources
    if any(domain in url_lower for domain in ['.edu', 'arxiv.org', 'scholar.google.com', 'pubmed', 'doi.org', 'jstor']):
        return SourceType.ACADEMIC
    
    # Reddit
    if 'reddit.com' in url_lower:
        return SourceType.REDDIT
    
    # News sources (common domains)
    news_domains = [
        'bbc.com', 'cnn.com', 'reuters.com', 'ap.org', 'nytimes.com',
        'washingtonpost.com', 'theguardian.com', 'wsj.com', 'npr.org',
        'bloomberg.com', 'forbes.com', 'time.com', 'news.yahoo.com',
    ]
    if any(domain in url_lower for domain in news_domains):
        return SourceType.NEWS
    
    # Default to web
    return SourceType.WEB


def _infer_angle_from_content(title: Optional[str], url: str) -> Optional[str]:
    """
    Infer editorial angle from title/URL (simple heuristics).
    
    Args:
        title: Title of the source
        url: URL of the source
        
    Returns:
        Inferred angle or None
    """
    text = (title or "").lower() + " " + url.lower()
    
    # Simple keyword-based angle detection
    if any(word in text for word in ['debunk', 'fact-check', 'false', 'misinformation']):
        return "fact-checking"
    if any(word in text for word in ['breaking', 'report', 'investigation']):
        return "investigative"
    if any(word in text for word in ['opinion', 'editorial', 'op-ed']):
        return "opinion"
    if any(word in text for word in ['official', 'government', 'statement']):
        return "official"
    
    return None


def research_map(job: JobConfig) -> dict:
    """
    Generate a research map using Perplexity AI.
    
    This function analyzes the job topic and generates:
    - research_map_md: Markdown document outlining research angles
    - angles: List of research angles to explore
    - key_terms: List of key terms to use in searches
    
    Args:
        job: JobConfig with topic and mode
        
    Returns:
        Dict with 'research_map_md', 'angles', 'key_terms'
    """
    try:
        settings = require_perplexity()
    except MissingRequiredSettingError:
        logger.warning("Perplexity API key not configured. Returning basic research map.")
        return {
            "research_map_md": f"# Research Map\n\n## Topic\n{job.topic}\n\n*Research angles require Perplexity API key.*",
            "angles": ["general"],
            "key_terms": job.topic.split(),
        }
    
    query = f"""Create a research map for this topic: {job.topic}

Research mode: {job.mode}

Provide a list of 5-10 specific research angles to explore. Each angle should be a concrete topic or perspective, not a category or header.

For example:
- "Accelerator pedal defect recall April 2024"
- "Trim attachment issues and consumer complaints"
- "NHTSA investigation and response"

Format your response as a numbered list of specific research angles."""
    
    try:
        response = _perplexity_search(query)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Extract angles from numbered lists and bullet points
        angles = []
        key_terms = job.topic.split()  # Basic key terms from topic

        # Filter out meta-headers and section titles
        meta_keywords = [
            'key research', 'important key', 'structured research',
            'research plan', 'perspectives to explore', 'terms, entities',
            'phase 1', 'phase 2', 'step 1', 'step 2'
        ]

        # Extract angles from numbered lists and bullet points
        angle_patterns = [
            r'^\d+\.\s+(.+?)$',  # Numbered lists
            r'^[-*]\s+(.+?)$',  # Bullet points
        ]

        for line in content.split('\n'):
            line_stripped = line.strip()
            for pattern in angle_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    angle_text = match.group(1).strip()
                    # Filter out meta-headers and very long/short lines
                    is_meta = any(keyword in angle_text.lower() for keyword in meta_keywords)
                    is_valid_length = 10 < len(angle_text) < 150

                    if not is_meta and is_valid_length:
                        # Clean up quotes if present
                        angle_text = angle_text.strip('"').strip("'")
                        angles.append(angle_text)
                        break

        # Dedupe angles while preserving order
        angles = list(dict.fromkeys(angles))
        
        # If no angles found, create default
        if not angles:
            angles = ["general investigation", "fact-checking", "timeline"]
        
        # Extract key terms from content (simple: capitalize words)
        words = re.findall(r'\b[A-Z][a-z]+\b', content)
        key_terms.extend([w for w in words if len(w) > 3])
        key_terms = list(dict.fromkeys(key_terms))[:20]  # Limit to 20 unique terms
        
        return {
            "research_map_md": content or f"# Research Map\n\n## Topic\n{job.topic}\n\n*No content generated.*",
            "angles": angles[:MAX_ANGLES],
            "key_terms": key_terms[:MAX_KEY_TERMS],
        }
    
    except (HTTPStatusError, RequestError, RuntimeError) as e:
        # Already logged by _perplexity_search
        error_msg = str(e).split(":")[-1].strip() if ":" in str(e) else str(e)
        logger.error(f"Failed to generate research map: {type(e).__name__}: {error_msg}")
        return {
            "research_map_md": f"# Research Map\n\n## Topic\n{job.topic}\n\n*Error generating research map: {error_msg}*",
            "angles": ["general"],
            "key_terms": job.topic.split(),
        }
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error generating research map: {e}")
        return {
            "research_map_md": f"# Research Map\n\n## Topic\n{job.topic}\n\n*Error generating research map: {str(e)}*",
            "angles": ["general"],
            "key_terms": job.topic.split(),
        }


def source_shortlist(
    job: JobConfig,
    angles: list[str],
    key_terms: list[str],
) -> dict:
    """
    Generate a source shortlist using Perplexity AI.
    
    Searches for sources based on job configuration, angles, and key terms.
    Returns URLs grouped by angle, deduplicated, and capped to budget.
    
    Args:
        job: JobConfig with topic, sources config, and budgets
        angles: List of research angles to search
        key_terms: List of key terms to include in searches
        
    Returns:
        Dict with 'urls' (list of SourceItem) and 'shortlist_md' (markdown)
    """
    try:
        settings = require_perplexity()
    except MissingRequiredSettingError:
        logger.warning("Perplexity API key not configured. Returning empty shortlist.")
        return {
            "urls": [],
            "shortlist_md": "# Source Shortlist\n\n*Perplexity API key required for source discovery.*",
        }
    
    all_sources: list[SourceItem] = []
    seen_urls: set[str] = set()
    sources_by_angle: dict[str, list[SourceItem]] = defaultdict(list)
    
    # Build search queries based on enabled source types
    queries_to_run = []
    
    # Build base query with key terms
    base_terms = " ".join(key_terms[:5]) if key_terms else job.topic  # Use top 5 key terms or topic
    
    # Web search (always enabled if web=True)
    if job.sources.web:
        # Use angles if available, otherwise just use topic
        search_angles = angles[:5] if angles else [""]  # Limit to top 5 angles
        for angle in search_angles:
            query = f"{base_terms} {angle}".strip()
            queries_to_run.append(("web", angle or "general", query))
    
    # News search
    if job.sources.include_news:
        for angle in angles[:3]:  # Fewer queries for news
            query = f"{base_terms} {angle} news article"
            queries_to_run.append(("news", angle, query))
    
    # Academic search
    if job.sources.include_academic:
        for angle in angles[:2]:  # Even fewer for academic
            query = f"{base_terms} {angle} research study academic"
            queries_to_run.append(("academic", angle, query))
    
    # Government/public records
    if job.sources.include_gov:
        for angle in angles[:2]:
            query = f"{base_terms} {angle} site:.gov OR site:archives.gov OR site:.mil"
            queries_to_run.append(("gov", angle, query))
    
    # Reddit (public threads)
    if job.sources.include_reddit_public:
        for angle in angles[:2]:
            query = f"{base_terms} {angle} site:reddit.com"
            queries_to_run.append(("reddit", angle, query))
    
    # Execute searches
    for source_type_str, angle, query in queries_to_run:
        if len(all_sources) >= job.budgets.max_web_urls:
            logger.info(f"Reached budget limit of {job.budgets.max_web_urls} URLs")
            break
        
        try:
            response = _perplexity_search(query)
            url_items = _extract_urls_from_response(response)
            
            for item in url_items:
                url = item["url"]
                
                # Dedupe
                if url in seen_urls:
                    continue
                
                # Check if URL matches source type
                classified_type = _classify_source_type(url)
                expected_type = SourceType[source_type_str.upper()]
                
                # Allow some flexibility (e.g., news URLs can be in web search)
                if classified_type != expected_type and source_type_str == "web":
                    # Web search can return any type
                    pass
                elif classified_type != expected_type and source_type_str != "web":
                    # For specific searches, prefer matching types but allow close matches
                    if classified_type == SourceType.WEB and expected_type in [SourceType.NEWS, SourceType.GOV]:
                        # Allow web URLs in news/gov searches
                        pass
                    else:
                        continue
                
                # Check budget
                if len(all_sources) >= job.budgets.max_web_urls:
                    break
                
                # Create SourceItem
                source = SourceItem(
                    url=url,
                    title=item.get("title") or _extract_title_from_url(url),
                    source_type=classified_type,
                    published_at=None,  # Would need to fetch to get this
                    text=item.get("snippet"),
                    angle=_infer_angle_from_content(item.get("title"), url) or angle,
                )
                
                all_sources.append(source)
                seen_urls.add(url)
                sources_by_angle[angle].append(source)
        
        except (HTTPStatusError, RequestError, RuntimeError) as e:
            # Already logged by _perplexity_search
            logger.warning(f"Failed to search for {source_type_str} angle '{angle}': {type(e).__name__}")
            continue
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error searching for {source_type_str} angle '{angle}': {e}")
            continue
    
    # Generate markdown shortlist
    shortlist_md = _generate_shortlist_markdown(job, sources_by_angle, angles)
    
    return {
        "urls": all_sources[:job.budgets.max_web_urls],  # Enforce budget
        "shortlist_md": shortlist_md,
    }


def _extract_title_from_url(url: str) -> str:
    """Extract a basic title hint from URL."""
    # Remove protocol and domain
    path = url.split('//', 1)[-1].split('/', 1)[-1] if '//' in url else url
    # Replace hyphens/slashes with spaces and capitalize
    title = path.replace('-', ' ').replace('/', ' ').replace('_', ' ')
    # Take first few words
    words = title.split()[:8]
    return ' '.join(words).title()


def _generate_shortlist_markdown(
    job: JobConfig,
    sources_by_angle: dict[str, list[SourceItem]],
    all_angles: list[str],
) -> str:
    """
    Generate markdown shortlist grouped by angle.
    
    Args:
        job: JobConfig
        sources_by_angle: Dict mapping angle to list of SourceItems
        all_angles: List of all research angles
        
    Returns:
        Markdown string
    """
    lines = [
        "# Source Shortlist",
        "",
        f"**Topic:** {job.topic}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
    ]
    
    # Group sources by angle
    for angle in all_angles:
        sources = sources_by_angle.get(angle, [])
        if not sources:
            continue
        
        lines.append(f"## {angle}")
        lines.append("")
        
        # Group by source type within angle
        by_type: dict[SourceType, list[SourceItem]] = defaultdict(list)
        for source in sources:
            by_type[source.source_type].append(source)
        
        for source_type in [SourceType.NEWS, SourceType.GOV, SourceType.ACADEMIC, SourceType.REDDIT, SourceType.WEB]:
            type_sources = by_type.get(source_type, [])
            if not type_sources:
                continue
            
            lines.append(f"### {source_type.value.title()} Sources")
            lines.append("")
            
            for source in type_sources:
                title = source.title or "Untitled"
                angle_note = f" *({source.angle})*" if source.angle and source.angle != angle else ""
                lines.append(f"- [{title}]({source.url}){angle_note}")
            
            lines.append("")
    
    # Missing angles section
    angles_with_sources = set(sources_by_angle.keys())
    missing_angles = [angle for angle in all_angles if angle not in angles_with_sources]
    
    if missing_angles:
        lines.append("## Missing Angles to Check")
        lines.append("")
        lines.append("The following research angles need more sources:")
        lines.append("")
        for angle in missing_angles:
            lines.append(f"- {angle}")
        lines.append("")
    
    # Summary
    total_sources = sum(len(sources) for sources in sources_by_angle.values())
    lines.append("---")
    lines.append("")
    lines.append(f"**Total sources:** {total_sources}")
    lines.append(f"**Budget limit:** {job.budgets.max_web_urls}")
    
    return "\n".join(lines)

