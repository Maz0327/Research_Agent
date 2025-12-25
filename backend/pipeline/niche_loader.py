"""Niche Overlay System loader and merger.

PRD v4.3: Config-driven query/source modifications for specialized research.

Niches modify:
- query_additions: Extra search queries
- source_floors: Override source type minimums
- synthesis: Additional synthesis options
- narrative_format: Output format style

Merge rules:
- query_additions: APPEND (niche queries added to mode queries)
- source_floors: OVERRIDE (niche floors replace mode floors)
- synthesis: MERGE (niche options added to mode options)
- narrative_format: OVERRIDE (niche format replaces mode format)
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Install with: pip install pyyaml")


# Default niche directory location
NICHE_CONFIG_DIR = Path(__file__).parent.parent / "config" / "niches"


class NicheConfig:
    """Parsed niche configuration."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize from parsed YAML data."""
        niche_data = data.get("niche", data)

        self.name: str = niche_data.get("name", "unknown")
        self.description: str = niche_data.get("description", "")
        self.query_additions: List[str] = niche_data.get("query_additions", [])
        self.source_floors: Dict[str, int] = niche_data.get("source_floors", {})
        self.synthesis: Dict[str, Any] = niche_data.get("synthesis", {})
        self.narrative_format: str = niche_data.get("narrative_format", "default")
        self.priority_keywords: List[str] = niche_data.get("priority_keywords", [])
        self.preferred_domains: List[str] = niche_data.get("preferred_domains", [])

    def get_queries(self, topic: str) -> List[str]:
        """
        Get expanded queries with topic substitution.

        Args:
            topic: Research topic to substitute

        Returns:
            List of queries with {topic} replaced
        """
        return [q.replace("{topic}", topic) for q in self.query_additions]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "query_additions": self.query_additions,
            "source_floors": self.source_floors,
            "synthesis": self.synthesis,
            "narrative_format": self.narrative_format,
            "priority_keywords": self.priority_keywords,
            "preferred_domains": self.preferred_domains,
        }


class ModeConfig:
    """Pipeline mode configuration."""

    def __init__(
        self,
        name: str,
        source_floors: Optional[Dict[str, int]] = None,
        max_slots: int = 25,
        synthesis: Optional[Dict[str, Any]] = None,
    ):
        """Initialize mode configuration."""
        self.name = name
        self.source_floors = source_floors or self._default_floors(name)
        self.max_slots = max_slots
        self.synthesis = synthesis or {}

    @staticmethod
    def _default_floors(mode: str) -> Dict[str, int]:
        """Get default source floors for a mode."""
        # PRD v4.3 source floors (CONSERVATIVE - increased limits)
        floors = {
            "quick": {"web": 3, "news": 1, "video": 1, "academic": 0, "discussion": 0},
            "breaking": {"web": 3, "news": 4, "video": 1, "academic": 0, "discussion": 1},
            "full": {"web": 4, "news": 3, "video": 3, "academic": 2, "discussion": 1},
            "investigation": {"web": 5, "news": 3, "video": 4, "academic": 3, "discussion": 3},
            "profile": {"web": 3, "news": 3, "video": 4, "academic": 1, "discussion": 1},
            "controversy": {"web": 3, "news": 3, "video": 3, "academic": 2, "discussion": 4},
        }
        return floors.get(mode, floors["full"])

    @staticmethod
    def _default_max_slots(mode: str) -> int:
        """Get default max slots for a mode."""
        slots = {
            "quick": 8,
            "breaking": 15,
            "full": 25,
            "investigation": 40,
            "profile": 25,
            "controversy": 25,
        }
        return slots.get(mode, 25)


class NicheRegistry:
    """Registry of available niches."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize registry from config directory."""
        self.config_dir = config_dir or NICHE_CONFIG_DIR
        self._niches: Dict[str, NicheConfig] = {}
        self._registry: Dict[str, Any] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure configs are loaded."""
        if not self._loaded:
            self._load_registry()
            self._loaded = True

    def _load_registry(self) -> None:
        """Load niche registry and configs."""
        if not YAML_AVAILABLE:
            logger.warning("YAML not available, niche system disabled")
            return

        registry_path = self.config_dir / "registry.yaml"
        if not registry_path.exists():
            logger.warning(f"Niche registry not found at {registry_path}")
            return

        try:
            with open(registry_path) as f:
                self._registry = yaml.safe_load(f) or {}

            # Load each enabled niche
            for niche_entry in self._registry.get("niches", []):
                if not niche_entry.get("enabled", True):
                    continue

                niche_name = niche_entry.get("name")
                config_file = niche_entry.get("config_file")

                if niche_name and config_file:
                    self._load_niche(niche_name, config_file)

            logger.info(f"Loaded {len(self._niches)} niches: {list(self._niches.keys())}")

        except Exception as e:
            logger.error(f"Failed to load niche registry: {e}")

    def _load_niche(self, name: str, config_file: str) -> None:
        """Load a single niche configuration."""
        config_path = self.config_dir / config_file

        if not config_path.exists():
            logger.warning(f"Niche config not found: {config_path}")
            return

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
                self._niches[name] = NicheConfig(data)
                logger.debug(f"Loaded niche: {name}")
        except Exception as e:
            logger.error(f"Failed to load niche {name}: {e}")

    def get(self, name: str) -> Optional[NicheConfig]:
        """Get a niche configuration by name."""
        self._ensure_loaded()
        return self._niches.get(name)

    def list_niches(self) -> List[Dict[str, str]]:
        """List available niches with descriptions."""
        self._ensure_loaded()
        return [
            {"name": name, "description": niche.description}
            for name, niche in self._niches.items()
        ]

    def is_valid(self, name: str) -> bool:
        """Check if a niche name is valid."""
        self._ensure_loaded()
        return name in self._niches

    @property
    def baseline_reserve_percent(self) -> int:
        """Get baseline reserve percentage for niche mode."""
        self._ensure_loaded()
        return self._registry.get("niche_settings", {}).get("baseline_reserve_percent", 25)


# Global registry instance
_registry: Optional[NicheRegistry] = None


def get_registry() -> NicheRegistry:
    """Get the global niche registry."""
    global _registry
    if _registry is None:
        _registry = NicheRegistry()
    return _registry


def get_niche(name: str) -> Optional[NicheConfig]:
    """
    Get a niche configuration by name.

    Args:
        name: Niche name (e.g., "downfalls", "mysteries")

    Returns:
        NicheConfig or None if not found
    """
    return get_registry().get(name)


def list_niches() -> List[Dict[str, str]]:
    """
    List all available niches.

    Returns:
        List of dicts with name and description
    """
    return get_registry().list_niches()


def is_valid_niche(name: str) -> bool:
    """
    Check if a niche name is valid.

    Args:
        name: Niche name to check

    Returns:
        True if valid niche
    """
    return get_registry().is_valid(name)


def merge_mode_and_niche(
    mode: str,
    niche: Optional[str] = None,
    mode_config: Optional[ModeConfig] = None,
) -> Dict[str, Any]:
    """
    Merge mode configuration with optional niche overlay.

    Merge rules per PRD v4.3:
    - query_additions: APPEND (niche queries added)
    - source_floors: OVERRIDE (niche floors replace mode floors)
    - synthesis: MERGE (niche options added to mode options)
    - narrative_format: OVERRIDE (niche format replaces mode format)

    Args:
        mode: Pipeline mode name
        niche: Optional niche name
        mode_config: Optional mode configuration override

    Returns:
        Merged configuration dict
    """
    # Start with mode config
    if mode_config is None:
        mode_config = ModeConfig(mode)

    result = {
        "mode": mode,
        "niche": niche,
        "source_floors": mode_config.source_floors.copy(),
        "max_slots": mode_config.max_slots,
        "synthesis": mode_config.synthesis.copy(),
        "narrative_format": "default",
        "query_additions": [],
        "priority_keywords": [],
        "preferred_domains": [],
        "baseline_reserve_percent": 0,
    }

    # If no niche, return mode config
    if not niche:
        return result

    # Get niche config
    niche_config = get_niche(niche)
    if not niche_config:
        logger.warning(f"Niche '{niche}' not found, using mode defaults")
        return result

    # APPEND: query_additions
    result["query_additions"] = niche_config.query_additions.copy()

    # OVERRIDE: source_floors
    if niche_config.source_floors:
        result["source_floors"] = niche_config.source_floors.copy()

    # MERGE: synthesis
    result["synthesis"].update(niche_config.synthesis)

    # OVERRIDE: narrative_format
    if niche_config.narrative_format:
        result["narrative_format"] = niche_config.narrative_format

    # Add niche-specific fields
    result["priority_keywords"] = niche_config.priority_keywords.copy()
    result["preferred_domains"] = niche_config.preferred_domains.copy()
    result["baseline_reserve_percent"] = get_registry().baseline_reserve_percent

    logger.info(f"Merged mode '{mode}' with niche '{niche}'")
    return result


def expand_queries(topic: str, niche: Optional[str] = None) -> List[str]:
    """
    Get expanded queries for a topic with niche additions.

    Args:
        topic: Research topic
        niche: Optional niche name

    Returns:
        List of expanded query strings
    """
    if not niche:
        return []

    niche_config = get_niche(niche)
    if not niche_config:
        return []

    return niche_config.get_queries(topic)


def get_source_floors(mode: str, niche: Optional[str] = None) -> Dict[str, int]:
    """
    Get source floors for a mode/niche combination.

    Args:
        mode: Pipeline mode
        niche: Optional niche overlay

    Returns:
        Dict of source type to floor count
    """
    merged = merge_mode_and_niche(mode, niche)
    return merged["source_floors"]


def get_synthesis_options(mode: str, niche: Optional[str] = None) -> Dict[str, Any]:
    """
    Get synthesis options for a mode/niche combination.

    Args:
        mode: Pipeline mode
        niche: Optional niche overlay

    Returns:
        Dict of synthesis options
    """
    merged = merge_mode_and_niche(mode, niche)
    return merged["synthesis"]
