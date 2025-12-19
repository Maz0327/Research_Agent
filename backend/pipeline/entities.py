"""Entity extraction from sources."""
import re
from collections import defaultdict, Counter
from typing import Dict, List, Set
from loguru import logger


# Note: spaCy is optional for better NER, but we'll use regex as fallback
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        logger.warning("spaCy model not found. Using regex fallback. Install with: python -m spacy download en_core_web_sm")
        nlp = None
except ImportError:
    logger.warning("spaCy not installed. Using regex fallback. Install with: pip install spacy")
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

        Steps:
        1. Use spaCy NER for initial extraction (if available)
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
        sources = transcripts + web_sources

        for source in sources:
            text = source.get('text', '') if isinstance(source, dict) else getattr(source, 'text', '')
            if text:
                all_texts.append(text)

        # Extract using spaCy if available
        if nlp:
            logger.info("Using spaCy for entity extraction")
            for text in all_texts:
                # Limit to 1M chars for performance
                doc = nlp(text[:1000000])

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
        else:
            logger.info("Using regex fallback for entity extraction")

        # Fallback/supplement: regex patterns
        person_patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last
            r'\b((?:Mr\.|Ms\.|Dr\.|Mrs\.) [A-Z][a-z]+)\b',  # Title Name
            r'\b([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)\b',  # First M. Last
        ]

        org_patterns = [
            r'\b([A-Z][A-Za-z]+ (?:Corporation|Corp\.|Inc\.|LLC|Ltd\.|Company|Co\.))\b',
            r'\b([A-Z][A-Za-z]+ [A-Z][A-Za-z]+)\b',  # Two capitalized words
        ]

        for text in all_texts:
            # Extract persons
            for pattern in person_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    name = match.group(0)
                    # Filter out common false positives
                    if name not in ["The New", "New York", "United States"]:
                        entities["people"].append({
                            "name": name,
                            "context": text[max(0, match.start()-50):match.end()+50]
                        })

            # Extract organizations
            for pattern in org_patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entities["organizations"].append({
                        "name": match.group(0),
                        "context": text[max(0, match.start()-50):match.end()+50]
                    })

        # Deduplicate and resolve aliases
        entities = self._resolve_aliases(entities)

        # Count mentions and rank by importance
        entities = self._rank_entities(entities)

        logger.info(f"Extracted {len(entities.get('people', []))} people, "
                    f"{len(entities.get('organizations', []))} organizations, "
                    f"{len(entities.get('locations', []))} locations")

        return entities

    def _resolve_aliases(self, entities: Dict) -> Dict:
        """Resolve name variations to canonical forms."""
        resolved = {}

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

            # Convert aliases set to list for JSON serialization
            for canonical_name in seen_names:
                seen_names[canonical_name]["aliases"] = list(seen_names[canonical_name]["aliases"])

            resolved[category] = list(seen_names.values())

        return resolved

    def _get_canonical_name(self, name: str, seen_names: Dict) -> str:
        """Get canonical form of a name."""
        name = name.strip()

        # Check if this is a substring of existing names or vice versa
        for canonical in seen_names:
            # Full match
            if name.lower() == canonical.lower():
                return canonical

            # Check if one is contained in the other
            if name.lower() in canonical.lower():
                # "Owens" vs "Candace Owens" -> keep longer
                if len(canonical) > len(name):
                    return canonical
            elif canonical.lower() in name.lower():
                if len(name) > len(canonical):
                    # Update to longer name and return
                    return name

        return name

    def _rank_entities(self, entities: Dict) -> Dict:
        """Rank entities by importance (mention count)."""
        for category in entities:
            entities[category].sort(key=lambda x: x.get("mentions", 0), reverse=True)
        return entities


def generate_entities_markdown(entities: Dict) -> str:
    """Generate markdown summary of entities."""
    lines = ["# Entities\n"]
    lines.append(f"*Extracted from all sources and ranked by mentions*\n")

    for category in ["people", "organizations", "locations"]:
        entity_list = entities.get(category, [])
        if entity_list:
            lines.append(f"## {category.title()}\n")
            for i, entity in enumerate(entity_list[:20], 1):  # Top 20
                mentions = entity.get("mentions", 0)
                name = entity.get("name", "Unknown")
                aliases = entity.get("aliases", [])

                lines.append(f"{i}. **{name}** ({mentions} mentions)")
                if len(aliases) > 1:
                    lines.append(f"   - *Aliases: {', '.join(aliases)}*")
                lines.append("")

    if not any(entities.get(cat) for cat in ["people", "organizations", "locations"]):
        lines.append("No entities extracted.\n")

    return "\n".join(lines)
