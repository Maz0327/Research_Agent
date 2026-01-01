"""Social Export: Social media content kit for multi-platform promotion.

Generates hooks, hashtags, captions, and thread outlines for
promoting research content across social platforms.
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any
from loguru import logger


# Platform-specific hashtag strategies
HASHTAG_LIMITS = {
    "tiktok": 5,
    "twitter": 3,
    "instagram": 10,
    "youtube": 5,
}

# Category-specific hashtag templates
CATEGORY_HASHTAGS = {
    "pop_culture": ["entertainment", "celebrity", "trending", "viral", "culture"],
    "political": ["politics", "news", "breaking", "government", "policy"],
    "true_crime": ["truecrime", "investigation", "justice", "crime", "documentary"],
    "mysteries": ["mystery", "unexplained", "theory", "conspiracy", "secrets"],
    "downfalls": ["scandal", "exposed", "drama", "downfall", "controversy"],
    "controversy": ["controversial", "debate", "exposed", "truth", "reveal"],
}

# Hook templates by style
HOOK_TEMPLATES = [
    "The {adjective} truth about {topic}...",
    "What they don't want you to know about {topic}",
    "Everything you thought you knew about {topic} is wrong",
    "{topic}: The story nobody is telling",
    "I spent {time} researching {topic}. Here's what I found.",
    "This changes everything we know about {topic}",
    "The {topic} story just got a lot more interesting",
]


@dataclass
class SocialContentKit:
    """Complete social media content kit."""

    topic: str
    hooks: list[str] = field(default_factory=list)
    hashtags_by_platform: dict = field(default_factory=dict)
    caption_templates: list[str] = field(default_factory=list)
    cta_suggestions: list[str] = field(default_factory=list)
    thread_outline: list[str] = field(default_factory=list)
    key_quotes: list[str] = field(default_factory=list)
    controversy_angles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "hooks": self.hooks,
            "hashtags_by_platform": self.hashtags_by_platform,
            "caption_templates": self.caption_templates,
            "cta_suggestions": self.cta_suggestions,
            "thread_outline": self.thread_outline,
            "key_quotes": self.key_quotes,
            "controversy_angles": self.controversy_angles,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class SocialExporter:
    """Generate social media content kit from research data."""

    def generate_kit(
        self,
        topic: str,
        claims: list,
        entities: dict,
        discovered_angles: list,
        category: str = "auto",
    ) -> SocialContentKit:
        """
        Generate social content kit from research data.

        Args:
            topic: Research topic
            claims: List of extracted claims
            entities: Dict of extracted entities
            discovered_angles: List of discovered unique angles
            category: Research category for hashtag optimization

        Returns:
            SocialContentKit with all content elements
        """
        logger.info(f"Generating social content kit for: {topic}")

        kit = SocialContentKit(topic=topic)

        # Generate hooks
        kit.hooks = self._generate_hooks(topic, claims, discovered_angles)

        # Generate platform-specific hashtags
        kit.hashtags_by_platform = self._generate_hashtags(topic, entities, category)

        # Generate caption templates
        kit.caption_templates = self._generate_captions(topic, claims)

        # Generate CTAs
        kit.cta_suggestions = self._generate_ctas(topic)

        # Generate thread outline
        kit.thread_outline = self._generate_thread(topic, claims, discovered_angles)

        # Extract key quotes
        kit.key_quotes = self._extract_quotes(claims)

        # Extract controversy angles
        kit.controversy_angles = self._extract_controversy(claims, discovered_angles)

        logger.info(f"Generated {len(kit.hooks)} hooks, {len(kit.thread_outline)} thread tweets")
        return kit

    def to_json(self, kit: SocialContentKit, indent: int = 2) -> str:
        """Export kit as JSON."""
        return kit.to_json(indent)

    def _generate_hooks(
        self,
        topic: str,
        claims: list,
        discovered_angles: list,
    ) -> list[str]:
        """Generate attention-grabbing hooks."""
        hooks = []

        # Template-based hooks
        adjectives = ["untold", "shocking", "hidden", "real", "full"]
        for template in HOOK_TEMPLATES[:4]:
            hook = template.format(
                topic=topic,
                adjective=adjectives[len(hooks) % len(adjectives)],
                time="100+ hours"
            )
            hooks.append(hook)

        # Claim-based hooks
        for claim in claims[:3]:
            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            if text and len(text) > 30:
                # Extract most impactful part
                hook = self._make_hook_from_claim(text)
                if hook and hook not in hooks:
                    hooks.append(hook)

        # Angle-based hooks
        angles_list = self._normalize_angles(discovered_angles)
        for angle in angles_list[:2]:
            name = self._get_attr(angle, "name") or self._get_attr(angle, "angle") or ""
            if name:
                hooks.append(f"New angle discovered: {name}")

        return hooks[:8]

    def _generate_hashtags(
        self,
        topic: str,
        entities: dict,
        category: str,
    ) -> dict:
        """Generate platform-specific hashtags."""
        hashtags = {platform: [] for platform in HASHTAG_LIMITS}

        # Base topic hashtag
        topic_tag = self._make_hashtag(topic)
        for platform in hashtags:
            hashtags[platform].append(topic_tag)

        # Category-specific hashtags
        if category in CATEGORY_HASHTAGS:
            category_tags = CATEGORY_HASHTAGS[category]
        else:
            category_tags = ["trending", "viral", "mustwatch"]

        for platform in hashtags:
            for tag in category_tags:
                if len(hashtags[platform]) < HASHTAG_LIMITS[platform]:
                    hashtags[platform].append(f"#{tag}")

        # Entity-based hashtags (people, organizations)
        people = entities.get("people") or entities.get("persons") or []
        for person in people[:3]:
            name = self._get_attr(person, "name") or str(person)
            tag = self._make_hashtag(name)
            for platform in hashtags:
                if len(hashtags[platform]) < HASHTAG_LIMITS[platform]:
                    hashtags[platform].append(tag)

        # Platform-specific additions
        hashtags["tiktok"].extend(["#fyp", "#foryou"][:HASHTAG_LIMITS["tiktok"] - len(hashtags["tiktok"])])
        hashtags["instagram"].extend(["#explore", "#reels"][:HASHTAG_LIMITS["instagram"] - len(hashtags["instagram"])])

        # Deduplicate per platform
        for platform in hashtags:
            hashtags[platform] = list(dict.fromkeys(hashtags[platform]))[:HASHTAG_LIMITS[platform]]

        return hashtags

    def _generate_captions(self, topic: str, claims: list) -> list[str]:
        """Generate caption templates."""
        captions = []

        # Short caption
        captions.append(f"The {topic} story you haven't heard. [Link in bio]")

        # Medium caption with hook
        if claims:
            text = self._get_attr(claims[0], "text") or ""
            if text:
                captions.append(f"{text[:100]}... Full breakdown: [Link]")

        # Long caption with context
        captions.append(
            f"I spent weeks researching {topic}. What I found changes everything. "
            f"Watch the full documentary breakdown to understand what's really going on. "
            f"[Link in bio]"
        )

        # Question-based caption
        captions.append(f"What do you think about {topic}? Drop your thoughts below 👇")

        # Controversy caption
        captions.append(
            f"This is the {topic} content they don't want you to see. "
            f"Save this before it's gone. Full video on my channel."
        )

        return captions

    def _generate_ctas(self, topic: str) -> list[str]:
        """Generate call-to-action suggestions."""
        return [
            "Follow for part 2",
            "Link in bio for the full breakdown",
            "Save this before it gets taken down",
            f"Comment your theory about {topic[:30]}",
            "Share with someone who needs to see this",
            "Turn on notifications for the full story",
            "Subscribe for more deep dives like this",
            "Drop a 🔥 if you want more content like this",
        ]

    def _generate_thread(
        self,
        topic: str,
        claims: list,
        discovered_angles: list,
    ) -> list[str]:
        """Generate Twitter/X thread outline."""
        thread = []

        # Hook tweet
        thread.append(f"🧵 THREAD: Everything you need to know about {topic}\n\nI researched this for weeks. Here's what I found:")

        # Context tweet
        thread.append(f"First, some context on {topic}:\n\n[Background information]")

        # Claim-based tweets
        for i, claim in enumerate(claims[:5], start=1):
            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            if text:
                truncated = text[:200] + "..." if len(text) > 200 else text
                thread.append(f"{i}/ {truncated}")

        # Angle-based tweets
        angles_list = self._normalize_angles(discovered_angles)
        for angle in angles_list[:2]:
            name = self._get_attr(angle, "name") or ""
            desc = self._get_attr(angle, "description") or ""
            if name:
                thread.append(f"📌 Key finding: {name}\n\n{desc[:150]}")

        # Conclusion tweet
        thread.append(f"That's the {topic} story.\n\nIf you found this valuable:\n- RT the first tweet\n- Follow for more threads like this\n\n[Link to full video/article]")

        return thread

    def _extract_quotes(self, claims: list) -> list[str]:
        """Extract quotable moments from claims."""
        quotes = []

        for claim in claims:
            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""

            # Find actual quotes in text
            quote_matches = re.findall(r'"([^"]{20,150})"', text)
            for match in quote_matches:
                if match not in quotes:
                    quotes.append(match)

            # Find attribution patterns
            attr_match = re.search(r'([A-Z][a-z]+\s[A-Z][a-z]+)\s+said\s+"([^"]+)"', text)
            if attr_match:
                quote = f'"{attr_match.group(2)}" - {attr_match.group(1)}'
                if quote not in quotes:
                    quotes.append(quote)

        return quotes[:10]

    def _extract_controversy(
        self,
        claims: list,
        discovered_angles: list,
    ) -> list[str]:
        """Extract controversy angles for maximum engagement."""
        controversies = []

        controversy_keywords = [
            "scandal", "controversy", "accused", "alleged", "disputed",
            "leaked", "exposed", "conflict", "opposition", "criticism"
        ]

        # From claims
        for claim in claims:
            text = self._get_attr(claim, "text") or ""
            text_lower = text.lower()

            for keyword in controversy_keywords:
                if keyword in text_lower:
                    controversies.append(text[:150])
                    break

        # From angles
        angles_list = self._normalize_angles(discovered_angles)
        for angle in angles_list:
            name = self._get_attr(angle, "name") or ""
            desc = self._get_attr(angle, "description") or ""
            combined = f"{name} {desc}".lower()

            for keyword in controversy_keywords:
                if keyword in combined:
                    controversies.append(f"{name}: {desc[:100]}")
                    break

        return list(set(controversies))[:5]

    def _make_hook_from_claim(self, claim_text: str) -> str:
        """Create hook from claim text."""
        # Find the most impactful sentence
        sentences = re.split(r'[.!?]+', claim_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence) < 150:
                return sentence + "..."

        # Fallback: truncate
        if len(claim_text) > 100:
            return claim_text[:100] + "..."
        return claim_text

    def _make_hashtag(self, text: str) -> str:
        """Convert text to hashtag."""
        # Remove special characters, keep alphanumeric
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        # CamelCase for multi-word
        words = clean.split()[:3]  # Max 3 words
        if len(words) > 1:
            tag = ''.join(w.capitalize() for w in words)
        else:
            tag = words[0] if words else "topic"
        return f"#{tag}"

    def _normalize_angles(self, discovered_angles: list) -> list:
        """Normalize angles to list of dicts."""
        if isinstance(discovered_angles, dict):
            return discovered_angles.get("angles") or discovered_angles.get("discovered") or []
        return discovered_angles or []

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
