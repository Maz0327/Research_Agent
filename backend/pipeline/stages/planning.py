"""Planning and research mapping stages.

Dec 2025: Added disambiguation support for ambiguous topics.
When LLM detects ambiguity, job pauses for user selection.
"""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job


class DisambiguationRequired(Exception):
    """Raised when job requires user disambiguation before continuing."""

    def __init__(self, job_id: str, interpretations: list):
        self.job_id = job_id
        self.interpretations = interpretations
        super().__init__(f"Job {job_id} requires disambiguation")


def stage_1_planning(ctx: PipelineContext) -> None:
    """Plan job using OpenAI to generate JobConfig.

    Dec 2025: Now handles ambiguous topics by pausing for user selection.
    If topic is ambiguous, sets status="disambiguating" and raises DisambiguationRequired.
    """
    from backend.integrations.openai_client import plan_job, generate_short_title
    from backend.models.job_config import JobConfig

    logger.info(f"[{ctx.job_id}] Stage 1: Planning job")
    update_job(ctx.job_id, stage="planning", progress_percent=5)

    try:
        if not ctx.topic or not ctx.topic.strip():
            raise ValueError("Topic cannot be empty")

        # plan_job now returns dict with is_ambiguous flag
        result = plan_job(ctx.topic)
        # Track OpenAI cost (estimate ~1K tokens for planning)
        ctx.add_cost("openai_planning", 0.002)

        # Check for disambiguation
        if result.get("is_ambiguous"):
            interpretations = result.get("interpretations", [])
            logger.info(f"[{ctx.job_id}] Topic is ambiguous, {len(interpretations)} interpretations found")

            # Store interpretations and pause for user selection
            update_job(
                ctx.job_id,
                status="disambiguating",
                stage="awaiting_disambiguation",
                interpretations=interpretations,
            )

            # Raise to cleanly exit pipeline
            raise DisambiguationRequired(ctx.job_id, interpretations)

        # Non-ambiguous: extract config from result
        ctx.job_config = result.get("config")
        if not isinstance(ctx.job_config, JobConfig):
            raise ValueError(f"plan_job returned invalid type: {type(ctx.job_config)}")

        config_dict = ctx.job_config.model_dump()
        if not config_dict or "topic" not in config_dict:
            raise ValueError("Invalid job_config structure: missing required fields")

        # Load niche overlay if specified
        if ctx.job_config.niche:
            try:
                from backend.pipeline.niche_loader import merge_mode_and_niche, is_valid_niche
                if is_valid_niche(ctx.job_config.niche):
                    ctx.niche_config = merge_mode_and_niche(
                        mode=ctx.job_config.mode.value,
                        niche=ctx.job_config.niche
                    )
                    logger.info(f"[{ctx.job_id}] Loaded niche overlay: {ctx.job_config.niche}")
                else:
                    ctx.add_warning(f"Unknown niche '{ctx.job_config.niche}', ignoring")
            except Exception as niche_error:
                logger.warning(f"[{ctx.job_id}] Failed to load niche: {niche_error}")
                ctx.add_warning(f"Niche loading failed: {str(niche_error)}")

        # Generate short title
        try:
            ctx.short_title = generate_short_title(ctx.topic)
            logger.info(f"[{ctx.job_id}] Generated title: '{ctx.short_title}'")
        except Exception as title_error:
            logger.warning(f"[{ctx.job_id}] Failed to generate title: {title_error}")
            ctx.short_title = " ".join(ctx.topic.split()[:6]).title()
            ctx.add_warning(f"Title generation failed, using fallback: {ctx.short_title}")

        # Save config and title
        job = get_job(ctx.job_id)
        if job:
            update_job(
                ctx.job_id,
                title=ctx.short_title,
                partial_outputs={"config_json": config_dict},
            )
        logger.info(f"[{ctx.job_id}] Planned job: {ctx.job_config.topic}, mode={ctx.job_config.mode}")

    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Planning failed: {e}")
        ctx.add_warning(f"Planning failed: {str(e)}, using default config")
        from backend.integrations.openai_client import _safe_default_config
        ctx.job_config = _safe_default_config(ctx.topic)


def stage_2_research_mapping(ctx: PipelineContext) -> None:
    """Generate research map using Perplexity."""
    from backend.integrations.perplexity_client import research_map

    logger.info(f"[{ctx.job_id}] Stage 2: Generating research map")
    update_job(ctx.job_id, stage="research_mapping", progress_percent=15)

    try:
        result = research_map(ctx.job_config)
        ctx.set_output("research_map_md", result.get("research_map_md", ""))
        ctx.angles = result.get("angles", [])
        ctx.key_terms = result.get("key_terms", [])
        # Track Perplexity cost (~$0.005 per search)
        ctx.add_cost("perplexity_research_map", 0.005)
        logger.info(f"[{ctx.job_id}] Generated research map with {len(ctx.angles)} angles")
    except Exception as e:
        logger.warning(f"[{ctx.job_id}] Research map generation failed: {e}")
        ctx.add_warning(f"Research map generation failed: {str(e)}")
        ctx.set_output("research_map_md", f"# Research Map\n\n*Error: {str(e)}*")
