"""
AI Decision Engine — optional recovery layer for Maestro mobile automation.

Activated only on Maestro step failure/timeout. Does not modify existing flows.
Enable via ATP_AI_RECOVERY=1 or --ai-recovery on the integration wrapper.
"""

from ai.ai_decision_engine import AIDecisionEngine, RecoveryOutcome
from ai.config_loader import load_engine_config

__all__ = ["AIDecisionEngine", "RecoveryOutcome", "load_engine_config"]
__version__ = "1.0.0"
