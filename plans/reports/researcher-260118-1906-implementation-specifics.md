# Hallucination Prevention: Implementation Specifics

**Target:** Tier 1 + Tier 2 recommendations from audit

---

## TIER 1: High-Priority Implementations

### 1. Explicit Uncertainty Instruction in Prompts

**Location:** `backend/pipeline/prompts/modes/base.py` → `SYSTEM_MESSAGE` or `EXTRACTION_GUARDRAILS`

**Current State:**
```python
# base.py has:
# - Source identity lock block
# - Confidence ceiling declaration
# - Source identity contract
# - Quality constraints

# Missing: Explicit uncertainty handling
```

**Implementation:**
```python
UNCERTAINTY_HANDLING = """
## WHEN UNCERTAIN

If you are uncertain about any extraction:
1. Do NOT speculate or fabricate supporting material
2. Do NOT claim certainty you don't have
3. Mark confidence as LOW
4. Add explanation to analysis_limitations:
   "Uncertainty [reason]: Could not determine [what] with confidence"

EXAMPLES:
- "Uncertainty: Speaker identity unclear - could not reliably attribute quote"
- "Uncertainty: Timestamp ambiguous - speaker timeline inconsistent"
- "Uncertainty: Theme barely evident - may be misinterpretation of single statement"
"""

# Add to build_base_prompt():
prompt = f"""
{source_identity_lock_block}
{confidence_ceiling_declaration}
{UNCERTAINTY_HANDLING}  # <-- NEW
...
"""
```

**Validation:** Check that any output with LOW confidence includes matching `analysis_limitations` entry.

**Cost:** 1-2 hours

---

### 2. Citation Trace Model

**Location:** `backend/models/semantic_units.py` → Add new dataclass

**Purpose:** Explicit "show your work" for each claim derivation.

**Implementation:**
```python
@dataclass
class CitationTrace:
    """
    Explicit provenance chain for a claim.

    Shows: Claim → Supporting Quote(s) → Source Location(s)
    """
    claim_id: str
    claim_statement: str

    # Quote level
    supporting_quotes: list[dict] = field(default_factory=list)
    # Format: [{"quote_id": "QT_1", "text": "...", "timestamp": "0:30"}]

    # Confidence justification
    confidence: ConfidenceLevel
    confidence_reasoning: str
    # Examples:
    # - "Confidence: HIGH - Direct verbatim quote with timestamp"
    # - "Confidence: MEDIUM - Quote slightly paraphrased in extraction"
    # - "Confidence: LOW - Inferred from multiple partial observations"

    # Metadata
    source_id: str
    analysis_mode: AnalysisMode

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claim_statement": self.claim_statement,
            "supporting_quotes": self.supporting_quotes,
            "confidence": self.confidence.value,
            "confidence_reasoning": self.confidence_reasoning,
            "source_id": self.source_id,
            "analysis_mode": self.analysis_mode.value,
        }
```

**Integration Point:** In `stage_semantic_extraction()`, after parsing:
```python
result, validation_report, cost = extract_semantic_structure(...)

# NEW: Build citation traces
citation_traces = []
for claim in result.claims:
    trace = build_citation_trace(
        claim=claim,
        quotes=result.quotes,  # Available quotes in result
        confidence_justification=...  # From validation report
    )
    citation_traces.append(trace)

result.citation_traces = citation_traces
```

**Validation:** Each claim must have at least one citation trace. Traces must reference valid quote_ids or observations.

**Cost:** 3-4 hours

---

### 3. Enhanced Quote Verification: Add Semantic Grounding

**Location:** `backend/pipeline/quote_verification.py` → Extend `verify_quote()`

**Current State:**
```python
def verify_quote(quote_text: str, transcript: str) -> dict:
    # Returns: verified (bool), score (0.0-1.0), status (str)
    # Only checks: Does quote text exist in transcript?
```

**New Implementation:**
```python
def verify_quote_semantic(
    quote_text: str,
    claim_statement: str,
    transcript: str,
    fuzzy_threshold: float = 0.7,
) -> dict:
    """
    Enhanced quote verification with semantic grounding.

    Returns:
    {
        "verified": bool,
        "score": float,  # Fuzzy match score
        "semantic_alignment": float,  # NEW: Does quote support claim?
        "status": "VERIFIED" | "UNCERTAIN" | "LIKELY_HALLUCINATED" | "MISALIGNED",
        "details": {
            "fuzzy_match": "...",
            "semantic_issue": "..." if misaligned
        }
    }
    """
    # Step 1: Fuzzy match (current)
    fuzzy_result = verify_quote(quote_text, transcript, threshold=fuzzy_threshold)

    # Step 2: NEW - Semantic alignment check
    if fuzzy_result["status"] != "LIKELY_HALLUCINATED":
        alignment = _check_semantic_alignment(quote_text, claim_statement)
        # alignment: 0.0-1.0 (higher = quote clearly supports claim)

        if alignment < 0.5:
            # Quote exists but doesn't support this specific claim
            return {
                "verified": False,
                "score": fuzzy_result["score"],
                "semantic_alignment": alignment,
                "status": "MISALIGNED",
                "details": {
                    "fuzzy_match": f"Found in transcript (score={fuzzy_result['score']:.2f})",
                    "semantic_issue": f"Quote doesn't support claim (alignment={alignment:.2f})"
                }
            }

    return {
        "verified": fuzzy_result["verified"],
        "score": fuzzy_result["score"],
        "semantic_alignment": _check_semantic_alignment(quote_text, claim_statement),
        "status": fuzzy_result["status"],
        "details": fuzzy_result.get("details", {})
    }

def _check_semantic_alignment(quote_text: str, claim_statement: str) -> float:
    """
    Check if quote semantically aligns with claim.

    Simple implementation (low cost):
    1. Extract key concepts from both
    2. Calculate overlap (Jaccard similarity on concepts)

    Could upgrade to embeddings later if needed.
    """
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords

    stop = set(stopwords.words('english'))

    quote_words = set(w.lower() for w in word_tokenize(quote_text)
                      if w.isalnum() and w.lower() not in stop)
    claim_words = set(w.lower() for w in word_tokenize(claim_statement)
                      if w.isalnum() and w.lower() not in stop)

    if not quote_words or not claim_words:
        return 0.5  # Neutral if can't extract concepts

    # Jaccard similarity
    intersection = quote_words & claim_words
    union = quote_words | claim_words
    return len(intersection) / len(union)
```

**Integration:** In `verify_quotes_in_extraction()`:
```python
for claim in result.claims:
    verified_supporting = []
    for quote_text in claim.supporting_quotes:
        # NEW: Use semantic verification
        verification = verify_quote_semantic(
            quote_text=quote_text,
            claim_statement=claim.statement,
            transcript=transcript
        )

        if verification["status"] == "MISALIGNED":
            warnings.append(
                f"Claim {claim.claim_id}: supporting quote found in transcript "
                f"but doesn't semantically support claim "
                f"(alignment={verification['semantic_alignment']:.2f})"
            )
            # Don't include in verified quotes
        elif verification["status"] != "LIKELY_HALLUCINATED":
            verified_supporting.append(quote_text)
        else:
            warnings.append(
                f"Claim {claim.claim_id}: supporting quote not found in transcript"
            )

    claim.supporting_quotes = verified_supporting
```

**Validation:** Misaligned quotes flagged; LOW confidence auto-applied if all quotes removed.

**Cost:** 4-6 hours

---

## TIER 2: Medium-Priority Implementations

### 4. Cross-Source Consistency Validation

**Location:** New file `backend/pipeline/consistency_validator.py`

**Purpose:** For multi-source jobs, detect when same claim gets different treatment across sources.

**Implementation:**
```python
def validate_cross_source_consistency(
    extractions: list[SemanticExtractionResult]
) -> dict:
    """
    Check for consistency across multiple source extractions.

    Returns:
    {
        "consistent": bool,
        "issues": [
            {
                "type": "conflicting_claims",
                "sources": ["SRC_1", "SRC_2"],
                "details": "Same topic, contradictory claims detected"
            }
        ],
        "confidence_warnings": [...]
    }
    """
    issues = []

    # Extract all key point concepts
    source_concepts = {}
    for extraction in extractions:
        concepts = set()
        for kp in extraction.key_points:
            # Extract key concepts (noun phrases, entities)
            concepts.update(_extract_concepts(kp.statement))
        source_concepts[extraction.source_id] = concepts

    # Find overlapping concepts
    all_concepts = set()
    for concepts in source_concepts.values():
        all_concepts.update(concepts)

    # For each concept appearing in 2+ sources, check consistency
    for concept in all_concepts:
        sources_with_concept = [
            sid for sid, concepts in source_concepts.items()
            if concept in concepts
        ]

        if len(sources_with_concept) >= 2:
            # Get claims about this concept from each source
            claims_by_source = {}
            for extraction in extractions:
                if extraction.source_id in sources_with_concept:
                    relevant_kps = [
                        kp for kp in extraction.key_points
                        if concept in _extract_concepts(kp.statement)
                    ]
                    claims_by_source[extraction.source_id] = relevant_kps

            # Check for contradictions
            contradiction = _detect_contradiction(claims_by_source)
            if contradiction:
                issues.append({
                    "type": "conflicting_claims",
                    "concept": concept,
                    "sources": sources_with_concept,
                    "details": contradiction
                })

    return {
        "consistent": len(issues) == 0,
        "issues": issues,
        "confidence_warnings": [
            f"Cross-source inconsistency detected: {issue['details']}"
            for issue in issues
        ]
    }

def _extract_concepts(text: str) -> set[str]:
    """Extract noun phrases / key concepts from text."""
    # Simple implementation: extract capitalized words + key nouns
    # Could upgrade to NLP library later
    import re

    # Capitalized sequences (likely entities)
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    return set(entities)

def _detect_contradiction(claims_by_source: dict) -> Optional[str]:
    """Detect contradictions between claims from different sources."""
    # Simple heuristic: check for opposite sentiments/modifiers
    # E.g., "succeeded" vs "failed", "yes" vs "no"

    opposite_pairs = [
        ("success", "failure"), ("failed", "succeeded"),
        ("yes", "no"), ("true", "false"),
        ("increase", "decrease"), ("gain", "loss"),
        ("support", "oppose"), ("agree", "disagree"),
    ]

    all_statements = []
    for statements in claims_by_source.values():
        all_statements.extend([s.statement for s in statements])

    for stmt1 in all_statements:
        for stmt2 in all_statements:
            if stmt1 != stmt2:
                for pair in opposite_pairs:
                    if pair[0] in stmt1.lower() and pair[1] in stmt2.lower():
                        return f"'{pair[0]}' vs '{pair[1]}' detected in different sources"

    return None
```

**Integration:** In synthesis stage, after all extractions complete:
```python
if len(ctx.semantic_extractions) >= 2:
    consistency_report = validate_cross_source_consistency(ctx.semantic_extractions)

    for warning in consistency_report["confidence_warnings"]:
        ctx.add_warning(warning)

    if not consistency_report["consistent"]:
        # Downgrade synthesis confidence
        ctx.synthesis_confidence_cap = ConfidenceLevel.MEDIUM
```

**Cost:** 6-8 hours

---

### 5. Reasoning Trace Collection

**Location:** Modify all prompts → Add reasoning extraction

**Purpose:** LLM explains its extraction reasoning; enables post-hoc validation.

**Implementation:**
```python
# Add to all mode-specific prompts:

REASONING_TRACE_INSTRUCTIONS = """
## EXTRACTION REASONING

For each item you extract (key point, claim, theme, tension):
Explain your reasoning in 1-2 sentences.

Examples:
- Key Point KP_1: "Extracted because speaker explicitly states this transition"
- Claim CLM_2: "Supported by QT_3 which shows direct evidence"
- Theme THEME_1: "Identified pattern across KP_1, KP_3, KP_5"

Include this in your response as 'extraction_reasoning' field.
"""

# Update schema to include:
@dataclass
class SemanticExtractionSchema:
    # ... existing fields ...
    extraction_reasoning: dict = field(default_factory=dict)
    # Format:
    # {
    #   "KP_1": "Reasoning text",
    #   "CLM_1": "Reasoning text",
    #   "THEME_1": "Reasoning text"
    # }
```

**Validation:**
```python
def validate_reasoning_completeness(extraction: dict) -> list[str]:
    """Check that each item has reasoning."""
    warnings = []
    reasoning = extraction.get("extraction_reasoning", {})

    for kp in extraction.get("key_points", []):
        if kp["key_point_id"] not in reasoning:
            warnings.append(f"No reasoning provided for {kp['key_point_id']}")

    return warnings
```

**Cost:** 4-6 hours

---

### 6. Hallucination Feedback Loop Infrastructure

**Location:** New `backend/pipeline/hallucination_log.py`

**Purpose:** Track detected hallucinations to improve prompts over time.

**Implementation:**
```python
@dataclass
class HalluccinationEvent:
    """Record of detected hallucination."""
    event_id: str
    job_id: str
    source_id: str

    # What was hallucinated
    hallucinated_item: str  # Type: "quote", "claim", "keypoint"
    text: str

    # How it was detected
    detection_method: str  # "quote_verification", "consistency", "semantic_mismatch"

    # Characteristics
    hallucination_type: str  # "fabrication", "drift", "misalignment", "contradiction"
    pattern: str  # Natural language description

    # Metadata
    analysis_mode: str
    timestamp: str


def log_hallucination(
    job_id: str,
    source_id: str,
    item_type: str,
    text: str,
    detection_method: str,
) -> None:
    """Record a detected hallucination."""
    event = HalluccinationEvent(
        event_id=f"HALL_{uuid.uuid4()}",
        job_id=job_id,
        source_id=source_id,
        hallucinated_item=item_type,
        text=text,
        detection_method=detection_method,
        hallucination_type=_classify_hallucination_type(text, item_type),
        pattern=_generate_pattern_description(text, item_type),
        analysis_mode="...",
        timestamp=datetime.now().isoformat(),
    )

    # Store in DB/log file
    _store_hallucination_event(event)

    logger.warning(f"Hallucination logged: {event.event_id}")


async def generate_hallucination_report(days: int = 7) -> dict:
    """Generate report on detected hallucinations in past N days."""
    events = _fetch_hallucination_events(days=days)

    return {
        "period": f"Last {days} days",
        "total_detected": len(events),
        "by_type": Counter(e.hallucination_type for e in events),
        "by_detection_method": Counter(e.detection_method for e in events),
        "by_mode": Counter(e.analysis_mode for e in events),
        "common_patterns": _extract_common_patterns(events),
        "recommendations": _generate_recommendations(events),
    }
```

**Integration Points:**
```python
# In quote_verification:
if verification["status"] == "LIKELY_HALLUCINATED":
    log_hallucination(
        job_id=ctx.job_id,
        source_id=result.source_id,
        item_type="quote",
        text=quote.text,
        detection_method="quote_verification"
    )

# In consistency_validator:
if not consistency_report["consistent"]:
    for issue in consistency_report["issues"]:
        log_hallucination(
            job_id=ctx.job_id,
            source_id="multi_source",
            item_type="keypoint",
            text=issue["details"],
            detection_method="consistency_check"
        )
```

**Cost:** 8-10 hours (infrastructure setup)

---

## Testing Strategy

### Unit Tests
- Verify `verify_quote_semantic()` correctly identifies misaligned quotes
- Verify `validate_cross_source_consistency()` detects contradictions
- Verify citation traces reference valid quote IDs

### Integration Tests
- End-to-end extraction with semantic verification
- Multi-source job with consistency checks
- Hallucination logging and retrieval

### Validation Tests
- Sample 100 extractions
- Manually verify hallucination detection rate
- Compare to baseline (current system)

---

## Rollout Plan

1. **Week 1:** Implement Tier 1 (Uncertainty + Citation Traces + Semantic Verification)
2. **Week 2:** Test + validation
3. **Week 3:** Implement Tier 2 (Consistency + Reasoning + Logging)
4. **Week 4:** Integration testing + production deployment

---

## Metrics to Track

**Before:**
- Hallucination rate (estimated from manual sampling)
- Quote verification removal rate (currently ~X%)
- Validation hard-fail rate

**After:**
- Hallucination rate (target: <10%)
- Quote removal rate by type (fabrication vs. drift)
- Cross-source contradiction detection rate
- Reasoning trace completeness (target: 100%)

