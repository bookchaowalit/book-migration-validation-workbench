"""Deterministic reconciliation core for the migration validation prototype."""

from .fuzzy import (
    DEFAULT_FUZZY_CANDIDATE_LIMIT,
    DEFAULT_FUZZY_CANDIDATE_MINIMUM,
    DEFAULT_FUZZY_THRESHOLD,
    find_fuzzy_candidates,
    fuzzy_score,
)
from .normalization import (
    available_profiles,
    canonical_profile,
    normalize_value,
    profile_metadata,
)

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_FUZZY_CANDIDATE_LIMIT",
    "DEFAULT_FUZZY_CANDIDATE_MINIMUM",
    "DEFAULT_FUZZY_THRESHOLD",
    "available_profiles",
    "canonical_profile",
    "fuzzy_score",
    "find_fuzzy_candidates",
    "normalize_value",
    "profile_metadata",
]
