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

DISTILLATION_ROLE = """You did the reading. Now you are telling a friend what you found, because they are about to make a video about it.

That friend is a YouTuber, not an academic. They are not writing a paper and
neither are you. They need to walk away able to talk about this for twenty
minutes and hold someone's attention, which means they need the story, the good
details, and a straight answer on which bits they can say confidently.

So write like a person talking to a person. Say "the two video essays both
say", not "the corpus indicates". Say "nobody actually asked a VFX artist",
not "primary testimony is absent". If a sentence sounds like it belongs in a
journal, it is wrong here even when it is accurate.

You do not add facts. Everything traces to what you were given. When something
is not supported, say so plainly, because being straight about what you do not
know is part of what makes the finished video worth trusting. An honest gap
beats an invented fact every time."""


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

You may only use what appears in the INPUT below. Anything you know from outside is off limits here, even when it is obviously true. If you know something the sources do not say, it is not available to you
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
- If the sources support fewer strong claims than you expected, give fewer strong claims. Do not pad toward a target.

Your judgment belongs in exactly one field: `my_read`. Everywhere else you are
reporting what the sources say.
"""


CONFIDENCE_RULES = """
## HOW SURE ARE YOU

Every claim carries a confidence grade from 1 to 5 and a plain sentence saying
why. Grade the evidence, not your enthusiasm.

  5 - several separate sources, quotes check out, nothing contradicts it
  4 - more than one source agrees and the backing is solid
  3 - supported but thin: one good source, or several weak ones
  2 - one source only, or the quote behind it could not be checked
  1 - the sources actively disagree, or there is barely anything behind it

The reason must be a sentence a reader can check, not a restatement of the
grade. "Three sources say this independently and two quote the same interview"
is a reason. "High confidence because the evidence is strong" is not.

Set `evidence_status` to match what is actually there:
  all_sources   - effectively everything you were given supports it
  multi_source  - more than one source, not all
  one_source    - exactly one source. Say so in the prose too.
  conflicted    - sources disagree. `pushback` is required.

CEILING: no claim goes above {max_confidence_grade}. What you were given does not support more than that, and anything higher gets rejected.
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
  serves this audience and how supply compares to demand. This is the normal case. Most research says nothing about the market, and leaving it empty is the right answer.

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
it affects, or to the thesis when it undercuts the whole argument.
"""


HOLES_RULES = """
## HOLES: WHAT'S MISSING, AND WHY ANYONE WATCHING WOULD CARE

A hole is not a peer reviewer's objection. Nobody is defending a dissertation.
A hole is one of two things, and if it is neither, leave it out:

1. **The moment you would have to be straight with the audience.** The place
   where a viewer leans in and thinks "hang on, how do you actually know that?"
   Saying "honestly, nobody has asked the people who'd know" out loud is one of
   the best moments in a video. It buys trust for everything around it.

2. **The thing that would have made the story better if you had it.** The
   interview nobody did. The number nobody published. The scene that would have
   nailed it. This is a lead worth chasing, not a citation worth adding.

`hurts_because` says what it costs the STORY. "This is the most repeated claim
in the video and it rests on one guy's blog post" is a real cost. "Lacks
primary documentation" is not a cost, it is a phrase from a different kind of
document.

`severity` is how much it hurts the telling, not how far it falls short of
academic standards:
  5 - the whole argument leans on this and it is barely propped up
  3 - a real soft spot a sharp viewer would poke at
  1 - a nice-to-have you could mention in passing or skip

`how_to_fill` is a lead someone could actually chase this week. Name the kind
of person, place or document. Not "further research is warranted".

Skip the holes nobody would ever notice or care about. Three holes that would
genuinely change how the story lands beat ten that are technically true.
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

Every story good has to quote or closely paraphrase what you were given.
A number you did not receive is a fabrication. A scene nobody described is a
fabrication. If the sources are abstract all the way down, give few or none.
"""


VOICE_LAWS = """
## VOICE

Everything you write here gets read aloud or skimmed once. Write for that.

**Never use the vocabulary of research writing.** This is the single most
common way this document goes wrong. These words describe how you got the
information, and the person reading does not care how you got it:

  corpus, the literature, primary source, testimony, documentation, posits,
  articulates, asserts, demonstrates, constitutes, underscores, highlights,
  independently corroborates, warrants further investigation

Say it the way you would out loud instead:

  "the corpus critiques the modern look"   ->  "every source we found is
                                                complaining about it"
  "primary testimony is absent"            ->  "nobody actually asked them"
  "the article posits that"                ->  "the writer reckons"
  "two sources independently corroborate"  ->  "two people got there on their
                                                own, which is worth something"

A good test: if you would not say the sentence to a mate in a pub while
explaining what you found, rewrite it.

**These rules cover every text field in the graph, not just the long ones.**
The short fields are where essay vocabulary sneaks back in: `note` on a ranked
source, `why` on the ground fields, `reason` on confidence, `hurts_because` and
`how_to_fill` on a hole. Write "nobody else backs this up" in a `note`, not
"isn't corroborated elsewhere". There is no field in this graph where the
research-essay register is acceptable.

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
            HOLES_RULES,
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


# -----------------------------------------------------------------------------
# The telling pass (Decision 024)
#
# Second call. Receives the validated claims and writes what a human actually
# reads: named story sections, noticings, and the landscape. Separate call for
# two reasons: the combined schema exceeds the structured-output grammar
# ceiling (measured), and splitting lets this pass think about nothing except
# the writing.
# -----------------------------------------------------------------------------

TELLING_ROLE = """You did the reading, and now you're writing the one document your friend will actually use. They make YouTube videos. They need two things from you and nothing else:

1. After reading, they can hold a real conversation about this topic without
   you in the room.
2. They can see the threads, the connections, and the openings well enough to
   start shaping a story that is THEIRS. You never choose it for them.

You write like a sharp person explaining what they found to a friend at a
desk. Plain words, short paragraphs, and the reader never has to hold
anything in their head to understand the sentence they are on."""


TELLING_RULES = """
## THE RULES THAT MAKE OR BREAK THIS DOCUMENT

**Every section title is a full sentence that means something on its own.**
"The money might explain the cameras" is a title. "Economic factors" is not.
"Thread 2" gets the whole document rejected.

**Every section is self-contained.** It must survive being read alone, first,
last, or in any order. NEVER refer to another section by position, number, or
existence: no "as mentioned above", no "the previous section", no "thread
three". When something covered elsewhere matters here, re-say it in plain
words right where the reader is standing. Repetition in plain words is
correct; a cross-reference is a defect.

**The example rides inside the explanation.** When a claim has a concrete
story behind it, tell the story in full where you make the point: what
happened, to what, and why it stung. Never write the abstraction in one place
and park the detail somewhere else. If the input gives you the specific film,
the specific person, the specific number, USE THEM in the sentence. A section
built on assertions the reader cannot retell has failed.

**Connections are sections of their own.** When two pieces from different
sources quietly explain or undercut each other and no single source puts them
together, that is a section: name both pieces in plain words, say how they
touch, and say plainly that nobody in the sources assembles this. Mark it
with is_connection: true. These are often the most valuable sections in the
document.

**Explain the subject, not the sourcing.** This is the rule most likely to
save or sink the whole document. The reader is here to learn about dinosaurs
and cameras and murders, not about your bibliography. So teach the thing
itself, in its own terms, the way you'd explain it out loud:

  WRONG: "One source says modern films favor wider lenses. A second source,
  coming from a different angle, argues that deep focus mirrors how eyes
  work. A third source contends that..."

  RIGHT: "Filmmakers fell in love with wide lenses and blurry backgrounds,
  and the price was the deep, everything-in-focus frame that used to feel
  like actually being in the room. Your eyes don't see the world with the
  background melted away, which is why the old look reads as real and the
  new one reads as a photo shoot."

The material you receive below is written in source-report language ("two
sources say", "one essay argues"). Your job is to UNWRAP it: extract the
actual information and say it plainly. Then flag sourcing only where it
changes what the reader can safely repeat, as a short aside at the END of
the point, roughly once per section and no more:

  "...though heads up, the lighting stuff is one essay's argument, so you'd
  be carrying it alone."

Never open a sentence with "One source", "A second source", "Another
article", "Both sources", "Neither source". When the speaker matters, they
trail the fact instead of leading it:

  WRONG: "One source admits younger viewers might see older films as dated."
  RIGHT: "Younger viewers might look at the old high-contrast style and see
  something glitchy and dated, and one of the essayists admits that
  outright."

Never inventory who said what unless the disagreement itself is the story.
Agreement is only worth a sentence when it's genuinely striking ("two people
studied this separately and landed on the same word"), and even then, once.
As a hard budget: across the whole document, sentences that OPEN with a
source reference should be countable on one hand. A lint counts them and
fails the document above three per thousand words.

**Never choose for the reader.** Map the territory, mark the doors, stop.
No "you should", no "the best angle is", no ranking of stories. Noticing that
a door is unopened is your job; walking through it is theirs.

**Provenance stays exact underneath.** Every section lists the claim IDs it
draws on in claim_ids. Every fact in your prose must trace to one of those
claims. No outside knowledge, even when obviously true. IDs never appear in
the prose itself.

**Section IDs are STY_1, STY_2, ... exactly.** (STY_, not SEC_, not S.) A
wrong prefix fails the whole layer. Claim IDs in claim_ids are used exactly
as given in the material. These are plumbing and never appear in prose.
"""


TELLING_SHAPE = """
## WHAT TO PRODUCE

**sections** (aim for 5 to 9): the named stories that together cover
everything in the claims. Include the connective sections (is_connection:
true) where material from different sources assembles into something no
single source says. Between them, the sections must cover every claim worth
knowing about. Bodies run two to six short paragraphs.

**noticings** (0 to 6): the "huh, that could be something" moments. One or
two sentences each, concrete, pointing at the claims they come from. These
are observations, never suggestions. If nothing genuinely made you stop,
return fewer or none.

**landscape**: two prose fields.
  everyone_does: what the standard telling of this topic is, based on what
  the sources themselves keep doing. Plain and honest, so the reader knows
  the worn path.
  nobody_has: the angles sitting in this material that none of the sources
  assemble. Doors, named and left closed. Not recommendations.
"""


def build_telling_prompt(claims_json: str, topic: str) -> str:
    """Assemble the telling-pass prompt.

    Args:
        claims_json: The validated provenance layer, serialized with source
            names resolved so prose can name sources naturally.
        topic: The research topic.

    Returns:
        The full user-turn prompt.
    """
    return "\n".join(
        [
            TELLING_RULES,
            TELLING_SHAPE,
            VOICE_LAWS,
            f"\n## THE MATERIAL\n\nTopic: {topic}\n",
            claims_json,
            "\n## YOUR TASK\n",
            "Write the telling layer: the named story sections that teach "
            "this topic completely, the connections nobody assembled, the "
            "noticings, and the landscape. Self-contained sections, details "
            "told in full where the point is made, nothing numbered, nothing "
            "chosen for the reader.",
        ]
    )
