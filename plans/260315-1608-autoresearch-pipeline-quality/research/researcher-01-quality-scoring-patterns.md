# Composite Quality Scoring for AI Pipelines
**Research Report** | 2026-03-15 | Focus: Practical patterns for production systems

---

## 1. Multi-Dimensional Quality Scoring Architecture

Production systems decompose quality into independent dimensions, score each separately, then combine via weighted sum:

**Standard 5-Dimension Model:**
- **Priors** (weight: 0.15) — Model cost efficiency + preference signals
- **Structural Quality** (0.20) — Format correctness, repetition detection, degeneration patterns
- **Semantic Quality** (0.25) — Meaning preservation via embeddings, cosine similarity
- **Query-Output Alignment** (0.15) — Instruction-following consistency
- **Agreement/Uncertainty** (0.15) — Cross-evaluator disagreement as confidence proxy

**Critical insight:** Some intuitive dimensions harm alignment (e.g., alignment dimension showed -0.437 correlation with ground truth). Systematic reliability auditing required—remove unreliable dimensions and re-normalize weights. Default weights are starting points only.

---

## 2. Combining Heterogeneous Metrics: Normalization + Weighting

**Challenge:** Metrics vary widely (0-1 floats, percentages 0-100%, counts, latency ms). Direct averaging fails.

**Solution: Two-Stage Approach**

```python
# Stage 1: Normalize each metric to [0,1] range
def normalize_metric(value, metric_type, bounds=None):
    """Normalize heterogeneous metrics to [0,1]."""
    if metric_type == 'validation_rate':  # Already 0-1
        return value
    elif metric_type == 'percentage':  # 0-100
        return value / 100.0
    elif metric_type == 'bounded':  # Custom [min, max]
        return (value - bounds['min']) / (bounds['max'] - bounds['min'])
    elif metric_type == 'latency_ms':  # Lower is better, capped at threshold
        threshold = bounds.get('max_acceptable', 1000)
        return max(0, 1 - (value / threshold))  # Inverted
    elif metric_type == 'cost':  # Lower is better
        budget = bounds.get('budget', 1.0)
        return max(0, 1 - (value / budget))
    return value

# Stage 2: Weighted composite
def composite_score(metrics_dict, weights_dict):
    """Combine normalized metrics with learned or expert weights."""
    normalized = {}
    for key, value in metrics_dict.items():
        normalized[key] = normalize_metric(
            value,
            metric_type=key.split('_')[0],
            bounds=get_bounds(key)
        )

    # Ensure weights sum to 1.0
    total_weight = sum(weights_dict.values())
    normalized_weights = {k: v/total_weight for k, v in weights_dict.items()}

    composite = sum(
        normalized[k] * normalized_weights[k]
        for k in normalized_weights.keys() if k in normalized
    )
    return composite
```

**Practical weighting strategies:**

1. **Expert-driven:** Subject matter experts assign weights (0.3 validation, 0.25 diversity, 0.25 provenance, 0.2 compliance)
2. **Data-driven:** Logistic regression on historical quality labels to learn optimal weights
3. **Equal weight:** When no ground truth available (0.25 each for 4 dimensions)
4. **Traffic-weighted:** Adjust weights based on production traffic distribution (higher weight on metrics that vary most in real usage)

---

## 3. Quality/Cost Ratio Tracking in LLM Pipelines

**Pattern: Meter → Attribute → Optimize**

**Step 1: Meter (Instrument every call)**
```python
class LLMCallMetrics:
    """Track per-request quality and cost."""
    def __init__(self, job_id, stage_name):
        self.job_id = job_id
        self.stage = stage_name
        self.input_tokens = 0
        self.output_tokens = 0
        self.model_name = None
        self.latency_ms = None
        self.extraction_confidence = None
        self.validation_passed = False

    def cost_usd(self, model_pricing):
        """Calculate cost for this call."""
        input_cost = self.input_tokens / 1000 * model_pricing['input']
        output_cost = self.output_tokens / 1000 * model_pricing['output']
        return input_cost + output_cost

    def quality_score(self):
        """Normalized 0-1 quality signal."""
        return self.extraction_confidence * (1 if self.validation_passed else 0.5)

# Per-job aggregation
job_metrics = {
    'total_cost': sum(call.cost_usd(pricing) for call in calls),
    'avg_quality': mean([call.quality_score() for call in calls]),
    'quality_per_dollar': mean([call.quality_score() / call.cost_usd(pricing) for call in calls]),
    'validation_rate': count(c for c in calls if c.validation_passed) / len(calls)
}
```

**Step 2: Attribute costs to pipeline stages**
- Extraction stage typically 40-50% of total cost
- Validation 5-10% (usually cheaper, code-based)
- Synthesis 30-40% (most expensive, cross-source analysis)

**Step 3: Optimize thresholds**
- Route simple queries to cheaper models (GPT-4o-mini for extraction, GPT-4 for synthesis)
- Use prompt caching: up to 90% cost reduction on cached context tokens
- Implement adaptive sampling: evaluate 100% of low-cost metrics, 5-10% of expensive LLM-based metrics

**Result:** UC Berkeley research shows 60-85% cost reduction while maintaining 95%+ quality through systematic optimization.

---

## 4. Karpathy's Autoresearch: Mechanical Metric Pattern

**Core insight:** The research loop itself is mechanical—hypothesis → code edit → train → score → keep/discard.

**Single mechanical metric: val_bpb (Validation Bits Per Byte)**
```python
# Vocabulary-size-independent measure of compression efficiency
validation_bpb = log2(vocabulary_size) / average_bits_per_byte

# Lower is better (model encodes text more efficiently)
# Properties:
# - Invariant to vocab size (enables fair architectural comparison)
# - Single number to optimize
# - Deterministic + repeatable
```

**Fixed-time evaluation budget:**
- All experiments get same wall-clock time (5 minutes, excluding startup)
- Hardware-agnostic: naturally optimizes for best model achievable in your compute budget
- Enables predictable iteration: ~12 experiments/hour, ~100 overnight

**Mechanical loop implementation:**
```python
def autoresearch_loop(initial_code, metric_fn, iterations=100, time_budget_sec=300):
    """Autonomous research loop—minimize single metric within time."""
    best_score = float('inf')
    best_code = initial_code

    for i in range(iterations):
        # Agent-modified code (hyperparams, architecture)
        candidate_code = agent.propose_modification(best_code)

        # Train with fixed time budget
        start = time.time()
        model = train(candidate_code, timeout=time_budget_sec)
        elapsed = time.time() - start

        # Score on single metric
        score = metric_fn(model)  # e.g., validation_bpb

        # Accept or reject
        if score < best_score:
            best_score = score
            best_code = candidate_code
            print(f"Iter {i}: NEW BEST {score:.4f} (time: {elapsed:.1f}s)")
        else:
            print(f"Iter {i}: rejected {score:.4f}")

    return best_code, best_score
```

**Why this works for composite scoring:**
- Simplicity: single metric prevents metric gaming (multi-objective can lead to adversarial tradeoffs)
- Comparability: vocabulary-size independence ensures fair experiment comparison
- Automation-friendly: agent can understand and optimize single number better than multi-dimensional scores

---

## 5. Production Quality Score Formula (Reference)

**Composite Quality Score = weighted combination of normalized dimensions**

```
Quality_Score = ∑(normalized_dimension_i × weight_i)

Example with 4 dimensions (all normalized to [0,1]):
Q = 0.35 × validation_rate +
    0.25 × source_diversity +
    0.25 × provenance_score +
    0.15 × compliance_score

Where:
- validation_rate = samples_passed / total_samples (already 0-1)
- source_diversity = unique_sources / max_possible_sources
- provenance_score = 1.0 if all items traced to source, else (traced_items / total_items)
- compliance_score = (1 - normalized_violation_count) where violations capped at threshold
```

---

## 6. Implementation Checklist

- [ ] **Identify dimensions:** What signals matter for your domain? (validation, diversity, provenance, compliance, cost, latency)
- [ ] **Bound each dimension:** Establish [min, max] for normalization; test normalization doesn't distort meaning
- [ ] **Choose weighting:** Expert judgment vs. data-driven via regression; validate weights on held-out data
- [ ] **Meter systematically:** Instrument every LLM call; track per-job + per-stage breakdowns
- [ ] **Audit reliability:** Remove dimensions with negative/neutral correlation to ground truth
- [ ] **Re-normalize:** If dimensions removed, recalculate weights so they still sum to 1.0
- [ ] **Document:** Record exact normalization bounds, weights, and thresholds in version control (changes = metric drift)

---

## Sources
- [Multi-Dimensional Quality Scoring Framework for Decentralized LLM Inference](https://arxiv.org/html/2603.04028)
- [Karpathy Autoresearch GitHub](https://github.com/karpathy/autoresearch)
- [scikit-learn Metrics and Scoring Documentation](https://scikit-learn.org/stable/modules/model_evaluation.html)
- [LLM Monitoring: Quality, Cost, Latency, and Drift](https://langwatch.ai/blog/what-is-llm-monitoring-(quality-cost-latency-and-drift-in-production))
- [Normalization Techniques: Min-Max and Z-Score](https://opensearch.org/blog/introducing-the-z-score-normalization-technique-for-hybrid-search/)
- [Feature Scaling in Production Pipelines](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_scaling_importance.html)
- [LLM Evaluation Metrics Guide - Confident AI](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation)
- [Weighting Components of Composite Scores](https://journals.sagepub.com/doi/10.1177/0146621615584703)
