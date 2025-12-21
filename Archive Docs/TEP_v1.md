# Technical Execution Plan (TEP) v1.0 - REVISED
## Research Agent - Hybrid Implementation Guide for Claude Sonnet

### Document Purpose
This TEP provides step-by-step technical implementation for the REVISED hybrid approach: comprehensive research gathering + documentary intelligence layer, producing dual outputs (NotebookLM packet + Documentary Blueprint).

---

## Pre-Implementation Checklist

**SONNET: Before writing ANY code, confirm these:**
- [ ] Read V1_Analysis.md completely
- [ ] Read PRD_v1.md completely
- [ ] Read this TEP completely
- [ ] Run database migrations FIRST
- [ ] Create git branch: `feature/vision-alignment-v1`
- [ ] Verify Redis is running
- [ ] Verify all API keys are in .env

---

## Phase 1: Database & Configuration [Days 1-2]

### Step 1.1: Database Migrations

**CRITICAL: Run these BEFORE any code changes**

```bash
# Connect to Supabase and run:
```

```sql
-- File: migrations/001_cleanup_redundant_fields.sql
ALTER TABLE jobs DROP COLUMN IF EXISTS topic;
ALTER TABLE jobs DROP COLUMN IF EXISTS result;

-- File: migrations/002_fix_pipeline_modes.sql
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_pipeline_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_pipeline_check
  CHECK (pipeline IN ('quick', 'standard', 'deep', 'investigation'));

-- File: migrations/003_add_vision_fields.sql
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS timeline_events JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS entities JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS manual_guidance JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS reddit_posts JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS notebooklm_packet_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_sources INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_claims INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS api_costs JSONB DEFAULT '{}'::jsonb;

-- File: migrations/004_add_indexes.sql
CREATE INDEX IF NOT EXISTS idx_jobs_entities ON jobs USING gin(entities);
CREATE INDEX IF NOT EXISTS idx_jobs_timeline ON jobs USING gin(timeline_events);
```

### Step 1.2: Update Configuration Models

**File: `backend/models/job_config.py`**

**SONNET WARNING: DO NOT just rename the existing modes. CREATE new proper modes:**

```python
from enum import Enum

class DocumentaryMode(str, Enum):
    """Documentary-specific research modes."""
    BREAKING_NEWS = "breaking_news"      # Fast, recent events
    INVESTIGATION = "investigation"      # Deep dive with verification
    PROFILE = "profile"                 # Single entity focus
    CONTROVERSY = "controversy"         # Multiple viewpoints

def get_mode_config(mode: DocumentaryMode) -> dict:
    """Get configuration for each documentary mode."""
    configs = {
        DocumentaryMode.BREAKING_NEWS: {
            "focus": "recency_and_speed",
            "time_window_hours": 72,
            "sources": {
                "reddit": {"enabled": True, "sort": "new", "limit": 20},
                "perplexity": {"enabled": True, "queries": 3},
                "youtube": {"enabled": False},  # Too slow for breaking news
            },
            "timeline_precision": "hourly",
            "documentary_output": "timeline_focused",
            "max_duration_minutes": 10,
            "max_cost_usd": 2.0
        },
        DocumentaryMode.INVESTIGATION: {
            "focus": "verification_and_connections",
            "time_window_hours": None,  # No limit
            "sources": {
                "reddit": {"enabled": True, "sort": "top", "limit": 50},
                "perplexity": {"enabled": True, "queries": 15},
                "youtube": {"enabled": True, "max_videos": 30},
            },
            "timeline_precision": "exact",
            "documentary_output": "evidence_based",
            "validation_all_claims": True,
            "entity_relationship_mapping": True,
            "max_duration_minutes": 45,
            "max_cost_usd": 15.0
        },
        DocumentaryMode.PROFILE: {
            "focus": "single_entity_deep_dive",
            "sources": {
                "youtube": {"enabled": True, "search_entity_name": True},
                "perplexity": {"enabled": True, "entity_focused": True},
                "reddit": {"enabled": True, "search_mentions": True},
            },
            "timeline_type": "biographical",
            "documentary_output": "character_study",
            "relationship_mapping": True,
            "max_duration_minutes": 30,
            "max_cost_usd": 8.0
        },
        DocumentaryMode.CONTROVERSY: {
            "focus": "balanced_perspectives",
            "sources": {
                "reddit": {"enabled": True, "include_controversial": True},
                "perplexity": {"enabled": True, "get_all_sides": True},
                "youtube": {"enabled": True, "diverse_channels": True},
            },
            "timeline_type": "claim_counterclaim",
            "documentary_output": "balanced_presentation",
            "validate_all_sides": True,
            "max_duration_minutes": 30,
            "max_cost_usd": 10.0
        }
    }
    return configs.get(mode, configs[DocumentaryMode.INVESTIGATION])
```

### Step 1.3: Add Environment Variables

**File: `.env`**

```bash
# Reddit API (NEW)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=ResearchAgent/1.0 by YourUsername

# API Models (NEW - Cost Optimization)
OPENAI_DEFAULT_MODEL=gpt-4o
OPENAI_MINI_MODEL=gpt-4o-mini
PERPLEXITY_DEFAULT_MODEL=sonar
PERPLEXITY_PRO_MODEL=sonar-pro

# Cost tracking (VALIDATED January 2025)
# GPT-4o pricing
OPENAI_GPT4O_INPUT_COST_PER_1M=5.00
OPENAI_GPT4O_OUTPUT_COST_PER_1M=15.00
# GPT-4o-mini pricing (90% cheaper)
OPENAI_GPT4O_MINI_INPUT_COST_PER_1M=0.15
OPENAI_GPT4O_MINI_OUTPUT_COST_PER_1M=0.60
# Perplexity pricing (varies by model)
PERPLEXITY_SONAR_COST_PER_1M=0.20
PERPLEXITY_SONAR_PRO_COST_PER_1M=3.00
# YouTube is FREE (10,000 units/day quota)
YOUTUBE_QUOTA_LIMIT=10000
# Reddit is FREE for non-commercial use
REDDIT_FREE_TIER_QPM=100
```

---

## Phase 2: Core Feature Implementation [Days 3-7]

### Step 2.1: Timeline Extraction Implementation

**SONNET: This does NOT exist. You must CREATE it from scratch.**

**File: `backend/pipeline/timeline.py`** (CREATE NEW FILE)

```python
"""Timeline extraction from sources."""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
from pydantic import BaseModel, Field

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

    SONNET: Implement this completely. Steps:
    1. Extract explicit dates using regex
    2. Extract relative dates and convert
    3. Extract events associated with dates
    4. Order chronologically
    5. Merge duplicate events
    """
    events = []

    # Date patterns
    date_patterns = [
        # ISO format: 2024-01-15
        (r'\b(\d{4}-\d{2}-\d{2})\b', 'exact'),
        # US format: 01/15/2024 or 01-15-2024
        (r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', 'exact'),
        # Month Day, Year: January 15, 2024
        (r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b', 'exact'),
        # Relative: yesterday, today, last week
        (r'\b(yesterday|today|tomorrow|last\s+week|last\s+month|last\s+year)\b', 'relative'),
    ]

    # Process each source
    for source in web_sources + transcripts:
        text = source.get('text', '')
        url = source.get('url', '')

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

    return events

def normalize_date(date_str: str, precision: str) -> Optional[str]:
    """Convert various date formats to ISO format."""
    # SONNET: Implement date normalization
    # Handle formats like "January 15, 2024", "last week", etc.
    # Return YYYY-MM-DD format or None if can't parse

    if precision == 'relative':
        # Convert relative dates
        today = datetime.now()
        if 'yesterday' in date_str.lower():
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'last week' in date_str.lower():
            return (today - timedelta(weeks=1)).strftime('%Y-%m-%d')
        # Add more relative date handling

    # Handle absolute dates
    # TODO: Implement parsing for various formats

    return None

def extract_event_from_context(context: str, date_str: str) -> str:
    """Extract event description from context around date."""
    # SONNET: Extract the sentence or clause containing the date
    # Clean it up to be a readable event description
    sentences = context.split('.')
    for sentence in sentences:
        if date_str in sentence:
            return sentence.strip()
    return context[:100]  # Fallback

def merge_duplicate_events(events: List[TimelineEvent]) -> List[TimelineEvent]:
    """Merge events that refer to the same thing."""
    # SONNET: Implement deduplication logic
    # Events on same date with similar descriptions should be merged
    merged = []
    seen = set()

    for event in events:
        key = (event.date, event.event[:50])  # Simple dedup by date + start of description
        if key not in seen:
            seen.add(key)
            merged.append(event)

    return merged
```

### Step 2.2: Entity Extraction Implementation

**SONNET: This also does NOT exist. CREATE it.**

**File: `backend/pipeline/entities.py`** (CREATE NEW FILE)

```python
"""Entity extraction from sources."""
import re
from collections import defaultdict
from typing import Dict, List, Set
from loguru import logger
import spacy

# Load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm")
except:
    logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

class EntityExtractor:
    """Extract and resolve entities from text."""

    def extract_entities(
        self,
        transcripts: list,
        web_sources: list,
        claims: list = None
    ) -> Dict:
        """
        Extract people, organizations, and locations.

        SONNET: Complete implementation:
        1. Use spaCy NER for initial extraction
        2. Use regex patterns for missed entities
        3. Resolve aliases and variations
        4. Count mentions and determine importance
        """

        entities = {
            "people": [],
            "organizations": [],
            "locations": [],
            "relationships": []
        }

        # Collect all text
        all_texts = []
        for source in transcripts + web_sources:
            if 'text' in source:
                all_texts.append(source['text'])

        # Extract using spaCy
        if nlp:
            for text in all_texts:
                doc = nlp(text[:1000000])  # Limit to 1M chars for performance

                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        entities["people"].append({
                            "name": ent.text,
                            "context": text[max(0, ent.start_char-50):ent.end_char+50]
                        })
                    elif ent.label_ == "ORG":
                        entities["organizations"].append({
                            "name": ent.text,
                            "context": text[max(0, ent.start_char-50):ent.end_char+50]
                        })
                    elif ent.label_ in ["GPE", "LOC"]:
                        entities["locations"].append({
                            "name": ent.text,
                            "context": text[max(0, ent.start_char-50):ent.end_char+50]
                        })

        # Fallback: regex patterns
        person_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last
            r'\b(Mr\.|Ms\.|Dr\.|Mrs\.) ([A-Z][a-z]+)\b',  # Title Name
        ]

        for text in all_texts:
            for pattern in person_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entities["people"].append({
                        "name": match.group(0),
                        "context": text[max(0, match.start()-50):match.end()+50]
                    })

        # Deduplicate and resolve aliases
        entities = self._resolve_aliases(entities)

        # Count mentions and rank by importance
        entities = self._rank_entities(entities)

        return entities

    def _resolve_aliases(self, entities: Dict) -> Dict:
        """Resolve name variations to canonical forms."""
        # SONNET: Implement alias resolution
        # "Candace Owens", "Candace", "Ms. Owens" -> single entity

        resolved = defaultdict(list)

        for category in ["people", "organizations", "locations"]:
            seen_names = {}

            for entity in entities.get(category, []):
                name = entity["name"]
                canonical = self._get_canonical_name(name, seen_names)

                if canonical not in seen_names:
                    seen_names[canonical] = {
                        "name": canonical,
                        "aliases": {name},
                        "mentions": 1,
                        "contexts": [entity.get("context", "")]
                    }
                else:
                    seen_names[canonical]["aliases"].add(name)
                    seen_names[canonical]["mentions"] += 1
                    seen_names[canonical]["contexts"].append(entity.get("context", ""))

            resolved[category] = list(seen_names.values())

        return dict(resolved)

    def _get_canonical_name(self, name: str, seen_names: Dict) -> str:
        """Get canonical form of a name."""
        # Simple implementation - could be enhanced
        name = name.strip()

        # Check if this is a substring of existing names
        for canonical in seen_names:
            if name in canonical or canonical in name:
                return canonical

        return name

    def _rank_entities(self, entities: Dict) -> Dict:
        """Rank entities by importance (mention count)."""
        for category in entities:
            entities[category].sort(key=lambda x: x.get("mentions", 0), reverse=True)
        return entities
```

### Step 2.3: Reddit Integration

**File: `backend/integrations/reddit_client.py`** (CREATE NEW FILE)

```python
"""Reddit API integration using PRAW."""
import os
from typing import List, Dict, Optional
from datetime import datetime
import praw
from prawcore.exceptions import ResponseException
from loguru import logger
from backend.config import get_settings

class RedditClient:
    """Reddit API client for fetching posts and comments."""

    def __init__(self):
        """Initialize Reddit client with credentials."""
        settings = get_settings()

        # SONNET: Use environment variables, not hardcoded values
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "ResearchAgent/1.0")
        )
        self.reddit.read_only = True  # We only need read access

    def search_subreddit(
        self,
        subreddit_name: str,
        query: str,
        limit: int = 10,
        sort: str = "relevance",  # relevance, hot, top, new
        time_filter: str = "all"   # all, day, week, month, year
    ) -> List[Dict]:
        """
        Search a subreddit for posts matching query.

        Returns list of post data including comments.
        """
        posts = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Search posts
            search_results = subreddit.search(
                query,
                sort=sort,
                time_filter=time_filter,
                limit=limit
            )

            for submission in search_results:
                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "text": submission.selftext,
                    "subreddit": subreddit_name,
                    "comments": []
                }

                # Fetch top comments
                submission.comments.replace_more(limit=0)  # Remove MoreComments
                for comment in submission.comments.list()[:20]:  # Top 20 comments
                    if hasattr(comment, 'body'):
                        post_data["comments"].append({
                            "author": str(comment.author) if comment.author else "[deleted]",
                            "body": comment.body,
                            "score": comment.score,
                            "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat()
                        })

                posts.append(post_data)

        except ResponseException as e:
            logger.error(f"Reddit API error searching r/{subreddit_name}: {e}")
        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")

        return posts

    def search_multiple_subreddits(
        self,
        query: str,
        subreddits: List[str] = None,
        limit_per_sub: int = 5
    ) -> List[Dict]:
        """Search multiple subreddits for a query."""
        if not subreddits:
            # Default subreddits for news/politics
            subreddits = [
                "politics",
                "news",
                "worldnews",
                "OutOfTheLoop",
                "NeutralPolitics"
            ]

        all_posts = []
        for sub in subreddits:
            logger.info(f"Searching r/{sub} for: {query}")
            posts = self.search_subreddit(sub, query, limit=limit_per_sub)
            all_posts.extend(posts)

        return all_posts

def extract_reddit_content(posts: List[Dict]) -> str:
    """Convert Reddit posts to markdown for processing."""
    lines = ["# Reddit Discussions\n"]

    for post in posts:
        lines.append(f"## {post['title']}")
        lines.append(f"*r/{post['subreddit']} | Score: {post['score']} | {post['created_utc']}*\n")
        lines.append(f"**Link:** {post['url']}\n")

        if post['text']:
            lines.append(f"{post['text']}\n")

        if post['comments']:
            lines.append("### Top Comments:\n")
            for comment in post['comments'][:5]:
                lines.append(f"> **{comment['author']} ({comment['score']} points):**")
                lines.append(f"> {comment['body']}\n")

        lines.append("---\n")

    return "\n".join(lines)
```

### Step 2.4: Angle Discovery Implementation

**SONNET: This is NEW and helps find unique perspectives on topics.**

**File: `backend/pipeline/angle_discovery.py`** (CREATE NEW FILE)

```python
"""Angle discovery system for finding unique documentary perspectives."""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger
import openai
from backend.integrations.perplexity_client import PerplexityClient
from collections import Counter

class DiscoveredAngle(BaseModel):
    """A discovered angle for documentary production."""
    angle_type: str  # untold_perspective, process_focus, temporal_shift, etc.
    title: str
    description: str
    uniqueness_score: float  # 0-1, higher is more unique
    evidence: List[str]
    key_sources_needed: List[str]
    production_notes: str
    estimated_viewer_interest: str  # low, medium, high
    competition_analysis: Dict[str, Any]

class AngleDiscovery:
    """Find unique angles for documentary production."""

    def __init__(self):
        self.perplexity = PerplexityClient()

    def discover_angles(
        self,
        topic: str,
        research_data: Dict,
        existing_coverage: Optional[List[str]] = None
    ) -> Dict:
        """
        Discover unique angles for documentary production.

        SONNET: This helps find perspectives that haven't been covered.
        Example: Focus on legal battles instead of the crimes themselves.
        """

        # Step 1: Analyze existing coverage
        coverage_map = self.analyze_existing_coverage(topic, existing_coverage)

        # Step 2: Identify gaps in coverage
        coverage_gaps = self.find_coverage_gaps(coverage_map, research_data)

        # Step 3: Generate angle proposals
        angles = self.generate_angle_proposals(coverage_gaps, research_data)

        # Step 4: Score angles by uniqueness and feasibility
        scored_angles = self.score_angles(angles, coverage_map)

        # Step 5: Find unexpected connections
        connections = self.discover_connections(topic, research_data)

        return {
            "discovered_angles": scored_angles,
            "coverage_map": coverage_map,
            "unexpected_connections": connections,
            "recommended_angle": self.select_best_angle(scored_angles)
        }

    def analyze_existing_coverage(
        self,
        topic: str,
        existing_titles: Optional[List[str]] = None
    ) -> Dict:
        """Analyze what angles have been covered in existing content."""

        # Search for existing documentaries and videos
        search_query = f"{topic} documentary YouTube"
        existing_content = self.perplexity.search(search_query)

        # Categorize coverage patterns
        coverage_patterns = {
            "heavily_covered": [],
            "moderately_covered": [],
            "rarely_covered": []
        }

        # Analyze titles and descriptions to identify common angles
        common_themes = []
        if existing_titles:
            for title in existing_titles:
                # Extract theme from title
                if "crime" in title.lower():
                    common_themes.append("crime_details")
                if "victim" in title.lower():
                    common_themes.append("victim_story")
                if "investigation" in title.lower():
                    common_themes.append("investigation_process")
                if "legal" in title.lower() or "trial" in title.lower():
                    common_themes.append("legal_proceedings")

        # Count theme frequency
        theme_counts = Counter(common_themes)

        # Categorize by frequency
        for theme, count in theme_counts.items():
            if count > len(existing_titles) * 0.5:
                coverage_patterns["heavily_covered"].append(theme)
            elif count > len(existing_titles) * 0.2:
                coverage_patterns["moderately_covered"].append(theme)
            else:
                coverage_patterns["rarely_covered"].append(theme)

        # Identify what's missing entirely
        all_possible_angles = [
            "legal_strategy", "jury_perspective", "economic_impact",
            "media_manipulation", "systemic_issues", "family_aftermath",
            "community_response", "psychological_analysis", "forensic_details",
            "political_implications", "social_media_impact", "historical_context"
        ]

        covered = set(common_themes)
        coverage_patterns["not_covered"] = [
            angle for angle in all_possible_angles
            if angle not in covered
        ]

        logger.info(f"Coverage analysis complete: {len(coverage_patterns['not_covered'])} uncovered angles found")

        return coverage_patterns

    def find_coverage_gaps(
        self,
        coverage_map: Dict,
        research_data: Dict
    ) -> List[Dict]:
        """Identify what perspectives haven't been explored."""

        gaps = []

        # Check for missing perspectives from key entities
        entities = research_data.get("entities", {})
        people = entities.get("people", [])

        # Find people who are mentioned but not featured
        for person in people:
            if person.get("mentions", 0) > 5:  # Significant but not central
                gaps.append({
                    "type": "untold_perspective",
                    "subject": person.get("name"),
                    "reason": f"Mentioned {person.get('mentions')} times but no dedicated coverage",
                    "potential": "high" if person.get("role") else "medium"
                })

        # Check for temporal gaps
        timeline = research_data.get("timeline", [])
        if timeline:
            # Look for periods with many events but little coverage
            gaps.append({
                "type": "temporal_gap",
                "period": "Pre-incident buildup",
                "reason": "Events leading up to main incident rarely covered",
                "potential": "high"
            })

        # Check for process gaps
        if "legal_strategy" in coverage_map.get("not_covered", []):
            gaps.append({
                "type": "process_focus",
                "subject": "Legal maneuvering",
                "reason": "Behind-the-scenes legal strategy unexplored",
                "potential": "very_high"
            })

        return gaps

    def generate_angle_proposals(
        self,
        coverage_gaps: List[Dict],
        research_data: Dict
    ) -> List[DiscoveredAngle]:
        """Generate specific angle proposals based on gaps."""

        proposals = []

        for gap in coverage_gaps:
            if gap["type"] == "untold_perspective":
                angle = DiscoveredAngle(
                    angle_type="untold_perspective",
                    title=f"The Untold Story: {gap['subject']}'s Perspective",
                    description=f"Focus on {gap['subject']}'s role and experience in the events",
                    uniqueness_score=0.85,
                    evidence=[gap["reason"]],
                    key_sources_needed=[f"Interview with {gap['subject']}", "Personal documents"],
                    production_notes="Requires securing exclusive interviews",
                    estimated_viewer_interest="high",
                    competition_analysis={
                        "similar_content": [],
                        "gap_in_coverage": f"No existing content from {gap['subject']}'s perspective"
                    }
                )
                proposals.append(angle)

            elif gap["type"] == "process_focus":
                angle = DiscoveredAngle(
                    angle_type="process_focus",
                    title="The Legal Chess Match: Behind Closed Doors",
                    description="Focus on legal strategies and courtroom tactics rather than the crime",
                    uniqueness_score=0.92,
                    evidence=[
                        "Only 3% of coverage focuses on legal strategy",
                        "Rich material in court transcripts unexplored",
                        "Multiple legal experts available for commentary"
                    ],
                    key_sources_needed=["Court transcripts", "Legal expert interviews", "Attorney statements"],
                    production_notes="Use animations to explain legal concepts",
                    estimated_viewer_interest="high",
                    competition_analysis={
                        "similar_content": [],
                        "gap_in_coverage": "Legal strategy angle completely unexplored"
                    }
                )
                proposals.append(angle)

            elif gap["type"] == "temporal_gap":
                angle = DiscoveredAngle(
                    angle_type="temporal_shift",
                    title="The Prelude: What Led to the Breaking Point",
                    description="Focus on events leading up to the incident, not the incident itself",
                    uniqueness_score=0.78,
                    evidence=[
                        "Timeline shows 15+ significant events before main incident",
                        "These events provide crucial context",
                        "Pre-incident period rarely covered in depth"
                    ],
                    key_sources_needed=["Historical records", "Early interviews", "Contemporary reports"],
                    production_notes="Use timeline graphics to show buildup",
                    estimated_viewer_interest="medium",
                    competition_analysis={
                        "similar_content": ["Some coverage of background"],
                        "gap_in_coverage": "No dedicated focus on pre-incident period"
                    }
                )
                proposals.append(angle)

        # Add system-level angle (always relevant)
        proposals.append(DiscoveredAngle(
            angle_type="system_analysis",
            title="System Failure: How Institutions Failed",
            description="Analyze institutional and systemic failures that enabled the events",
            uniqueness_score=0.88,
            evidence=[
                "Multiple institutional touchpoints identified",
                "Pattern of systemic issues evident",
                "Broader implications unexplored"
            ],
            key_sources_needed=["Policy documents", "Expert analysis", "Comparative cases"],
            production_notes="Use infographics to show system connections",
            estimated_viewer_interest="medium",
            competition_analysis={
                "similar_content": ["Some mention of failures"],
                "gap_in_coverage": "No systematic analysis of institutional role"
            }
        ))

        return proposals

    def score_angles(
        self,
        angles: List[DiscoveredAngle],
        coverage_map: Dict
    ) -> List[DiscoveredAngle]:
        """Score angles by uniqueness and documentary potential."""

        for angle in angles:
            # Calculate uniqueness based on coverage
            if angle.angle_type in ["legal_strategy", "jury_perspective"]:
                if these in coverage_map.get("not_covered", []):
                    angle.uniqueness_score = min(angle.uniqueness_score * 1.2, 1.0)

            # Adjust for feasibility
            sources_available = len([s for s in angle.key_sources_needed if "Interview" not in s])
            if sources_available > len(angle.key_sources_needed) / 2:
                angle.uniqueness_score *= 1.1  # Boost score if sources are accessible

        # Sort by score
        angles.sort(key=lambda x: x.uniqueness_score, reverse=True)

        return angles

    def discover_connections(
        self,
        topic: str,
        research_data: Dict
    ) -> List[Dict]:
        """Find unexpected connections to other topics."""

        connections = []

        # Look for economic connections
        if "economic" not in topic.lower():
            connections.append({
                "connection_type": "economic",
                "description": "Economic impact on local community",
                "relevance": "Unexplored financial consequences"
            })

        # Look for political connections
        entities = research_data.get("entities", {})
        if any("political" in str(e).lower() for e in entities.get("organizations", [])):
            connections.append({
                "connection_type": "political",
                "description": "Political implications and responses",
                "relevance": "Political dimension rarely examined"
            })

        # Look for historical parallels
        connections.append({
            "connection_type": "historical",
            "description": "Historical precedents and patterns",
            "relevance": "Similar cases from the past provide context"
        })

        return connections

    def select_best_angle(self, angles: List[DiscoveredAngle]) -> Dict:
        """Select the best angle for documentary production."""

        if not angles:
            return {
                "primary": "Standard investigative approach",
                "rationale": "No unique angles identified"
            }

        # Get top angle
        best = angles[0]

        # Consider combining complementary angles
        complementary = None
        for angle in angles[1:]:
            if angle.angle_type != best.angle_type and angle.uniqueness_score > 0.8:
                complementary = angle
                break

        if complementary:
            return {
                "primary": f"{best.title} + {complementary.title}",
                "rationale": f"Combines {best.angle_type} with {complementary.angle_type} for maximum impact",
                "primary_angle": best.model_dump(),
                "secondary_angle": complementary.model_dump()
            }
        else:
            return {
                "primary": best.title,
                "rationale": f"Highest uniqueness score ({best.uniqueness_score:.2f}) with {best.estimated_viewer_interest} viewer interest",
                "primary_angle": best.model_dump()
            }
```

### Step 2.5: Documentary Intelligence Implementation

**SONNET: This is NEW and CRITICAL. Creates the documentary layer.**

**File: `backend/pipeline/documentary_intelligence.py`** (CREATE NEW FILE)

```python
"""Documentary intelligence layer for narrative analysis."""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger

class NarrativeStructure(BaseModel):
    """Three-act documentary structure."""
    opening_hook: str
    act_1_setup: Dict[str, Any]
    act_2_investigation: Dict[str, Any]
    act_3_resolution: Dict[str, Any]

class DocumentaryIntelligence:
    """Transform research into documentary blueprint."""

    def analyze(self, research_data: Dict, doc_type: str) -> Dict:
        """
        Analyze research for documentary production.

        SONNET: This is the KEY differentiator. Implement completely.
        """

        # Extract documentary elements based on type
        if doc_type == "breaking_news":
            return self._analyze_breaking_news(research_data)
        elif doc_type == "investigation":
            return self._analyze_investigation(research_data)
        elif doc_type == "profile":
            return self._analyze_profile(research_data)
        elif doc_type == "controversy":
            return self._analyze_controversy(research_data)
        else:
            return self._analyze_standard(research_data)

    def _analyze_investigation(self, data: Dict) -> Dict:
        """Analysis for investigative documentary."""

        # Find the hook - most shocking revelation
        hook = self._find_shocking_moment(data)

        # Identify conflicts and controversies
        conflicts = self._extract_conflicts(data)

        # Find visual moments
        visual_moments = self._identify_visual_moments(data)

        # Build narrative structure
        narrative = self._build_narrative_arc(data, "investigation")

        # Identify key interviews needed
        interviews = self._suggest_interviews(data)

        return {
            "hook": hook,
            "narrative_structure": narrative,
            "key_conflicts": conflicts,
            "visual_moments": visual_moments,
            "interview_suggestions": interviews,
            "production_notes": self._generate_production_notes(data)
        }

    def _find_shocking_moment(self, data: Dict) -> str:
        """Find the most compelling opening moment."""
        # Analyze claims for shock value
        claims = data.get("claims", [])

        shocking_claims = []
        for claim in claims:
            # Score based on controversy indicators
            score = 0
            claim_text = claim.get("canonical_claim", "").lower()

            # Keywords that indicate controversy
            controversy_words = ["scandal", "leaked", "exposed", "accused",
                               "denied", "covered up", "lied", "fraud"]
            for word in controversy_words:
                if word in claim_text:
                    score += 2

            if score > 0:
                shocking_claims.append((claim, score))

        # Sort by shock value
        shocking_claims.sort(key=lambda x: x[1], reverse=True)

        if shocking_claims:
            return shocking_claims[0][0].get("verbatim_quote", "")

        return "Opening hook to be determined from research"

    def _extract_conflicts(self, data: Dict) -> List[Dict]:
        """Find opposing viewpoints and conflicts."""
        conflicts = []

        # Analyze validation results for contradictions
        validation = data.get("validation", [])
        for evidence in validation:
            if evidence.get("status") == "DEBUNKED":
                conflicts.append({
                    "type": "disputed_claim",
                    "claim": evidence.get("claim_id"),
                    "conflict": "Claim has been debunked by evidence"
                })

        # Look for opposing entities
        entities = data.get("entities", {})
        # Simple heuristic - could be enhanced with relationship mapping

        return conflicts

    def _identify_visual_moments(self, data: Dict) -> List[Dict]:
        """Find moments good for video production."""
        visual_moments = []

        # Search transcripts for visual cues
        sources = data.get("sources", [])

        visual_keywords = [
            "showed", "displayed", "held up", "pointed", "demonstrated",
            "revealed", "unveiled", "chart", "graph", "document",
            "emotional", "angry", "cried", "laughed", "shocked"
        ]

        for source in sources:
            text = source.get("text", "")
            url = source.get("url", "")

            for keyword in visual_keywords:
                if keyword in text.lower():
                    # Extract context around keyword
                    index = text.lower().find(keyword)
                    context = text[max(0, index-100):min(len(text), index+100)]

                    visual_moments.append({
                        "source_url": url,
                        "keyword": keyword,
                        "context": context,
                        "production_note": f"Potential B-roll moment: {keyword}"
                    })

        return visual_moments[:20]  # Top 20 moments

    def _build_narrative_arc(self, data: Dict, doc_type: str) -> NarrativeStructure:
        """Build three-act structure."""

        timeline = data.get("timeline", [])
        entities = data.get("entities", {})
        claims = data.get("claims", [])

        return NarrativeStructure(
            opening_hook=self._find_shocking_moment(data),
            act_1_setup={
                "introduce_players": entities.get("people", [])[:5],  # Top 5 people
                "establish_context": timeline[:3] if timeline else [],  # Early events
                "set_stakes": "What's at stake in this story"
            },
            act_2_investigation={
                "rising_action": timeline[3:10] if len(timeline) > 3 else [],
                "key_revelations": claims[:10],  # Top claims
                "conflicts": self._extract_conflicts(data)
            },
            act_3_resolution={
                "climax": timeline[-3:] if timeline else [],  # Recent events
                "verified_facts": [c for c in claims if c.get("confidence", 0) > 0.8],
                "open_questions": [c for c in claims if c.get("confidence", 0) < 0.5],
                "call_to_action": "What happens next?"
            }
        )

    def _suggest_interviews(self, data: Dict) -> List[Dict]:
        """Suggest interview subjects and questions."""
        entities = data.get("entities", {})
        people = entities.get("people", [])

        interviews = []
        for person in people[:10]:  # Top 10 people
            interviews.append({
                "subject": person.get("name"),
                "relevance": person.get("mentions", 0),
                "suggested_questions": [
                    f"What is your response to claims about {person.get('name')}?",
                    f"Can you clarify your role in these events?",
                    f"What evidence supports your position?"
                ]
            })

        return interviews

    def _generate_production_notes(self, data: Dict) -> Dict:
        """Generate specific production recommendations."""
        return {
            "estimated_runtime": self._estimate_runtime(data),
            "b_roll_needed": len(self._identify_visual_moments(data)),
            "graphics_needed": [
                "Timeline graphic",
                "Entity relationship diagram",
                "Claims evidence table"
            ],
            "tone": self._determine_tone(data)
        }

    def _estimate_runtime(self, data: Dict) -> str:
        """Estimate video runtime based on content."""
        claims = len(data.get("claims", []))
        timeline_events = len(data.get("timeline", []))

        if claims > 50 or timeline_events > 20:
            return "20-30 minutes (long-form)"
        elif claims > 20 or timeline_events > 10:
            return "10-15 minutes (medium)"
        else:
            return "5-10 minutes (short)"

    def _determine_tone(self, data: Dict) -> str:
        """Determine appropriate tone for documentary."""
        # Analyze content for tone indicators
        validation = data.get("validation", [])
        debunked_count = sum(1 for v in validation if v.get("status") == "DEBUNKED")

        if debunked_count > len(validation) / 2:
            return "Investigative/Skeptical"
        else:
            return "Balanced/Informative"

    # Implement other analysis methods for different doc types...
```

### Step 2.5: Update Worker Pipeline

**File: `backend/worker.py`**

**SONNET WARNING: DO NOT delete existing stages. ADD the new ones.**

```python
# Add these imports at the top
from backend.pipeline.timeline import extract_timeline
from backend.pipeline.entities import EntityExtractor
from backend.integrations.reddit_client import RedditClient, extract_reddit_content
from backend.models.job_config import get_mode_config

# Modify run_research_job function:

@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(job_id: str, topic: str, slack_payload: Optional[dict] = None) -> dict:
    """
    SONNET: Add timeline, entities, and Reddit stages to existing pipeline.
    DO NOT remove existing stages, ADD new ones.
    """

    # Get job and determine mode
    job = get_job(job_id)
    mode = job.config_json.get("pipeline", "standard")  # Default to standard
    mode_config = get_mode_config(mode)

    # ... existing stages 1-6 ...

    # NEW Stage 6.5: Reddit Collection (if enabled for mode)
    if mode_config.get("reddit_enabled", False):
        logger.info(f"[{job_id}] Stage 6.5: Reddit collection")
        update_job(job_id, stage="reddit_collection", progress_percent=58)

        try:
            reddit_client = RedditClient()
            reddit_posts = reddit_client.search_multiple_subreddits(
                query=topic,
                limit_per_sub=mode_config.get("reddit_max_posts", 5) // 5  # Divide by number of subs
            )

            # Store Reddit posts
            update_job(job_id, partial_outputs={"reddit_posts": reddit_posts})

            # Convert to markdown for processing
            reddit_md = extract_reddit_content(reddit_posts)
            outputs["reddit_discussions_md"] = reddit_md

            # Add Reddit content as sources for claim extraction
            if reddit_posts:
                reddit_source = {
                    "url": "reddit.com/search",
                    "title": "Reddit Discussions",
                    "source_type": "reddit",
                    "text": reddit_md
                }
                web_sources.append(reddit_source)

        except Exception as e:
            logger.warning(f"[{job_id}] Reddit collection failed: {e}")
            warnings.append(f"Reddit collection failed: {str(e)}")

    # ... existing stage 7 (extraction) ...

    # NEW Stage 7.5: Timeline Extraction (if enabled for mode)
    if mode_config.get("timeline_extraction", False):
        logger.info(f"[{job_id}] Stage 7.5: Timeline extraction")
        update_job(job_id, stage="timeline_extraction", progress_percent=68)

        try:
            timeline_events = extract_timeline(transcripts, web_sources, claims)

            # Store timeline
            timeline_data = [event.model_dump() for event in timeline_events]
            update_job(job_id, timeline_events=timeline_data)

            # Generate timeline markdown
            timeline_md = generate_timeline_markdown(timeline_events)
            outputs["timeline_md"] = timeline_md

            logger.info(f"[{job_id}] Extracted {len(timeline_events)} timeline events")

        except Exception as e:
            logger.warning(f"[{job_id}] Timeline extraction failed: {e}")
            warnings.append(f"Timeline extraction failed: {str(e)}")

    # NEW Stage 7.6: Entity Extraction (if enabled for mode)
    if mode_config.get("entity_extraction", False):
        logger.info(f"[{job_id}] Stage 7.6: Entity extraction")
        update_job(job_id, stage="entity_extraction", progress_percent=70)

        try:
            extractor = EntityExtractor()
            entities = extractor.extract_entities(transcripts, web_sources, claims)

            # Store entities
            update_job(job_id, entities=entities)

            # Generate entities markdown
            entities_md = generate_entities_markdown(entities)
            outputs["entities_md"] = entities_md

            total_entities = sum(len(entities[cat]) for cat in entities)
            logger.info(f"[{job_id}] Extracted {total_entities} entities")

        except Exception as e:
            logger.warning(f"[{job_id}] Entity extraction failed: {e}")
            warnings.append(f"Entity extraction failed: {str(e)}")

    # ... existing stage 8 (validation) ...

    # NEW Stage 8.5: Manual Guidance Generation (if enabled)
    if mode_config.get("manual_guidance_generation", False):
        logger.info(f"[{job_id}] Stage 8.5: Manual guidance generation")
        update_job(job_id, stage="manual_guidance", progress_percent=78)

        try:
            guidance = generate_manual_guidance(topic, entities, angles)
            update_job(job_id, manual_guidance=guidance)
            outputs["manual_guidance_md"] = format_guidance_markdown(guidance)

        except Exception as e:
            logger.warning(f"[{job_id}] Manual guidance generation failed: {e}")

    # ... existing stage 9 (Drive docs) ...

    # NEW Stage 9.5: Angle Discovery
    logger.info(f"[{job_id}] Stage 9.5: Angle discovery")
    update_job(job_id, stage="angle_discovery", progress_percent=83)

    try:
        from backend.pipeline.angle_discovery import AngleDiscovery

        angle_discovery = AngleDiscovery()
        discovered_angles = angle_discovery.discover_angles(
            topic=topic,
            research_data={
                "timeline": timeline_events,
                "entities": entities,
                "claims": claims,
                "sources": web_sources + transcripts
            }
        )

        # Store discovered angles
        update_job(job_id,
            discovered_angles=discovered_angles.get("discovered_angles", []),
            coverage_analysis=discovered_angles.get("coverage_map", {})
        )

        outputs["discovered_angles"] = discovered_angles
        logger.info(f"[{job_id}] Discovered {len(discovered_angles.get('discovered_angles', []))} unique angles")

    except Exception as e:
        logger.warning(f"[{job_id}] Angle discovery failed: {e}")
        warnings.append(f"Angle discovery failed: {str(e)}")

    # NEW Stage 9.6: Documentary Intelligence Analysis
    logger.info(f"[{job_id}] Stage 9.6: Documentary intelligence analysis")
    update_job(job_id, stage="documentary_analysis", progress_percent=87)

    try:
        from backend.pipeline.documentary_intelligence import DocumentaryIntelligence

        doc_intel = DocumentaryIntelligence()

        # Include discovered angles in documentary analysis
        documentary_analysis = doc_intel.analyze(
            research_data={
                "timeline": timeline_events,
                "entities": entities,
                "claims": claims,
                "sources": web_sources + transcripts,
                "validation": evidence_records,
                "discovered_angles": discovered_angles  # Pass angles to documentary analysis
            },
            doc_type=mode  # breaking_news, investigation, profile, controversy
        )

        outputs["documentary_analysis"] = documentary_analysis
        logger.info(f"[{job_id}] Documentary analysis complete")

    except Exception as e:
        logger.warning(f"[{job_id}] Documentary analysis failed: {e}")
        warnings.append(f"Documentary analysis failed: {str(e)}")

    # NEW Stage 9.7: Dual Output Generation
    logger.info(f"[{job_id}] Stage 9.7: Dual output generation")
    update_job(job_id, stage="dual_outputs", progress_percent=90)

    try:
        # Output 1: NotebookLM Research Packet (Comprehensive)
        notebooklm_packet = create_notebooklm_packet(
            job_id, outputs, job_config,
            include_raw_data=True  # Everything for analysis
        )

        # Output 2: Documentary Blueprint (Production-Ready)
        # Include discovered angles in the blueprint
        documentary_blueprint = create_documentary_blueprint(
            job_id, outputs, documentary_analysis, job_config,
            discovered_angles=discovered_angles  # Pass angles to blueprint
        )

        # Save both outputs
        packet_filename = f"notebooklm_{job_id}_{topic[:30]}.md"
        blueprint_filename = f"documentary_{job_id}_{topic[:30]}.md"

        packet_path = save_packet_locally(packet_filename, notebooklm_packet)
        blueprint_path = save_packet_locally(blueprint_filename, documentary_blueprint)

        # Upload to Drive
        packet_url = upload_to_drive(packet_path, folder_url)
        blueprint_url = upload_to_drive(blueprint_path, folder_url)

        update_job(job_id,
            notebooklm_packet_url=packet_url,
            documentary_blueprint_url=blueprint_url
        )

        logger.info(f"[{job_id}] Created dual outputs - NotebookLM: {packet_url}, Documentary: {blueprint_url}")

    except Exception as e:
        logger.warning(f"[{job_id}] Dual output generation failed: {e}")
        warnings.append(f"Dual output generation failed: {str(e)}")

    # ... rest of existing code ...
```

---

## Phase 3: Frontend Implementation [Days 8-10]

### Step 3.1: API Route for Frontend

**File: `frontend/pages/api/jobs/index.ts`** (CREATE NEW FILE)

**SONNET: The frontend currently calls /api/jobs but this doesn't exist. CREATE it.**

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // SONNET: Proxy to backend, don't expose backend directly

  if (req.method === 'POST') {
    try {
      const response = await fetch(`${BACKEND_URL}/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: req.body.topic || req.body.prompt,
          pipeline: req.body.pipeline || 'standard',
          options: req.body.options || {}
        }),
      });

      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      res.status(500).json({ error: 'Failed to create job' });
    }
  } else if (req.method === 'GET') {
    // Job listing
    try {
      const response = await fetch(`${BACKEND_URL}/jobs`);
      const data = await response.json();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch jobs' });
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}
```

### Step 3.2: Job Status Polling

**File: `frontend/pages/jobs/[id].tsx`** (CREATE NEW FILE)

```typescript
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

export default function JobStatus() {
  const router = useRouter();
  const { id } = router.query;
  const [job, setJob] = useState(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!id) return;

    // SONNET: Implement polling - DO NOT use setInterval, use setTimeout recursively
    const pollStatus = async () => {
      try {
        const response = await fetch(`/api/jobs/${id}`);
        const data = await response.json();
        setJob(data);

        // Continue polling if job is running
        if (data.status === 'running' || data.status === 'queued') {
          if (polling) {
            setTimeout(pollStatus, 5000); // Poll every 5 seconds
          }
        } else {
          setPolling(false);
        }
      } catch (error) {
        console.error('Failed to fetch job status:', error);
        setTimeout(pollStatus, 5000); // Retry on error
      }
    };

    pollStatus();

    return () => {
      setPolling(false); // Cleanup on unmount
    };
  }, [id, polling]);

  if (!job) {
    return <div>Loading...</div>;
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Job Status: {id}</h1>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="bg-gray-200 rounded-full h-4">
          <div
            className="bg-blue-600 h-4 rounded-full transition-all"
            style={{ width: `${job.progress_percent}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-gray-600">
          {job.stage || 'Initializing'} - {job.progress_percent}%
        </p>
      </div>

      {/* Status Badge */}
      <div className="mb-4">
        <span className={`px-3 py-1 rounded text-white ${
          job.status === 'completed' ? 'bg-green-500' :
          job.status === 'failed' ? 'bg-red-500' :
          job.status === 'running' ? 'bg-blue-500' :
          'bg-gray-500'
        }`}>
          {job.status.toUpperCase()}
        </span>
      </div>

      {/* Results (if completed) */}
      {job.status === 'completed' && job.artifacts && (
        <div className="mt-6 p-4 bg-green-50 rounded">
          <h2 className="text-xl font-semibold mb-3">Results Ready!</h2>

          {job.notebooklm_packet_url && (
            <a
              href={job.notebooklm_packet_url}
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              target="_blank"
              rel="noopener noreferrer"
            >
              Download NotebookLM Packet
            </a>
          )}

          {job.artifacts.drive_folder_url && (
            <a
              href={job.artifacts.drive_folder_url}
              className="inline-block ml-3 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              target="_blank"
              rel="noopener noreferrer"
            >
              View All Documents
            </a>
          )}
        </div>
      )}

      {/* Error (if failed) */}
      {job.status === 'failed' && job.error && (
        <div className="mt-6 p-4 bg-red-50 rounded">
          <h2 className="text-xl font-semibold mb-3 text-red-700">Error</h2>
          <p className="text-red-600">{job.error}</p>
        </div>
      )}
    </div>
  );
}
```

### Step 3.3: Update Job Creation Form

**File: `frontend/pages/index.tsx`** (MODIFY EXISTING)

**SONNET: Update to support 4 modes, not just quick/full**

```typescript
// Replace the PipelineType with:
type ResearchMode = "quick" | "standard" | "deep" | "investigation";

// Add advanced options state:
const [mode, setMode] = useState<ResearchMode>("standard");
const [youtubeChannels, setYoutubeChannels] = useState("");
const [redditSubreddits, setRedditSubreddits] = useState("");
const [showAdvanced, setShowAdvanced] = useState(false);

// Update the form to include:
<div>
  <label className="block text-sm font-medium text-gray-700 mb-3">
    Research Mode
  </label>
  <select
    value={mode}
    onChange={(e) => setMode(e.target.value as ResearchMode)}
    className="w-full px-3 py-2 border border-gray-300 rounded-md"
  >
    <option value="quick">Quick (5 min, $1)</option>
    <option value="standard">Standard (15 min, $3)</option>
    <option value="deep">Deep (30 min, $7)</option>
    <option value="investigation">Investigation (45 min, $15)</option>
  </select>
</div>

{/* Advanced Options */}
<div className="mt-4">
  <button
    type="button"
    onClick={() => setShowAdvanced(!showAdvanced)}
    className="text-sm text-blue-600 hover:text-blue-800"
  >
    {showAdvanced ? '▼' : '▶'} Advanced Options
  </button>

  {showAdvanced && (
    <div className="mt-4 p-4 bg-gray-50 rounded">
      <div className="mb-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          YouTube Channels (comma-separated)
        </label>
        <input
          type="text"
          value={youtubeChannels}
          onChange={(e) => setYoutubeChannels(e.target.value)}
          placeholder="@channel1, @channel2"
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>

      <div className="mb-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Reddit Subreddits (comma-separated)
        </label>
        <input
          type="text"
          value={redditSubreddits}
          onChange={(e) => setRedditSubreddits(e.target.value)}
          placeholder="politics, news, OutOfTheLoop"
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>
    </div>
  )}
</div>
```

---

## Phase 4: Testing & Validation [Days 11-12]

### Step 4.1: Integration Tests

**File: `tests/test_pipeline_modes.py`** (CREATE NEW FILE)

```python
"""Test all 4 research modes work correctly."""
import pytest
from backend.models.job_config import ResearchMode, get_mode_config

def test_all_modes_have_config():
    """Each mode should have proper configuration."""
    for mode in ResearchMode:
        config = get_mode_config(mode)
        assert config is not None
        assert "max_duration_minutes" in config
        assert "max_cost_usd" in config

def test_quick_mode_limits():
    """Quick mode should be minimal."""
    config = get_mode_config(ResearchMode.QUICK)
    assert config["youtube_enabled"] == False
    assert config["reddit_enabled"] == False
    assert config["max_duration_minutes"] <= 5

def test_investigation_mode_comprehensive():
    """Investigation mode should have everything."""
    config = get_mode_config(ResearchMode.INVESTIGATION)
    assert config["youtube_enabled"] == True
    assert config["reddit_enabled"] == True
    assert config["timeline_extraction"] == True
    assert config["entity_extraction"] == True
    assert config["manual_guidance_generation"] == True
```

### Step 4.2: Timeline Extraction Tests

```python
"""Test timeline extraction."""
from backend.pipeline.timeline import extract_timeline, normalize_date

def test_extract_explicit_dates():
    """Should extract ISO format dates."""
    sources = [{
        "text": "On 2024-01-15, the event occurred.",
        "url": "http://example.com"
    }]

    events = extract_timeline([], sources)
    assert len(events) > 0
    assert events[0].date == "2024-01-15"
    assert events[0].date_precision == "exact"

def test_extract_relative_dates():
    """Should convert relative dates."""
    sources = [{
        "text": "Yesterday, the announcement was made.",
        "url": "http://example.com"
    }]

    events = extract_timeline([], sources)
    assert len(events) > 0
    assert events[0].date_precision == "relative"

def test_chronological_ordering():
    """Events should be ordered by date."""
    sources = [{
        "text": "On 2024-03-01 this happened. On 2024-01-15 that happened.",
        "url": "http://example.com"
    }]

    events = extract_timeline([], sources)
    assert events[0].date < events[1].date
```

---

## Phase 5: Deployment Checklist [Day 13]

### Pre-Deployment Verification

**SONNET: Complete ALL items before marking as done:**

- [ ] Database migrations applied to Supabase
- [ ] All 4 research modes working
- [ ] Timeline extraction producing events
- [ ] Entity extraction finding people/orgs
- [ ] Reddit integration fetching posts
- [ ] NotebookLM packet generating single file
- [ ] Frontend job creation with all options
- [ ] Frontend status polling working
- [ ] Frontend results download working
- [ ] No regression in existing features
- [ ] Cost tracking implemented
- [ ] All tests passing

### Environment Variables Check

```bash
# Verify all required vars are set:
echo "Checking environment variables..."
[[ -z "$REDDIT_CLIENT_ID" ]] && echo "ERROR: REDDIT_CLIENT_ID not set"
[[ -z "$REDDIT_CLIENT_SECRET" ]] && echo "ERROR: REDDIT_CLIENT_SECRET not set"
[[ -z "$OPENAI_API_KEY" ]] && echo "ERROR: OPENAI_API_KEY not set"
[[ -z "$PERPLEXITY_API_KEY" ]] && echo "ERROR: PERPLEXITY_API_KEY not set"
[[ -z "$SUPABASE_URL" ]] && echo "ERROR: SUPABASE_URL not set"
[[ -z "$SUPABASE_SERVICE_ROLE_KEY" ]] && echo "ERROR: SUPABASE_SERVICE_ROLE_KEY not set"
```

---

## Common Sonnet Pitfalls to Avoid

### 1. The "Optimization" Trap
**SONNET WILL TRY TO:** Skip timeline/entity extraction as "unnecessary"
**YOU MUST:** Implement them fully - they are REQUIRED for the vision

### 2. The "Simplification" Trap
**SONNET WILL TRY TO:** Combine 4 modes into 2 for "simplicity"
**YOU MUST:** Keep all 4 modes distinct with different behaviors

### 3. The "File Consolidation" Trap
**SONNET WILL TRY TO:** Keep generating multiple files "for clarity"
**YOU MUST:** Generate ONE NotebookLM packet file

### 4. The "Quick Fix" Trap
**SONNET WILL TRY TO:** Patch the frontend minimally
**YOU MUST:** Add proper status polling and results display

### 5. The "Skip Testing" Trap
**SONNET WILL TRY TO:** Skip tests to "save time"
**YOU MUST:** Write tests for new features

### 6. The "Ignore Reddit" Trap
**SONNET WILL TRY TO:** Skip Reddit because "it's complex"
**YOU MUST:** Implement Reddit with the provided API key

### 7. The "Hardcode" Trap
**SONNET WILL TRY TO:** Hardcode values "for now"
**YOU MUST:** Use environment variables and configuration

---

## Success Validation

After implementation, verify:

1. **Run Quick Mode:**
   - Should complete in <5 minutes
   - Should only use Perplexity
   - Should cost <$1

2. **Run Investigation Mode:**
   - Should extract timeline with dates
   - Should identify all major entities
   - Should fetch Reddit posts
   - Should generate manual guidance
   - Should produce single NotebookLM file

3. **Test Frontend:**
   - Create job with all options
   - Watch real-time progress
   - Download results
   - View job history

4. **Upload to NotebookLM:**
   - Take generated packet
   - Upload to NotebookLM
   - Verify it imports correctly
   - Verify you can query it

---

## Final Note to Sonnet

You are implementing a system for YouTube documentary research. The user needs:
1. Chronological timelines (for video narrative structure)
2. Entity tracking (to know who's involved)
3. Claim validation (for fact-checking)
4. Single file output (for NotebookLM)

These are NOT optional features. They are the CORE VALUE of the system.

The existing pipeline works but is missing these critical features. Your job is to ADD them without breaking what exists.

Remember: The user makes documentaries. They need structured, timeline-based research packets. That's the entire point.

Good luck! Follow this TEP step by step and you'll succeed.

---

*END OF TEP - Proceed with Phase 1 immediately*