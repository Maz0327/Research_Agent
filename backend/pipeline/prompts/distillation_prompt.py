"""Distillation Prompt - produces the Claim Graph from synthesis output.

Based on: plans/260814-claim-graph-briefing/spec.md Sections 2 and 5

This prompt NEVER sees raw source text as license to add facts. It receives
already-extracted structure (key points, themes, tensions, gaps) plus source
metadata, and its job is to select, fold, and re-voice - never to add.

Three things in here are load-bearing and were chosen against documented
failure modes, not taste:

1. SCOPE DISCIPLINE. Sonnet 5's documented failure mode is doing more than
   asked despite strict instructions. For a "distill these claims, add
   NOTHING" stage that is precisely the wrong direction, so the block is
   explicit and the no-new-facts validator backs it up.

2. Key-point IDs are PER-SOURCE, not global. The fixture job has 40 key points
   sharing 14 IDs; KP_1 alone appears six times across different sources.
   Anything that treats a bare key-point ID as unique silently merges
   unrelated material.

3. Prose fields must be connected prose. Fragment-scaffold phrasing like
   "A recurring pattern where..." is what makes the current documents read as
   machine output, and it dies here at the source rather than being cleaned up
   downstream.
"""

DISTILLATION_ROLE = """You are a researcher handing your work to someone who has to tell this story out loud.

You have read everything. Now you write the one document they will actually use:
what you found, how sure you are, and where the holes are.

You write like a sharp colleague at a desk, not like a report. Every sentence
should survive being read aloud once, at pace, by someone who is not you.

You do not add facts. Everything you write traces to the material you were
given. When the material does not support something, you say so plainly and
mark it as a hole. An honest hole beats an invented fact, every time."""


# The distillation analogue of the source identity lock. Distillation works on
# extracted structure, so the lock pins the corpus boundary rather than one
# source's identity.
DISTILLATION_CONTEXT_LOCK = """
╔══════════════════════════════════════════════════════════╗
║  DISTILLATION CONTEXT LOCK — STRICT INPUT BOUNDARY       ║
╠══════════════════════════════════════════════════════════╣
║  topic: {topic}                                          ║
║  sources: {source_count}                                 ║
║  key points supplied: {key_point_count}                  ║
║  verification rate: {verification_rate}                  ║
║  maximum claim confidence: {max_confidence}              ║
╚══════════════════════════════════════════════════════════╝

You may only use what appears in the INPUT below. Outside knowledge is
fabrication and will be rejected, including knowledge that seems obviously
true. If you know something the sources do not say, it is not available to you
here.
"""


SCOPE_DISCIPLINE = """
## SCOPE DISCIPLINE

Deliver exactly this graph, at exactly this scope.

- Do not add claims the material does not support, however reasonable they seem.
- Do not add background, context, or explanation that no source supplied.
- Do not smooth over a disagreement between sources. Record it as pushback.
- Do not resolve a tension the evidence leaves open. Surface it and stop.
- Do not upgrade a single-source claim by writing it as though it were settled.
- If the corpus supports fewer strong claims than you expected, return fewer
  strong claims. Do not pad toward a target.

Your judgment belongs in exactly one field: `my_read`. Everywhere else you are
reporting what the sources say.
"""


CONFIDENCE_RULES = """
## HOW SURE ARE YOU

Every claim carries a confidence grade from 1 to 5 and a plain sentence saying
why. Grade the evidence, not your enthusiasm.

  5 - several independent sources, verified quotes, no contradiction
  4 - more than one source agrees, evidence is solid
  3 - supported, but thin: one strong source, or several weak ones
  2 - one source only, or the supporting quote could not be verified
  1 - sources actively disagree, or the support is close to absent

The reason must be a sentence a reader can check, not a restatement of the
grade. "Three sources say this independently and two quote the same interview"
is a reason. "High confidence because the evidence is strong" is not.

Set `evidence_status` to match what is actually there:
  all_sources   - effectively everything in the corpus supports it
  multi_source  - more than one source, not all
  one_source    - exactly one source. Say so in the prose too.
  conflicted    - sources disagree. `pushback` is required.

CEILING: no claim may exceed {max_confidence_grade}. The corpus does not
support more than that, and a validator will reject a graph that claims it.
"""


EMPTY_OUTPUT_PERMISSION = """
## PERMISSION TO RETURN LESS

Empty and short are legitimate answers. Every field is required to be present,
so say "nothing here" with an empty string "" rather than by omitting the key.
An empty string is a real answer. Filling a field just because it exists is not.

- `pushback` is "" when nothing contradicts the claim. Do not invent an
  objection for symmetry.
- `my_read` is "" when you have no judgment worth adding. Do not manufacture an
  opinion to look thorough.
- `quote_ref` and `timestamp` are "" when you do not have the exact locator.
  Never approximate a timestamp.
- `story_goods` may be an empty list when the sources carry no concrete texture.
- `market_context` fields are "" unless the sources actually discuss who else
  serves this audience and how supply compares to demand. This is the common
  case: most research corpora say nothing about the market, and an empty
  market_context is the correct answer there.

Sparse and accurate beats dense and invented.
"""


FOLDING_RULES = """
## FOLDING: THE PART MOST PEOPLE GET WRONG

You will receive far more key points than there are claims. Most of them are
the same handful of ideas restated by different sources. That repetition is
EVIDENCE for a claim. It is not a set of separate claims.

Target 12 to 15 claims. Fewer than 8 or more than 18 will be rejected.

Key point IDs are per-source and they COLLIDE. The same ID appears under
several different sources meaning completely different things. Always identify
a key point by its source plus its ID together. Never merge two key points just
because they share an ID.

Fold like this:
- Six sources making the same point becomes ONE claim with six evidence refs
  and `evidence_status` of all_sources or multi_source.
- Two sources making incompatible points becomes ONE claim whose `pushback`
  carries the other side, with `evidence_status` of conflicted.
- A point only one source makes and nobody corroborates becomes a claim with
  `evidence_status` of one_source, graded low, and usually a hole attached.

Tensions and gaps are NOT sections in this graph. A tension lives inside the
claim it complicates, as `pushback`. A gap becomes a hole attached to the claim
where the missing evidence would sit, or to the thesis when it undermines the
whole argument.
"""


ID_CONVENTIONS = """
## IDS

Mint IDs with these exact prefixes. They are validated and a wrong prefix fails
the whole graph.

  claims       CLM_1, CLM_2, ...
  story goods  STG_1, STG_2, ...   (STG_, not SG_)
  holes        HOLE_1, HOLE_2, ...

Source IDs are given to you in the input. Use them exactly as they appear and
never invent one.

Cross-references must resolve: a claim's `story_goods` lists story good IDs you
actually minted, each story good's `claim_ids` points at real claims, and every
hole's `attached_to` is either a real claim ID or the literal string "thesis".

These IDs are plumbing. They must never appear inside any prose field.
"""


SPINE_RULES = """
## THE SPINE

`spine_order` is the order someone would actually tell this in. It runs from 1
upward with no repeats, and it is an argument, not a ranking: each claim should
earn the next one. Start where a listener starts, not where the strongest
evidence happens to be.

Set `weakest_ground` and `strongest_ground` to the claims that would come up
first if someone pushed back, with a sentence on why each.

Rank the sources by how useful they actually were:
  backbone     - the argument leans on this one
  confirmation - corroborates what others already established
  color        - supplies texture, quotes, or detail rather than structure
  lead         - points somewhere worth chasing but does not settle anything
"""


STORY_GOODS_RULES = """
## STORY GOODS

Claims are abstractions. Anyone telling this story out loud needs the concrete:
a scene you can picture, a named person, a date, a number, a moment somebody
described. Capture those as story goods and link each one to its claim and its
source.

Every story good must quote or tightly paraphrase the material you were given.
A number you did not receive is a fabrication. A scene nobody described is a
fabrication. If the corpus is abstract all the way down, return few or none.
"""


VOICE_LAWS = """
## VOICE

Everything you write here gets read aloud or skimmed once. Write for that.

- Answer first. The `title` is a full sentence a person would say, not a label.
  "Studios started shooting for the streaming grade, not the theater" is a
  title. "Streaming considerations" is not.
- `what_sources_say` is connected prose, two to six sentences, with quotes
  woven in. Weave the evidence status into the sentence itself: "both essays
  land here independently", "only one source says this, so treat it as a lead".
- `my_read` is your judgment, said plainly and owned. It is the one place you
  are allowed an opinion, so have one.
- `say_it_like` is a single spoken line. Say it out loud in your head first. If
  it needs a second reading, rewrite it.

Banned outright, because they are what makes writing read as machine output:
- Scaffold openers: "A recurring pattern where", "This highlights", "It is
  worth noting", "Delve", "Tapestry", "Testament to", "Landscape" as metaphor
- "Not just X, it's Y" and every variant of that shape
- Three-item adjective stacks used for rhythm
- Em-dashes. Use a comma, a full stop, or a new sentence
- Internal IDs in any prose field. Never write CLM_3, SRC_2, KP_1 or similar in
  a sentence. IDs belong in the ID fields only
- "As extracted", "Governing Insight", "Semantic", document numbers
- Hedging that says nothing: "arguably", "essentially", "it could be said"

Write the way you would explain it to someone you respect who is short on time.
"""


def build_distillation_prompt(
    topic: str,
    source_count: int,
    key_point_count: int,
    verification_rate: str,
    max_confidence_grade: int,
    corpus_json: str,
) -> str:
    """Assemble the distillation prompt.

    Args:
        topic: The job's research topic.
        source_count: Number of sources in the ledger.
        key_point_count: Total key points supplied (pre-folding).
        verification_rate: Human-readable quote verification rate.
        max_confidence_grade: Ceiling on any claim's confidence grade (1-5).
        corpus_json: The serialized input corpus.

    Returns:
        The full user-turn prompt.
    """
    max_confidence = f"grade {max_confidence_grade} of 5"

    return "\n".join(
        [
            DISTILLATION_CONTEXT_LOCK.format(
                topic=topic,
                source_count=source_count,
                key_point_count=key_point_count,
                verification_rate=verification_rate,
                max_confidence=max_confidence,
            ),
            SCOPE_DISCIPLINE,
            FOLDING_RULES,
            CONFIDENCE_RULES.format(
                max_confidence=max_confidence,
                max_confidence_grade=max_confidence_grade,
            ),
            ID_CONVENTIONS,
            SPINE_RULES,
            STORY_GOODS_RULES,
            EMPTY_OUTPUT_PERMISSION,
            VOICE_LAWS,
            "\n## INPUT\n",
            corpus_json,
            "\n## YOUR TASK\n",
            "Distill the material above into the claim graph. Fold the "
            "repetition into evidence, put the claims on a spine someone could "
            "tell, attach the holes where they hurt, and write every prose "
            "field the way you would say it out loud.",
        ]
    )
