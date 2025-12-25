"""Timeline extraction from sources."""
import re
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
from pydantic import BaseModel, Field
import dateparser


class TimelineEvent(BaseModel):
    """Single timeline event."""
    date: str = Field(..., description="ISO format date YYYY-MM-DD")
    date_precision: str = Field(..., description="exact|day|month|year|relative")
    event: str = Field(..., description="Event description")
    source_url: str = Field(..., description="Source URL")
    attribution: Optional[str] = Field(None, description="Who said/reported this")
    confidence: float = Field(1.0, description="Confidence score 0-1")


def extract_timeline(
    transcripts: list,
    web_sources: list,
    claims: list = None
) -> List[TimelineEvent]:
    """
    Extract timeline events from all sources.

    Steps:
    1. Extract explicit dates using regex
    2. Extract relative dates and convert
    3. Extract events associated with dates
    4. Order chronologically
    5. Merge duplicate events
    """
    events = []

    # Date patterns with their precision levels
    date_patterns = [
        # ISO format: 2024-01-15
        (r'\b(\d{4}-\d{2}-\d{2})\b', 'exact'),
        # US format: 01/15/2024 or 01-15-2024
        (r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', 'day'),
        # Month Day, Year: January 15, 2024
        (r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b', 'exact'),
        # Month Year: January 2024
        (r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b', 'month'),
        # Relative: yesterday, today, last week
        (r'\b(yesterday|today|tomorrow|last\s+week|last\s+month|last\s+year|this\s+week|this\s+month)\b', 'relative'),
        # Time ago: "3 days ago", "2 weeks ago"
        (r'\b(\d+\s+(?:day|week|month|year)s?\s+ago)\b', 'relative'),
    ]

    # Process each source
    sources = web_sources + transcripts
    for source in sources:
        text = source.get('text', '') if isinstance(source, dict) else getattr(source, 'text', '')
        url = source.get('url', '') if isinstance(source, dict) else getattr(source, 'url', '')

        if not text:
            continue

        # Find all dates in text
        for pattern, precision in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)

                # Convert to ISO format
                iso_date = normalize_date(date_str, precision)
                if not iso_date:
                    continue

                # Extract surrounding context (event description)
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]

                # Clean up context to get event description
                event_desc = extract_event_from_context(context, date_str)

                # Create timeline event
                event = TimelineEvent(
                    date=iso_date,
                    date_precision=precision,
                    event=event_desc,
                    source_url=url,
                    confidence=0.9 if precision == 'exact' else 0.6
                )
                events.append(event)

    # Sort chronologically
    events.sort(key=lambda x: x.date)

    # Merge duplicates
    events = merge_duplicate_events(events)

    logger.info(f"Extracted {len(events)} timeline events from {len(sources)} sources")

    return events


def normalize_date(date_str: str, precision: str) -> Optional[str]:
    """Convert various date formats to ISO format."""

    if precision == 'relative':
        # Convert relative dates
        today = datetime.now()
        date_lower = date_str.lower()

        if 'yesterday' in date_lower:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'today' in date_lower:
            return today.strftime('%Y-%m-%d')
        elif 'tomorrow' in date_lower:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'last week' in date_lower or 'this week' in date_lower:
            return (today - timedelta(weeks=1)).strftime('%Y-%m-%d')
        elif 'last month' in date_lower or 'this month' in date_lower:
            return (today - timedelta(days=30)).strftime('%Y-%m-%d')
        elif 'last year' in date_lower:
            return (today - timedelta(days=365)).strftime('%Y-%m-%d')
        elif 'ago' in date_lower:
            # Parse "3 days ago" format
            try:
                parsed = dateparser.parse(date_str)
                if parsed:
                    return parsed.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                pass

    # Handle absolute dates using dateparser
    try:
        parsed = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'past'})
        if parsed:
            return parsed.strftime('%Y-%m-%d')
    except Exception as e:
        logger.debug(f"Failed to parse date '{date_str}': {e}")

    return None


def extract_event_from_context(context: str, date_str: str) -> str:
    """Extract event description from context around date."""
    # Extract the sentence or clause containing the date
    sentences = re.split(r'[.!?]', context)

    for sentence in sentences:
        if date_str in sentence:
            cleaned = sentence.strip()
            # Remove leading/trailing noise
            cleaned = re.sub(r'^[\s\W]+', '', cleaned)
            cleaned = re.sub(r'[\s\W]+$', '', cleaned)
            if len(cleaned) > 10:  # Only return if meaningful
                return cleaned[:200]  # Cap at 200 chars

    # Fallback: return context around the date
    index = context.find(date_str)
    if index != -1:
        start = max(0, index - 50)
        end = min(len(context), index + len(date_str) + 100)
        return context[start:end].strip()[:200]

    return context[:100]  # Ultimate fallback


def merge_duplicate_events(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """Merge events that refer to the same thing."""
    if not events:
        return []

    merged = []
    seen = {}

    for event in events:
        # Create key from date and first 50 chars of event
        event_preview = event.event[:50].lower().strip()
        key = (event.date, event_preview)

        if key not in seen:
            seen[key] = event
            merged.append(event)
        else:
            # Merge: keep higher confidence event
            existing = seen[key]
            if event.confidence > existing.confidence:
                # Replace with higher confidence version
                merged.remove(existing)
                merged.append(event)
                seen[key] = event

    return merged


def generate_timeline_markdown(events: List[TimelineEvent]) -> str:
    """Generate markdown timeline from events."""
    if not events:
        return "# Timeline\n\nNo timeline events extracted.\n"

    lines = ["# Timeline\n"]
    lines.append(f"*{len(events)} events extracted and ordered chronologically*\n")

    for event in events:
        lines.append(f"## {event.date}")
        lines.append(f"**Precision:** {event.date_precision} | **Confidence:** {event.confidence:.2f}\n")
        lines.append(f"{event.event}\n")
        if event.attribution:
            lines.append(f"*Attribution: {event.attribution}*\n")
        lines.append(f"**Source:** {event.source_url}\n")
        lines.append("---\n")

    return "\n".join(lines)
