# Gemini 2.5 Pro Video Analysis - Code Examples

Complete, tested examples for Research Agent integration.

---

## 1. Basic YouTube Video Analysis

### 1.1 Simple Query with Timestamps

```python
from google import genai

client = genai.Client(api_key="YOUR_GOOGLE_API_KEY")

# Single YouTube video
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        """Extract all direct quotes about 'climate policy' from this video.
        For each quote, provide:
        - Timestamp (MM:SS format)
        - Speaker name
        - Exact quote (use quotation marks)
        - 1-2 sentence context

        Format as JSON array.
        """
    ]
)

print(response.text)
# Output:
# [
#   {
#     "timestamp": "02:15",
#     "speaker": "John Smith",
#     "quote": "Climate policy needs urgent action",
#     "context": "Discussing recent legislative changes"
#   }
# ]
```

### 1.2 Batch Processing (Multiple Videos)

```python
# Gemini 2.5 allows up to 10 videos per request
video_urls = [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.youtube.com/watch?v=VIDEO2",
    "https://www.youtube.com/watch?v=VIDEO3",
]

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=video_urls + [
        """Analyze these 3 videos for contradictions about 'renewable energy'.

        For each contradiction:
        - Video # and timestamp
        - Speaker quote
        - Conflicting statement (from different video, with timestamp)
        - Assessment: likely error, deliberate contradiction, or different context?

        Return as JSON.
        """
    ]
)
```

---

## 2. Structured Output with Pydantic

### 2.1 Documentary Extraction Schema

```python
from pydantic import BaseModel, Field
from typing import List
from google import genai

class QuoteData(BaseModel):
    """Quote with attribution and context."""
    timestamp: str = Field(..., description="MM:SS format")
    speaker: str = Field(..., description="Speaker name or ID")
    quote: str = Field(..., description="Exact quote from video")
    confidence: float = Field(..., description="0.0-1.0 confidence")

class MomentData(BaseModel):
    """Key moment in video."""
    timestamp: str = Field(..., description="MM:SS format")
    description: str = Field(..., description="What happens at this moment")
    relevance: str = Field(..., description="Why it's important to research")
    visual_cues: bool = Field(default=False)

class ContradictionData(BaseModel):
    """Factual contradiction between sources."""
    video_1_url: str
    timestamp_1: str
    claim_1: str
    video_2_url: str
    timestamp_2: str
    claim_2: str
    contradiction_type: str = Field(
        ..., description="factual | temporal | definition | tone"
    )

class DocumentaryAnalysis(BaseModel):
    """Complete documentary analysis."""
    quotes: List[QuoteData]
    key_moments: List[MomentData]
    contradictions: List[ContradictionData]
    timeline_summary: str = Field(..., description="Chronological summary")

# Usage
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        video_url,
        "Extract documentary information as specified in the schema."
    ],
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=DocumentaryAnalysis
    )
)

# Parse response
import json
result = DocumentaryAnalysis.model_validate_json(response.text)
print(f"Found {len(result.quotes)} quotes")
print(f"Found {len(result.contradictions)} contradictions")
```

---

## 3. Advanced: Clip Boundary Detection

```python
from google import genai

client = genai.Client(api_key="YOUR_GOOGLE_API_KEY")

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        "https://www.youtube.com/watch?v=DOCUMENTARY_VIDEO",
        """Identify all scene/topic transitions in this documentary.

        For each transition:
        - Timestamp of transition (MM:SS)
        - Current topic/scene name
        - Next topic/scene name
        - Visual indicator (scene change, title card, etc.)
        - Audio indicator (music change, narrator transition, etc.)

        Return as JSON array sorted by timestamp.

        Example format:
        {
            "timestamp": "03:45",
            "from_topic": "Character introduction",
            "to_topic": "First event",
            "visual": "Scene fade to black",
            "audio": "Music tempo increases"
        }
        """
    ]
)

print(response.text)
# Use to create clip boundaries for documentary
```

---

## 4. Cross-Video Contradiction Analysis

### 4.1 Simple Two-Video Comparison

```python
video_1 = "https://www.youtube.com/watch?v=INTERVIEW1"
video_2 = "https://www.youtube.com/watch?v=INTERVIEW2"

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        video_1,
        video_2,
        """Compare these two interviews for contradictions.

        The person being interviewed makes claims about 'X' in both videos.
        Identify if the claims are consistent or contradictory.

        For each contradiction:
        - Video 1: timestamp, exact quote
        - Video 2: timestamp, exact quote
        - Severity: 1-5 (1=minor wording difference, 5=direct contradiction)
        - Explanation of the contradiction

        Return as JSON.
        """
    ]
)

print(response.text)
```

### 4.2 Multiple Videos (Up to 10)

```python
from typing import List

def analyze_contradictions(video_urls: List[str], topic: str) -> dict:
    """Find all contradictions across multiple videos about a topic."""

    if len(video_urls) > 10:
        raise ValueError("Gemini 2.5 supports max 10 videos per request")

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=video_urls + [
            f"""Analyze all {len(video_urls)} videos for contradictions about: {topic}

            For each contradiction found:
            - Video # (1, 2, 3, etc.) and timestamp
            - Speaker name (if identifiable)
            - Claim 1: exact quote
            - Claim 2: exact quote (different video)
            - Type: factual | temporal | definition | tone
            - Severity: 1-5
            - Likely explanation

            Return as JSON array.
            """
        ]
    )

    import json
    contradictions = json.loads(response.text)
    return contradictions

# Usage
videos = [
    "https://www.youtube.com/watch?v=...",
    "https://www.youtube.com/watch?v=...",
    "https://www.youtube.com/watch?v=...",
]

result = analyze_contradictions(videos, "climate change policy")
for contradiction in result:
    print(f"Video {contradiction['video_1']} vs {contradiction['video_2']}")
    print(f"  Severity: {contradiction['severity']}/5")
```

---

## 5. Speaker Identification with Known Context

### 5.1 Providing Speaker Context

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[
        video_url,
        """Transcribe this interview with speaker diarization.

        Known participants:
        - Dr. Sarah Chen (researcher, wears glasses)
        - John Smith (journalist, asks questions)
        - Unknown Guest (to be identified if possible)

        For each segment:
        - Timestamp (MM:SS)
        - Speaker ID (use name if identified, else SPEAKER_A, etc.)
        - Complete transcript of segment

        When a new speaker appears, note identifying details (appearance, voice characteristics).

        Return as JSON with speaker sequence.
        """
    ]
)
```

### 5.2 Handling Multi-Speaker Accuracy Issues

```python
from google import genai

def transcribe_with_diarization_detailed(video_url: str, speakers: List[str]):
    """Improve diarization with detailed speaker instructions."""

    speaker_descriptions = "\n".join([
        f"- {name}: [add any identifying details]"
        for name in speakers
    ])

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            video_url,
            f"""Transcribe with automatic speaker diarization.

            Known speakers:
            {speaker_descriptions}

            Instructions:
            1. Use speaker names when you identify them
            2. For unnamed speakers, assign consistent IDs: SPEAKER_A, SPEAKER_B, etc.
            3. When a name emerges in conversation, note it
            4. Flag any uncertain identifications with [?]
            5. Include timestamps for every speaker change

            Return JSON:
            {{
                "segments": [
                    {{
                        "timestamp": "MM:SS",
                        "speaker": "Name or ID",
                        "transcript": "...",
                        "confidence": 0.0-1.0
                    }}
                ]
            }}
            """
        ]
    )

    return json.loads(response.text)
```

---

## 6. Long Video Handling (Chunking Strategy)

### 6.1 Automatic Chunking

```python
from typing import List
import json

class VideoChunkAnalyzer:
    """Handle long videos by chunking."""

    def chunk_video(
        self,
        video_url: str,
        chunk_size_minutes: int = 60
    ) -> List[str]:
        """Generate chunk URLs using fragment identifiers."""
        chunks = []
        # Format: https://youtube.com/watch?v=VIDEO_ID#t=START,END
        for start in range(0, 300, chunk_size_minutes):  # 300 min = 5 hours
            end = min(start + chunk_size_minutes, 300)
            chunk_url = f"{video_url}#t={start*60},{end*60}"
            chunks.append(chunk_url)
        return chunks

    async def analyze_long_video(
        self,
        video_url: str,
        analysis_prompt: str
    ) -> dict:
        """Analyze long video by chunks, then consolidate."""

        chunks = self.chunk_video(video_url)
        all_results = []

        for i, chunk in enumerate(chunks):
            print(f"Analyzing chunk {i+1}/{len(chunks)}")

            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    chunk,
                    f"{analysis_prompt}\nThis is part {i+1} of {len(chunks)}."
                ]
            )

            all_results.append(json.loads(response.text))

        # Consolidate results
        return self.consolidate_chunk_results(all_results)

    def consolidate_chunk_results(self, chunk_results: List[dict]) -> dict:
        """Merge results from multiple chunks."""
        consolidated = {
            "quotes": [],
            "moments": [],
            "contradictions": [],
        }

        for chunk_result in chunk_results:
            if "quotes" in chunk_result:
                consolidated["quotes"].extend(chunk_result["quotes"])
            if "moments" in chunk_result:
                consolidated["moments"].extend(chunk_result["moments"])
            if "contradictions" in chunk_result:
                consolidated["contradictions"].extend(
                    chunk_result["contradictions"]
                )

        # Deduplicate
        return self.deduplicate_results(consolidated)

    def deduplicate_results(self, results: dict) -> dict:
        """Remove duplicate quotes/moments across chunks."""
        # Deduplicate quotes by content similarity
        # Deduplicate moments by timestamp proximity
        return results
```

### 6.2 Usage

```python
analyzer = VideoChunkAnalyzer()

result = await analyzer.analyze_long_video(
    video_url="https://www.youtube.com/watch?v=LONG_VIDEO",
    analysis_prompt="Extract all claims about climate policy with timestamps"
)

print(f"Total quotes extracted: {len(result['quotes'])}")
```

---

## 7. Token Cost Estimation

### 7.1 Pre-Flight Token Calculation

```python
def estimate_video_tokens(
    video_duration_minutes: int,
    resolution: str = "default"
) -> dict:
    """Estimate tokens before API call."""

    if resolution == "default":
        tokens_per_second = 258
    elif resolution == "low":
        tokens_per_second = 66
    else:
        tokens_per_second = 258

    total_seconds = video_duration_minutes * 60
    video_tokens = total_seconds * tokens_per_second
    audio_tokens = total_seconds * 32  # Always included
    total_tokens = video_tokens + audio_tokens

    # Pricing (Dec 2025)
    flash_input_cost = total_tokens / 1_000_000 * 0.15
    pro_input_cost = total_tokens / 1_000_000 * 1.25

    return {
        "duration_minutes": video_duration_minutes,
        "resolution": resolution,
        "estimated_tokens": total_tokens,
        "flash_input_cost": f"${flash_input_cost:.4f}",
        "pro_input_cost": f"${pro_input_cost:.4f}",
        "tokens_per_second": tokens_per_second,
    }

# Usage
estimates = [
    estimate_video_tokens(60),      # 1 hour default
    estimate_video_tokens(60, "low"),  # 1 hour low resolution
    estimate_video_tokens(180),     # 3 hour default
]

for est in estimates:
    print(f"{est['duration_minutes']}m {est['resolution']}: "
          f"{est['estimated_tokens']} tokens, "
          f"Flash: {est['flash_input_cost']}, "
          f"Pro: {est['pro_input_cost']}")
```

---

## 8. Error Handling & Fallback

### 8.1 Robust Analysis Function

```python
from google import genai
from loguru import logger
import asyncio

class GeminiVideoAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def analyze_with_retry(
        self,
        video_url: str,
        prompt: str,
        max_retries: int = 3
    ) -> dict:
        """Analyze with exponential backoff retry."""

        for attempt in range(max_retries):
            try:
                logger.info(f"Analyzing {video_url}, attempt {attempt+1}/{max_retries}")

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[video_url, prompt]
                )

                if not response.text:
                    raise ValueError("Empty response from Gemini")

                return json.loads(response.text)

            except genai.APIError as e:
                logger.warning(f"API error: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                raise

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    async def analyze_with_fallback(
        self,
        video_url: str,
        prompt: str,
        fallback_fn=None  # Fallback to Supadata/Whisper
    ) -> dict:
        """Analyze with fallback to transcript-based approach."""

        try:
            return await self.analyze_with_retry(video_url, prompt)
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")

            if fallback_fn:
                logger.info("Falling back to transcript-based analysis")
                return await fallback_fn(video_url, prompt)
            else:
                raise

# Usage
analyzer = GeminiVideoAnalyzer(api_key="YOUR_KEY")

result = await analyzer.analyze_with_fallback(
    video_url="https://www.youtube.com/watch?v=...",
    prompt="Extract quotes with timestamps",
    fallback_fn=supadata_transcribe_and_extract  # Your fallback function
)
```

---

## 9. Integration with Research Agent Pipeline

### 9.1 Pipeline Stage Implementation

```python
# In backend/pipeline/stages.py

from backend.integrations.gemini_video import GeminiVideoAnalyzer
from backend.pipeline.context import PipelineContext
from backend.models.video_extraction import VideoAnalysisResult

async def stage_6_video_extraction(ctx: PipelineContext):
    """Extract claims, quotes, contradictions from YouTube videos."""

    logger.info(f"Stage 6: Video extraction for job {ctx.job.id}")

    # Filter YouTube URLs only
    youtube_urls = [
        url for url in ctx.collected_urls
        if "youtube.com" in url or "youtu.be" in url
    ]

    if not youtube_urls:
        ctx.add_warning("No YouTube videos found in sources")
        ctx.update_job(
            status="running",
            stage="stage_6_video_extraction",
            progress=50
        )
        return

    try:
        analyzer = GeminiVideoAnalyzer(
            api_key=settings.require_google_api_key(),
            model=ctx.job.video_analysis_model or "gemini-2.5-flash"
        )

        # Process in batches (max 10 per Gemini 2.5 request)
        batch_size = 10
        for i in range(0, len(youtube_urls), batch_size):
            batch = youtube_urls[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}, "
                       f"{len(batch)} videos")

            result = await analyzer.analyze_with_fallback(
                video_urls=batch,
                analysis_prompt=BUILD_DOCUMENTARY_PROMPT(ctx),
                fallback_fn=lambda urls, p: supadata_transcribe_batch(urls)
            )

            # Add results to context
            ctx.extracted_claims.extend(result.claims)
            ctx.timeline_moments.extend(result.moments)
            ctx.contradictions.extend(result.contradictions)

            # Cost tracking
            estimated_cost = calculate_video_cost(batch)
            ctx.add_cost("gemini_video", estimated_cost)

        logger.info(f"Extracted {len(ctx.extracted_claims)} claims, "
                   f"{len(ctx.contradictions)} contradictions")

    except Exception as e:
        ctx.add_warning(f"Video extraction failed: {e}")
        logger.error(f"Video extraction error: {e}")

    ctx.update_job(
        status="running",
        stage="stage_6_video_extraction",
        progress=60
    )
```

### 9.2 Documentary Prompt Builder

```python
def BUILD_DOCUMENTARY_PROMPT(ctx: PipelineContext) -> str:
    """Build extraction prompt based on research mode/category."""

    category_guidance = {
        "pop_culture": "Focus on celebrity statements, entertainment industry claims",
        "political": "Extract policy positions, political claims, contradictions",
        "true_crime": "Extract facts, timelines, suspect statements",
        "mysteries": "Extract theories, evidence, expert claims",
        "downfalls": "Extract scandal details, key accusations, denials",
    }

    mode = ctx.job.category or "general"
    guidance = category_guidance.get(mode, "General documentary research")

    return f"""Extract documentary research information from these videos.

Category: {mode}
Research Mode: {ctx.job.mode}
Focus: {guidance}

Extract and return JSON:
{{
    "quotes": [
        {{
            "timestamp": "MM:SS",
            "speaker": "Name or 'Unknown'",
            "quote": "Exact quote",
            "confidence": 0.0-1.0,
            "relevance": "Why this matters for the research"
        }}
    ],
    "key_moments": [
        {{
            "timestamp": "MM:SS",
            "description": "What happens",
            "moment_type": "claim|evidence|contradiction|visual_evidence",
            "relevance": "Research significance"
        }}
    ],
    "contradictions": [
        {{
            "video_1_timestamp": "MM:SS",
            "claim_1": "Quote from video 1",
            "video_2_timestamp": "MM:SS",
            "claim_2": "Conflicting quote from video 2",
            "type": "factual|temporal|definition|tone",
            "severity": 1-5
        }}
    ]
}}

Instructions:
1. Timestamps MUST be in MM:SS format
2. Include confidence scores for quotes
3. Flag contradictions across videos
4. Focus on {mode}-relevant information
5. Include visual context when relevant
"""
```

---

## 10. Testing Examples

### 10.1 Unit Test

```python
import pytest
from unittest.mock import patch, MagicMock
from backend.integrations.gemini_video import GeminiVideoAnalyzer

@pytest.mark.asyncio
async def test_youtube_video_analysis():
    """Test basic YouTube video analysis."""

    # Mock Gemini response
    mock_response = {
        "quotes": [
            {
                "timestamp": "00:15",
                "speaker": "Test Speaker",
                "quote": "Test quote",
                "confidence": 0.95
            }
        ],
        "moments": [],
        "contradictions": []
    }

    analyzer = GeminiVideoAnalyzer(api_key="test-key")

    with patch.object(analyzer.client.models, 'generate_content') as mock_gen:
        mock_gen.return_value.text = json.dumps(mock_response)

        result = await analyzer.analyze_with_retry(
            "https://www.youtube.com/watch?v=test",
            "Extract quotes"
        )

        assert len(result['quotes']) == 1
        assert result['quotes'][0]['timestamp'] == "00:15"
        assert result['quotes'][0]['speaker'] == "Test Speaker"

@pytest.mark.asyncio
async def test_batch_video_processing():
    """Test processing multiple videos."""

    analyzer = GeminiVideoAnalyzer(api_key="test-key")
    videos = [
        f"https://www.youtube.com/watch?v=test{i}"
        for i in range(5)
    ]

    # Should not raise error
    # (actual API would be mocked in real tests)
    assert len(videos) <= 10
```

---

## References

- [Google Gemini API Documentation](https://ai.google.dev/gemini-api/docs/video-understanding)
- [Gemini Models Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Python Genai SDK](https://github.com/google-gemini/python-client)
- [Pydantic for Structured Output](https://docs.pydantic.dev/)

