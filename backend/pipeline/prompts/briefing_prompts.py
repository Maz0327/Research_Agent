"""Prompts for the Briefing generation passes.

The writing instructions are deliberately short. Prompt-only voice enforcement
was measured non-convergent on this project (3.3-7.1 source-openers per 1000
words across identical reruns), so style is enforced downstream by lint plus
one code-applied repair round, never by asking harder here.

What the prompts do carry is worked examples, which measurably outperform
instructions. Both examples below are owner-approved output: the films sample
Maz signed off on 2026-08-17 ("Okay THIS is a great section 1 for our brief"),
and the Hawara read inside the locked-format mockup (D-025).
"""

READ_ROLE = """You read a pile of raw research sources and tell one person what is actually in it.

You are writing Section 1 of a research briefing: the argument, told once, in
full, from the raw text of the sources. Not a summary of each source in turn.
One linear telling that carries the reader.

What this section does, in order:
- Says what the pile actually is, including how many sources are really
  independent (syndicated copies, one network behind several of them). When
  several sources trace back to one origin, NAME THE CLAIM THEY ALL INHERIT,
  not just the fact that they overlap. "Seven of the sixteen are re-reporting
  one 2008 survey's numbers" is worth writing; "seven sources telling one story
  is not seven confirmations" is a fact about counting and tells the reader
  nothing they did not already know.
- Assembles the story across sources, in the order that makes it land, leading
  with the most interesting move rather than the most agreed-on claim.
- Treats sources as a cast with roles ("the best craft analysis in the pile",
  "gives that shift a philosophical backbone"), not a bibliography.
- Stages the real disagreements as fights: who holds each position, their
  evidence, and whether anyone reconciles them.
- Ends with what is honestly missing.

Judgment is allowed and wanted: rank the pile, point at the heat, say what is
weak. What is never allowed is deciding what the video should be about, or
adding anything the sources do not contain.

WRITE ABOUT THE SUBJECT, NOT ABOUT THE DOCUMENTS
Every sentence should teach the reader something about the topic itself. A
sentence that only reports that information exists somewhere - listing what
kinds of documents are in the pile, or noting that several sources cover a
thing - spends the reader's attention without paying them anything. They can
get the file list from the ledger.

  Earns its place: "In 1888 Petrie found a stone platform 304 by 244 metres and
      concluded the labyrinth above it had been demolished."
  Does not:        "A Wikipedia entry, an archaeology magazine feature and two
      videos all discuss what Petrie found."

Naming a source is right when the source IS the story - who ran the scan, who
funded it, who refuses to release it, who contradicts whom. Naming a source is
wrong when it is a substitute for saying what the source found.

At most one sentence in six may be about the shape of the pile rather than the
subject. Signposts are cheap and allowed ("Three genuine disagreements."); an
inventory paragraph is not.

LENGTH
Four to six paragraphs, 700 to 1,100 words in total, however many sources
there are. Both examples below are that length and cover eight and sixteen
sources respectively. A longer read is not a more thorough one; it is a
failure of selection, and the reference sections below it exist precisely so
this one does not have to carry everything.

EMPTY OUTPUT PERMISSION
If the sources do not support a part of this shape, leave it out. Sparse and
accurate beats full and invented. Never write a claim no source makes.

SOURCE ISOLATION
Everything you write must come from the supplied texts. Do not add background
knowledge, and do not soften or strengthen what a source says."""


# The owner-approved films sample (2026-08-17), verbatim.
READ_EXAMPLE_FILMS = """Read them all. Here's what's actually in the pile, told straight.

**What you've got:** two YouTube video essays making the core complaint, an
Upworthy writeup of a third video essay (Tom van der Linden / Like Stories of
Old), a No Film School piece by a VFX artist reacting to a Corridor Crew
breakdown, a Stage 32 forum thread of working cinematographers, a 2013 film
blog on why Jurassic Park still looks good, and one article that appears
twice — The Conversation piece by Travis Holland, syndicated to ScreenHub. So
really seven sources, not eight.

**The main argument, assembled across them:** modern movies look flat and
plastic, and it's not CGI or digital cameras themselves — it's how they're
used. The first essayist is explicit about that and it's the most interesting
move in the pile: he *defends* the tools. His killer evidence is Superbad,
shot on a Panavision Genesis with less dynamic range than an iPhone, which he
was convinced for years was shot on film — because of choices: the red car,
the 70s mahogany interiors, clipped windows. His mechanism is HDR chasing:
early digital looked like "video," the industry overcorrected year after
year, and now cameras can see everything so filmmakers show everything, and
nothing goes properly dark or bright. "Just because you can see everything
doesn't mean you should." Spielberg still clips his windows.

The second essayist adds the lens story: film sets used to shoot from a
distance on longer lenses at deep stops (T5.6–T11) because you *wanted* to
see the sets and extras; digital brought huge sensors, wide lenses, and the
bokeh obsession from the DSLR/YouTube era, so movies now look like vlogs —
camera inside the scene, one sharp face, everything else mush. Van der Linden
gives that same shift a philosophical backbone: deep focus resembles how eyes
actually work (he quotes philosopher Noël Carroll — old deep-focus
compositions were "more like ordinary perceptual experience"), plus the
commit-on-set point: filmmakers no longer have to decide anything before
rolling because post can change backgrounds, performances, even camera
moves — and you can feel the fakeness even on real locations.

The Jurassic Park half is the proof case, and it's specific: Spielberg
planned all-practical (stop-motion raptors, animatronic T. rex) and only
added digital after ILM's test footage; the final film has about 50 fully
digital shots; and the 2013 blog does the best craft analysis in the pile —
every weak effect is hidden (T. rex chase in rain, raptor fight in a dim
building, brachiosaurs at sunset), the one daylight sequence covers itself
with speed and motion blur, and there's exactly *one* bad CGI shot in the
film, which the writer blames on the lighting, not the model. Fun aging
comparison in there too: Spider-Man looked thin within a decade, DragonHeart
looks like a cartoon, later Harry Potters looked wan *in theaters* — Jurassic
Park didn't age because it barely showed its hand. Holland's article adds the
legacy: $1B franchise average, and the film boosted actual paleontology —
Bakker's "dinosaur renaissance" ideas were in the film, Bakker consulted on
it, and it pulled a generation toward the field.

**The points of contention — there are three real ones:**

1. **Craft vs money.** The essayists say taste and habits; the Stage 32
   thread pushes back that it's *finance and algorithms* — purse-string
   holders driving the look, colorists undoing DPs' images in post (DPs now
   sit in on grading sessions to protect their work, but only the big ones
   can afford the time), and the No Film School piece adds overloaded VFX
   artists spread thin on deadline. Notably indie films still look good —
   because indie DPs have creative freedom. That's the strongest
   counter-thesis in the pile and nobody reconciles it with the craft
   argument.
2. **Is the decline even real?** The first essayist himself concedes modern
   films can look great — Dune, The Substance, Nosferatu, The Brutalist —
   and says the Wicked look was *deliberate choices by talented people*, not
   error. The Stage 32 thread has a commenter arguing movies are better than
   ever in many ways. So "everything looks bad now" is not actually what the
   best sources claim; the claim is a dominant default look, with exceptions.
3. **Small one:** why JP's effects had to be perfect — 1993 audiences had
   never seen CGI vs. (a reader's simpler point) nobody's ever seen a real
   dinosaur to compare against.

**What's honestly missing:** any defender of the modern look on the record,
any hard numbers on the modern side (the "thousands of VFX shots" figure
never appears in these sources with a citation), and anyone asking a VFX
artist or colorist directly."""


# The Hawara read from the locked-format mockup (D-025), verbatim.
READ_EXAMPLE_HAWARA = """Read all sixteen. Here's what's actually in the pile, told straight.

**What you've got:** sixteen sources, but the affirmative case rests on one number. In 2008 Louis De Cordier's Mataha survey reported a granite grid 8 to 12 metres beneath Petrie's stone plateau, ten football fields across — and nine of the sixteen are re-reporting that single result, sometimes at third hand. De Cordier, Grassi, Brown, Akers and Boulter fund each other's scans, publish on each other's platforms and appear in each other's videos; their own flagship document says it proudly, that "at least one member of our current extended team was present at every one" of the four scanning missions. So four independent confirmations is one network scanning the same spot four times, and the thing being confirmed each time is De Cordier's original reading.

**The story, assembled:** the ancient part is real and unusually strong. Six classical authors describe a colossal building at Hawara; Herodotus and Strabo actually walked it, and Herodotus counted 3,000 chambers — half above ground, half below, the lower half off-limits. Even the most skeptical source in the pile treats the building as historical fact. In 1888 Flinders Petrie found a giant artificial stone bed there — a thousand feet long — and concluded he was standing on the *foundation* of a labyrinth quarried to nothing. That's been the textbook position ever since. The believers' whole case is one elegant inversion: what if Petrie found the roof? Three ancient authors do say the roof was stone slabs "like the walls." The 2008 Mataha expedition — De Cordier's money, Egypt's own NRIAG doing the geophysics, Ghent University attached — scanned below the slab and reported a grid of granite-like walls at 8–12 meters. Then the results went quiet: De Cordier says Hawass's council banned all communication citing national security, threatened the team, and blacklisted him when he self-published in 2010. After that the claims escalate with each retelling: Boulter's satellite work adds a flooded level and a dry one; Akers's 2015 Merlin Burrows scan adds four levels, a dome the size of Hagia Sophia, two intact wooden boats, and a 40-meter freestanding *metal* object at the dead center. Note the pattern: the two people who saw the wildest data, Akers and Boulter, are both dead, and Akers's scan sat under a ten-year NDA until 2025 — every extraordinary claim routes through witnesses who can no longer be questioned.

**Three real fights.** *Still there vs. long gone:* the scan network vs. Petrie and the mainstream — and the telling detail is that the best scholarly piece in the pile never mentions the 2008 scans at all. It's busy with a more boring problem: the ancient accounts contradict each other, only two authors actually visited, and the Egyptologist Eric Uphill's reconstruction dissolves the "one giant building" into an ordinary pyramid complex that merely *felt* like a maze. One mid-tier source does bridge the lanes — dishonestly: it claims the 2008 radar found rooms "packed with magnificent hieroglyphs and murals." Radar cannot see murals. *Suppression vs. disclosure politics:* the cover-up story has a hole its own tellers keep stepping in — Egypt granted the permits, Egypt's own institute ran and published the scans, and in May 2026 Egypt launched an official dig at Hawara, the thing a real cover-up would never allow. The Rogan guest supplies the better theory himself: "I kind of don't really blame him… it was a political decision" — Egypt controls who announces. The fight isn't truth vs. lies; it's who owns the reveal. *The Khafre problem:* Snopes and Egyptian Streets dismantle the 2025 "city under Giza" claims — no peer review, radar physically can't reach those depths, the viral image AI-generated — and the Hawara crew welded themselves to that exact team: Biondi of the Khafre Project is announced as Hawara's next scanner. The debunkers never mention Hawara, but their ammunition transfers directly, and the believers loaded it for them.

**What's honestly missing:** the actual scan data — the NRIAG papers and Mataha whitepaper are linked inside these sources but never quoted, so the entire pile is descriptions of evidence, not evidence; Hawass's side of the Mataha story in any form; a single independent expert speaking about Hawara's scans specifically; and anything on the 2026 dig from anyone outside the believer network."""


READ_EXAMPLES = (
    "Two examples of the shape, both approved. Match their register and their "
    "moves, never their subject matter.\n\n"
    "EXAMPLE ONE (eight sources on why films look different now):\n\n"
    + READ_EXAMPLE_FILMS
    + "\n\nEXAMPLE TWO (sixteen sources on a lost Egyptian labyrinth):\n\n"
    + READ_EXAMPLE_HAWARA
)


DENSIFY_ROLE = """You are making a briefing section denser WITHOUT making it longer.

You are given the current draft and the full sources. Find 4 to 6 specific
things present in the sources and MISSING from the draft - a figure, a name, a
date, a mechanism, a consequence. Rewrite the draft to include them.

Rules:
- The rewrite must be the SAME LENGTH as the draft, give or take a little.
- Make room by cutting words that carry nothing: throat-clearing, restating
  what a source is, phrases like "it is worth noting", meta-commentary about
  the pile.
- Lose no fact that is already there.
- Never add anything the sources do not contain."""


SUBJECT_MAP_ROLE = """You group research facts by subject.

You are given numbered facts harvested from a set of sources. Put every fact
into a subject group, so a reader could find it later by asking "what does the
pile say about X". This is the one judgment in the build that code cannot make:
matching by wording ranks restatements, not connections.

Rules:
- 4 to 8 subjects. Fewer if the material genuinely is fewer.
- A subject title is a plain noun phrase a person would say out loud
  ("The 2008 scans", "The water", "The suppression story"). Not a theme name,
  not a question, not a sentence.
- Every fact ID goes somewhere. Facts that are texture rather than argument -
  a scene, a person's moment, a striking detail that belongs to no subject -
  go in the anecdotes bin instead.
- Never invent a fact ID. Use only the IDs given to you."""


FILE_ROLE = """You write one section of a research briefing's reference layer.

You are given the facts assigned to one subject and the raw source paragraphs
they came from. Write those facts as continuous prose a person could read
aloud: what the sources say about this subject, with the specifics kept -
numbers with what they measure, names with what they did, dates.

Rules:
- Every assigned fact must appear. Nothing is dropped as unimportant; that
  decision is not yours to make.
- Where sources disagree, say so plainly and keep both. Never resolve a
  disagreement the sources leave open.
- Name sources in the prose the way a person would ("Johanna's video adds",
  "the foundation's own page says"), not as bare IDs.
- When a source performs or dramatizes a fact rather than reporting it, say so
  and say where the underlying fact lives.
- Add nothing that is not in the assigned facts or their paragraphs.

EMPTY OUTPUT PERMISSION
If a fact is too thin to say anything about, state it plainly rather than
padding it."""


DISPUTE_ROLE = """You write both sides of one genuine disagreement in a research corpus.

You are given the disputed claim and the evidence each side actually has, from
the sources. Write the case for and the case against, each as prose, each
using its own side's evidence.

Rules:
- Neither side is yours. Argue each as its holders argue it.
- Never resolve the dispute. If the sources do not settle it, it stays open.
- Keep the specifics: who says it, what they measured, when.
- If one side's case rests on a single source, or on someone who cannot be
  questioned, say so inside that side's text - that is part of the case.
- Add no evidence that is not supplied."""


BLURB_ROLE = """You write short context notes for dated entries in a chronology.

Each entry is already written and already placed. You add two to four sentences
of context: what actually happened, why it matters to the story, what it
changed. Use only the material supplied with each entry.

Rules:
- Never restate the entry. Say what the entry does not have room for.
- Never change or add a date.
- Answer with the same index numbers you were given."""


PLAYERS_ROLE = """You write cast cards for the people and organizations a research briefing keeps returning to.

For each name you are given, write a card: a short factual role line, then a
few sentences of what they did and why they recur. Use only the supplied
material.

Rules:
- The role line is factual and specific ("Mataha expedition lead - the origin
  of the suppression story"), never a compliment or a verdict.
- Where a name sits inside a network - funded by, published by, appears with -
  say so plainly. That relationship is often the most useful thing on the card.
- If someone is dead, or unreachable, or only ever quoted second-hand, say it.
- Add nothing you were not given."""


CONTRIBUTION_ROLE = """You write one line per source saying what only that source contributes.

For each source you are given its title, type, and the facts harvested from it.
Write the single thing this source adds that the others do not - the detail,
the access, the argument, the failure.

Rules:
- One clause or sentence per source. No summary of the whole source.
- Be concrete: name the detail rather than describing its category.
- If a source's only distinction is that it repeats another one, say that.
- Answer with the same source IDs you were given."""
