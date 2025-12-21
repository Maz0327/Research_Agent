# Product Requirements Document (PRD) v1.0
## Research Agent - YouTube Documentary Research System

### Document Purpose
This PRD defines the complete requirements for the Research Agent system, addressing gaps identified in V1_Analysis.md. It is specifically written to guide AI implementation (Claude Sonnet) with explicit warnings against common pitfalls.

---

## 1. Product Vision & Goals (REVISED - Hybrid Approach)

### Vision Statement
Build a **dual-purpose research and documentary intelligence system** that both gathers comprehensive research for NotebookLM analysis AND transforms it into production-ready documentary blueprints, enabling both deep analysis and rapid video production.

### The Hybrid Architecture
```
Comprehensive Research Gathering + Documentary Intelligence Layer
                        ↓
    Dual Output: NotebookLM Packet + Documentary Blueprint
```

### Primary Goals
1. **Comprehensive Research** - Gather all available sources for deep analysis
2. **Documentary Intelligence** - Transform research into narrative structures
3. **Dual Output System** - Serve both analysis (NotebookLM) and production (video creation)
4. **Production Optimization** - Identify visual moments, key quotes, and story arcs

### Success Metrics
- Research completion in <30 minutes
- Both outputs generated (research packet + documentary blueprint)
- Documentary blueprint includes script outline, B-roll list, interview questions
- <$10 cost per complete package

---

## 2. User Personas & Use Cases

### Primary User: Documentary Creator
**Who:** YouTube content creator producing investigative/news documentaries
**Needs:**
- Chronological timeline of events
- Verified claims with citations
- Key players and their relationships
- Missing angles for balanced coverage

### Use Cases

#### UC1: Breaking News Research
**Trigger:** Major news event occurs
**Flow:** User submits topic → System gathers sources → Outputs timeline + claims → User creates video script

#### UC2: Deep Investigation
**Trigger:** Long-form documentary project
**Flow:** User submits topic + specific angles → System does deep research → User uploads to NotebookLM for analysis

#### UC3: Claim Verification
**Trigger:** Controversial claims need fact-checking
**Flow:** User submits claim-heavy topic → System validates each claim → User gets evidence table

---

## 3. Functional Requirements

### 3.1 Documentary Research Modes (REVISED - Documentary-Specific)

**IMPORTANT FOR SONNET:** Replace generic modes with documentary-specific modes that serve different video types:

#### Mode: `breaking_news`
- **Focus:** Speed and recency over depth
- **Sources:** Reddit (last 48h), Twitter guidance, News sites via Perplexity
- **Timeline:** Last 48-72 hours with hourly precision
- **Documentary Output:** Timeline-focused with developing story structure
- **Use Case:** Breaking news videos, rapid response content
- **Max Duration:** 10 minutes
- **Max Cost:** $2

#### Mode: `investigation`
- **Focus:** Deep verification and hidden connections
- **Sources:** Everything available + historical data
- **Timeline:** Complete historical reconstruction
- **Documentary Output:** Evidence-based narrative with claim verification
- **Use Case:** Long-form investigative documentaries
- **Max Duration:** 45 minutes
- **Max Cost:** $15

#### Mode: `profile`
- **Focus:** Single person or organization deep dive
- **Sources:** YouTube interviews, articles mentioning entity, social media
- **Timeline:** Biographical/chronological
- **Documentary Output:** Character study with relationship mapping
- **Use Case:** Profile pieces, biographical documentaries
- **Max Duration:** 30 minutes
- **Max Cost:** $8

#### Mode: `controversy`
- **Focus:** All sides of a disputed issue
- **Sources:** Diverse perspectives, opposing viewpoints
- **Timeline:** Event sequence with claim/counter-claim
- **Documentary Output:** Balanced presentation with evidence table
- **Use Case:** Explainer videos, controversy breakdowns
- **Max Duration:** 30 minutes
- **Max Cost:** $10

### 3.2 Timeline Extraction (NOT IMPLEMENTED - REQUIRED)

**SONNET WARNING:** This feature does NOT exist. You must CREATE it from scratch.

#### Requirements:
1. Extract explicit dates from all sources
2. Order events chronologically
3. Include attribution for each event
4. Handle relative dates ("last week", "two months ago")
5. Confidence scoring for inferred dates

#### Output Format:
```json
{
  "timeline": [
    {
      "date": "2024-01-15",
      "date_precision": "exact|inferred|approximate",
      "event": "Congressional hearing on topic",
      "source": "https://youtube.com/...",
      "attribution": "Rep. John Smith",
      "confidence": 0.95
    }
  ]
}
```

### 3.3 Entity Extraction (NOT IMPLEMENTED - REQUIRED)

**SONNET WARNING:** The Claim model has an entities field but NO extraction logic. CREATE the extraction.

#### Requirements:
1. Extract people, organizations, locations
2. Track aliases and variations
3. Build relationship graph
4. Role identification

#### Output Format:
```json
{
  "entities": {
    "people": [
      {
        "name": "Candace Owens",
        "aliases": ["Candace", "Owens"],
        "role": "Political commentator",
        "mentioned_count": 45,
        "sentiment": "mixed"
      }
    ],
    "organizations": [...],
    "locations": [...]
  }
}
```

### 3.4 Web UI Requirements (MINIMAL - NEEDS COMPLETE REBUILD)

**SONNET WARNING:** Current frontend is barely functional. Do NOT just patch it. REBUILD these components:

#### Required Pages

##### 1. Job Creation Page
- Research mode selector (4 modes, not 2)
- Advanced options panel
- YouTube channel input
- Reddit subreddit input
- Time window selector
- Cost estimate display

##### 2. Job Status Page
- Real-time progress bar
- Current stage display
- Live log stream
- Cancel button
- Cost accumulator

##### 3. Results Page
- Timeline visualization
- Entity relationship graph
- Claims table with validation status
- Download options:
  - NotebookLM packet (single file)
  - Individual documents
  - JSON export
- Share link generation

##### 4. Job History Page
- Sortable/filterable job list
- Quick re-run button
- Cost per job
- Success/failure indicators

### 3.5 Reddit Integration (NEW - Use API Key)

**SONNET NOTE:** User has Reddit API key. Implement proper Reddit scraping.

#### Requirements:
1. Search subreddits by topic
2. Fetch top/new/controversial posts
3. Extract comment threads
4. Parse deleted/removed content indicators
5. Track vote counts and awards

#### Implementation:
```python
# Use PRAW (Python Reddit API Wrapper)
import praw

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=USER_AGENT
)
```

### 3.6 Dual Output System (NEW - Two Distinct Outputs)

**SONNET WARNING:** System must generate TWO outputs - one for NotebookLM analysis, one for documentary production.

#### Output 1: NotebookLM Research Packet (Comprehensive)
```markdown
# Research Packet: [Topic]
Generated: [Date]

## Executive Summary
[Key findings in 3-5 bullets]

## Complete Timeline
[Every event found, chronologically ordered]

## All Entities
[Complete list of people, organizations, locations]

## All Claims
[Every claim extracted with sources]

## All Sources
[Complete list with full text/transcripts]

## Validation Results
[All fact-checking results]

## Raw Data
[Complete transcripts, articles, posts]
```

#### Output 2: Documentary Blueprint (Production-Ready)
```markdown
# Documentary Blueprint: [Topic]
Generated: [Date]

## Opening Hook
[Most compelling moment to start the video]

## Three-Act Structure
### Act 1: Setup
- Introduce key players
- Establish stakes
- Timeline to incident

### Act 2: Investigation
- Claims and counter-claims
- Evidence presentation
- Conflict escalation

### Act 3: Resolution
- What we know for certain
- What remains disputed
- Call to action

## Key Production Elements
### Interview Clips Needed
[Specific people and questions]

### B-Roll List
[Visual moments with timestamps]

### Graphics Required
[Charts, timelines, relationship diagrams]

## Script Outline
[Scene-by-scene breakdown]

## Fact-Check Priority
[Claims that must be verified before production]
```

### 3.7 Documentary Intelligence Layer (NEW - REQUIRED)

**SONNET:** This is a NEW requirement beyond basic research gathering.

#### Requirements:
1. **Narrative Detection:** Identify story arcs in research
2. **Conflict Mapping:** Find opposing viewpoints and controversies
3. **Visual Moment Extraction:** Identify moments good for video
4. **Emotional Arc:** Track emotional progression of story
5. **Production Planning:** Generate specific production recommendations

#### Implementation:
```python
class DocumentaryIntelligence:
    def analyze(self, research_data):
        return {
            "narrative_structure": self.find_story_arc(research_data),
            "key_conflicts": self.identify_conflicts(research_data),
            "visual_moments": self.extract_visual_opportunities(research_data),
            "emotional_beats": self.map_emotional_journey(research_data),
            "production_needs": self.identify_production_requirements(research_data)
        }
```

### 3.8 Angle Discovery System (NEW - Find Unique Perspectives)

**SONNET:** This feature identifies unexplored angles and unique perspectives for documentary production.

#### Purpose
Help creators find fresh perspectives on well-covered topics by analyzing existing coverage patterns and identifying gaps, underrepresented viewpoints, or novel connections.

#### Requirements:
1. **Coverage Analysis:** Map what angles have been covered extensively
2. **Gap Detection:** Identify missing perspectives and unexplored angles
3. **Connection Discovery:** Find unexpected relationships between topics
4. **Perspective Mapping:** Identify underrepresented voices or viewpoints
5. **Angle Scoring:** Rank angles by uniqueness and documentary potential

#### Angle Types:
- **Untold Perspective:** Stories from ignored participants (e.g., jury members in famous trials)
- **Process Focus:** Behind-the-scenes of events (e.g., legal strategies vs. the crime itself)
- **Temporal Shift:** Before/after stories rarely covered (e.g., victim's family 10 years later)
- **System Analysis:** Institutional angles (e.g., how police procedures failed)
- **Counter-Narrative:** Challenge dominant narrative with evidence
- **Intersectional:** Connect to unexpected topics (e.g., economic impact of true crime tourism)

#### Output Format:
```json
{
  "discovered_angles": [
    {
      "angle_type": "process_focus",
      "title": "The Legal Chess Match: Defense Strategies in High-Profile Cases",
      "description": "Focus on legal maneuvering rather than crime details",
      "uniqueness_score": 0.92,
      "evidence": [
        "Only 3% of existing coverage focuses on legal strategy",
        "Rich material in court transcripts unexplored",
        "Multiple legal experts available for interviews"
      ],
      "key_sources_needed": ["Court transcripts", "Legal expert interviews"],
      "production_notes": "Requires animation for legal concepts",
      "estimated_viewer_interest": "high",
      "competition_analysis": {
        "similar_content": ["List of similar videos"],
        "gap_in_coverage": "No one has covered jury selection process"
      }
    }
  ],
  "coverage_map": {
    "heavily_covered": ["Crime details", "Victim stories", "Perpetrator psychology"],
    "moderately_covered": ["Investigation process", "Media coverage"],
    "rarely_covered": ["Legal strategies", "Jury perspectives", "Economic impacts"]
  },
  "recommended_angle": {
    "primary": "Legal strategy focus with jury perspective",
    "rationale": "Combines two underexplored angles with high documentary value"
  }
}
```

#### Implementation:
```python
class AngleDiscovery:
    def discover_angles(self, topic: str, research_data: dict):
        # Analyze existing coverage
        coverage_map = self.analyze_existing_coverage(topic)

        # Identify gaps
        coverage_gaps = self.find_coverage_gaps(coverage_map, research_data)

        # Generate angle proposals
        angles = self.generate_angle_proposals(coverage_gaps, research_data)

        # Score and rank angles
        scored_angles = self.score_angles(angles, coverage_map)

        # Find unexpected connections
        connections = self.discover_connections(topic, research_data)

        return {
            "discovered_angles": scored_angles,
            "coverage_map": coverage_map,
            "unexpected_connections": connections,
            "recommended_angle": self.select_best_angle(scored_angles)
        }

    def analyze_existing_coverage(self, topic: str) -> dict:
        """Analyze what angles have been covered in existing content"""
        # Search YouTube, news articles, documentaries
        # Categorize by angle type
        # Calculate coverage density
        pass

    def find_coverage_gaps(self, coverage_map: dict, research_data: dict) -> list:
        """Identify what hasn't been covered or is underrepresented"""
        # Compare available sources to actual coverage
        # Identify silent voices
        # Find missing temporal perspectives
        pass

    def score_angles(self, angles: list, coverage_map: dict) -> list:
        """Score angles by uniqueness and documentary potential"""
        # Uniqueness: How rarely is this angle covered?
        # Access: Can we get sources for this angle?
        # Interest: Will viewers care?
        # Feasibility: Can it be produced effectively?
        pass
```

#### Integration with Research Pipeline:
1. Run angle discovery after initial research gathering
2. Use discovered angles to guide secondary research
3. Include angle recommendations in Documentary Blueprint
4. Adjust source collection based on chosen angle

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Job initiation: <3 seconds
- Status updates: Every 5 seconds
- Full pipeline: <30 minutes for 'deep' mode

### 4.2 Reliability
- Graceful degradation if sources fail
- Automatic retry for transient failures
- Partial results on timeout

### 4.3 Cost Management
- Display estimated cost before job start
- Track actual API costs
- Warning if job exceeds budget
- Kill switch at 2x estimated cost

### 4.4 Security
- API keys never exposed to frontend
- Rate limiting per IP
- Supabase RLS for multi-tenancy
- Input sanitization for all user text

---

## 5. Data Schema Requirements

### 5.1 Database Changes REQUIRED

**SONNET:** Run these migrations FIRST before any code changes:

```sql
-- Remove redundant fields
ALTER TABLE jobs DROP COLUMN IF EXISTS topic;
ALTER TABLE jobs DROP COLUMN IF EXISTS result;

-- Fix pipeline constraint
ALTER TABLE jobs DROP CONSTRAINT jobs_pipeline_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_pipeline_check
  CHECK (pipeline IN ('quick', 'standard', 'deep', 'investigation'));

-- Add missing fields
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS timeline_events JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS entities JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS manual_guidance JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS reddit_posts JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS notebooklm_packet_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_sources INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_claims INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS api_costs JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discovered_angles JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS coverage_analysis JSONB DEFAULT '{}'::jsonb;
```

---

## 6. Integration Requirements

### 6.1 Model Selection Strategy (NEW - Cost Optimization)

**SONNET:** Use the right model for each task to optimize costs without sacrificing quality.

#### OpenAI Model Selection:
```python
# Task-specific model selection
TASK_MODELS = {
    "job_planning": "gpt-4o",              # Complex reasoning needed
    "claim_extraction": "gpt-4o",          # Nuanced understanding required
    "claim_validation_queries": "gpt-4o",  # Precision critical
    "entity_extraction": "gpt-4o-mini",    # Simple pattern matching
    "timeline_extraction": "gpt-4o-mini",  # Date parsing and ordering
    "documentary_analysis": "gpt-4o",      # Creative narrative work
    "angle_discovery": "gpt-4o",           # Strategic thinking needed
}
```

**Cost Impact:**
- Using GPT-4o-mini for entity/timeline extraction saves ~$1.50 per job
- Total savings: ~20-30% per job without quality loss

#### Perplexity Model Selection:
```python
# Use cheaper models for initial discovery
PERPLEXITY_MODELS = {
    "initial_discovery": "sonar",          # Basic search, cheaper
    "claim_validation": "sonar-pro",       # Accuracy critical
    "angle_coverage_analysis": "sonar",    # Volume over precision
}
```

### 6.2 Perplexity Optimization

**Current Issues:**
- Over-reliance on Perplexity for core research
- No caching of repeated queries
- No fallback if Perplexity fails

**New Requirements:**
1. Cache Perplexity responses for 24 hours
2. Fallback to YouTube + Reddit if Perplexity fails
3. Max 10-15 Perplexity queries per job (mode-dependent)
4. Use Perplexity for discovery, not analysis
5. Use basic Sonar model by default, Sonar Pro only when precision critical

### 6.3 API Budget Controls (VALIDATED - January 2025)

**SONNET NOTE:** These costs have been validated against current API pricing as of January 2025.

Per job limits:
- **OpenAI:** Max $3 per job
  - Using GPT-4o: $5/1M input tokens, $15/1M output tokens
  - Typical job uses ~500K tokens combined = $1.50-$3.00
  - Consider GPT-4o-mini ($0.15/1M input) for simpler tasks to reduce costs by 90%
- **Perplexity:** Max $5 per job
  - Sonar models: $0.2-$5 per 1M tokens depending on model
  - Use Sonar (basic) for cost efficiency, Sonar Pro only when needed
  - Includes per-request search fees
  - 10-15 queries with search context = ~$2.00-$5.00
- **YouTube:** Max 1000 quota units
  - FREE with 10,000 units/day default quota
  - Search operation: 100 units, video details: 1-50 units
  - 1000 units = ~10 searches or 20-100 video details
- **Reddit:** Max 100 requests
  - FREE for non-commercial use (100 QPM limit)
  - Commercial tier: $0.24 per 1,000 requests ($0.024 per 100 requests)
  - Ensure project qualifies for free tier (non-commercial research)

#### Cost Breakdown by Mode (Validated):
- **breaking_news:** ~$1.00 actual (budget: $2) - Perplexity $0.45 + OpenAI $0.50
- **investigation:** ~$7-8 actual (budget: $15) - Perplexity $4.50 + OpenAI $2.50-$3.00 + angle discovery $0.50
- **profile:** ~$4-5 actual (budget: $8) - Perplexity $2.50 + OpenAI $1.50-$2.00
- **controversy:** ~$5-6 actual (budget: $10) - Perplexity $3.50 + OpenAI $2.00-$2.50

**Cost Optimization Strategies:**
1. Use GPT-4o-mini for entity extraction and simple parsing tasks
2. Use basic Sonar model for initial discovery, Sonar Pro only for validation
3. Cache Perplexity responses to avoid duplicate queries
4. Batch OpenAI requests where possible to reduce API overhead

---

## 7. Critical Implementation Warnings for Sonnet

### DO NOT:
1. **DO NOT** modify the pipeline to skip stages
2. **DO NOT** combine the 4 research modes into 2
3. **DO NOT** output multiple files for NotebookLM
4. **DO NOT** skip entity/timeline extraction as "optimization"
5. **DO NOT** use print() for debugging - use logger
6. **DO NOT** catch all exceptions - let pipeline handle errors
7. **DO NOT** hardcode API keys anywhere
8. **DO NOT** skip Reddit integration

### YOU MUST:
1. **MUST** implement all 4 research modes exactly as specified
2. **MUST** create timeline extraction from scratch
3. **MUST** create entity extraction from scratch
4. **MUST** output single NotebookLM file
5. **MUST** implement job status polling in frontend
6. **MUST** add cost tracking
7. **MUST** test each pipeline stage independently
8. **MUST** preserve existing working code where possible

---

## 8. Acceptance Criteria

### Core Features
- [ ] 4 research modes working with correct sources
- [ ] Timeline extraction producing chronological events
- [ ] Entity extraction identifying people/orgs/places
- [ ] Single NotebookLM packet file generation
- [ ] Reddit integration fetching real posts
- [ ] Angle discovery system finding unique perspectives

### Frontend
- [ ] Job creation with all options
- [ ] Real-time status updates
- [ ] Results display with download
- [ ] Job history with filtering

### Quality
- [ ] No regression in existing pipeline
- [ ] All stages have error handling
- [ ] Costs tracked per job
- [ ] Manual guidance generated for Reddit/Twitter

---

## 9. Phased Rollout Plan

### Phase 1: Core Features (Week 1)
1. Database migrations
2. Timeline extraction
3. Entity extraction
4. 4 research modes

### Phase 2: Reddit Integration (Week 2)
1. Reddit API setup
2. Subreddit search
3. Comment extraction
4. Integration into pipeline

### Phase 3: Frontend Rebuild (Week 3)
1. Job creation page
2. Status polling
3. Results display
4. History page

### Phase 4: NotebookLM Output (Week 4)
1. Single file generator
2. Markdown formatting
3. Download functionality
4. Testing with actual NotebookLM

### Phase 5: Polish & Deploy (Week 5)
1. Cost optimization
2. Performance tuning
3. Error handling
4. Production deployment

---

## Appendix A: Example Job Configurations

### Quick Mode Job
```json
{
  "mode": "quick",
  "topic": "OpenAI news today",
  "sources": {
    "perplexity_only": true
  },
  "max_duration_minutes": 5,
  "max_cost_usd": 1
}
```

### Investigation Mode Job
```json
{
  "mode": "investigation",
  "topic": "Candace Owens Charlie Kirk controversy",
  "sources": {
    "youtube_channels": ["@RealCandaceO", "@CharlieKirk"],
    "reddit_subreddits": ["r/politics", "r/conservative"],
    "perplexity_queries": 10,
    "time_window": "2024-01-01 to present"
  },
  "validation": {
    "verify_all_claims": true,
    "cross_reference_sources": true
  },
  "max_duration_minutes": 45,
  "max_cost_usd": 15
}
```

---

*END OF PRD - See TEP_v1.md for technical implementation details*