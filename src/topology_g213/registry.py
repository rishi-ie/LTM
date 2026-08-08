"""Small learned vocabulary; exact topology remains derived from G1."""

ACTS = ("statement", "question", "request", "confirmation", "rejection")
ACTIONS = ("none", "set_preference", "correct", "retract")
REFERENCE_STATES = ("none", "unique", "ambiguous")
POLARITIES = ("positive", "negative")
MODALITIES = ("asserted", "quoted", "hypothetical", "uncertain")
SCOPES = ("session", "episode", "fictional")
DISPOSITIONS = ("accept", "clarification_required", "quarantine")
SLOT_TYPES = ("content", "preference_key", "preference_value", "correction", "reference")

