"""
Models package for LogiSight.
Re-exports all models from the original models.py and the new copilot_memory module.
"""

# Re-export everything from the original models.py (one level up)
from app.models_legacy import (
    Anomaly,
    Airport,
    Charge,
    ChargeAlias,
    Company,
    Country,
    Currency,
    Invoice,
    InvoiceCharge,
    Profile,
    Quote,
    QuoteCharge,
    TrackingEvent,
)

# Export new copilot memory models
from app.models.copilot_memory import (
    ChargeEmbedding,
    CopilotMemoryEvent,
    CopilotSession,
)

__all__ = [
    # Original models
    "Anomaly",
    "Airport",
    "Charge",
    "ChargeAlias",
    "Company",
    "Country",
    "Currency",
    "Invoice",
    "InvoiceCharge",
    "Profile",
    "Quote",
    "QuoteCharge",
    "TrackingEvent",
    # New copilot models
    "ChargeEmbedding",
    "CopilotMemoryEvent",
    "CopilotSession",
]
