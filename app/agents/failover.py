"""
Model Failover Chain for the Astromech AI Agent Orchestrator.

Provides automatic failover across configured LLM providers when a model
becomes unavailable, rate-limited, or otherwise fails. The chain is built
dynamically from the active models in ``data/models.json`` and supports
resetting, advancing, and full audit logging of every attempt.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.language_models import BaseChatModel

from app.core.llm import get_llm as _get_llm
from app.core.models_config import LLMSystemConfig, ModelConfig, load_models_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FailoverAttempt:
    """Record of a single failover event."""

    provider: str
    model: str
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


# Provider ordering weights – lower means *later* in the failover chain.
# Ollama / local providers are kept as an absolute last resort.
_LAST_RESORT_PROVIDERS: set[str] = {"ollama"}


# ---------------------------------------------------------------------------
# FailoverChain
# ---------------------------------------------------------------------------

class FailoverChain:
    """Ordered failover chain across configured LLM models.

    The chain is constructed once from the active model configuration and
    supports advancing through alternatives when the current model fails.

    Parameters
    ----------
    preferred_provider : str | None
        Provider name for the initially-requested model.  If supplied (and
        active in the config) it will be placed first in the chain.
    preferred_model : str | None
        Model-id for the initially-requested model.
    """

    def __init__(
        self,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> None:
        self._chain: list[tuple[str, str]] = []
        self._index: int = 0
        self._failed_indices: set[int] = set()
        self._attempts: list[FailoverAttempt] = []

        self._build_chain(preferred_provider, preferred_model)
        logger.info(
            "FailoverChain initialised with %d model(s): %s",
            len(self._chain),
            [f"{p}/{m}" for p, m in self._chain],
        )

    # ------------------------------------------------------------------
    # Chain construction
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        preferred_provider: Optional[str],
        preferred_model: Optional[str],
    ) -> None:
        """Build the ordered failover chain from the models config.

        Ordering priority:
        1. The explicitly requested model (if active).
        2. The "default" alias from config.
        3. The "smart" alias from config.
        4. Any remaining active models (excluding last-resort providers).
        5. Last-resort / local models (e.g. Ollama).
        """
        config = load_models_config()
        active_models: list[ModelConfig] = [
            m for m in config.active_models if m.is_active
        ]

        # If runtime config leaves only one active model, seed additional
        # candidates from default model presets for enabled providers so
        # failover can still recover from single-model outages/timeouts.
        if len(active_models) < 2:
            seeded: list[ModelConfig] = []
            present = {(m.provider, m.model_id) for m in active_models}
            for m in LLMSystemConfig.default().active_models:
                provider_cfg = config.providers.get(m.provider)
                if provider_cfg and provider_cfg.enabled and (m.provider, m.model_id) not in present:
                    seeded.append(m)
                    present.add((m.provider, m.model_id))
            if seeded:
                logger.info(
                    "FailoverChain: seeded %d fallback model(s) from defaults due to low active model count.",
                    len(seeded),
                )
                active_models.extend(seeded)

        seen: set[tuple[str, str]] = set()

        def _add(provider: str, model_id: str) -> None:
            key = (provider, model_id)
            if key not in seen:
                seen.add(key)
                self._chain.append(key)

        # 1. Explicitly requested model
        if preferred_provider and preferred_model:
            # Verify it exists and is active
            for m in active_models:
                if m.provider == preferred_provider and m.model_id == preferred_model:
                    _add(m.provider, m.model_id)
                    break

        # 2. Default alias
        default_model = config.get_model("default")
        if default_model and default_model.is_active:
            _add(default_model.provider, default_model.model_id)

        # 3. Smart alias
        smart_model = config.get_model("smart")
        if smart_model and smart_model.is_active:
            _add(smart_model.provider, smart_model.model_id)

        # 4. Other active models (non-last-resort first)
        regular: list[ModelConfig] = []
        last_resort: list[ModelConfig] = []
        for m in active_models:
            if m.provider in _LAST_RESORT_PROVIDERS:
                last_resort.append(m)
            else:
                regular.append(m)

        for m in regular:
            _add(m.provider, m.model_id)

        # 5. Last-resort / local models
        for m in last_resort:
            _add(m.provider, m.model_id)

        if not self._chain:
            logger.warning(
                "FailoverChain: no active models found – "
                "falling back to hardcoded Ollama default."
            )
            self._chain.append(("ollama", "llama3"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current(self) -> tuple[str, str]:
        """Return ``(provider, model_id)`` for the current chain position."""
        if self.is_exhausted():
            raise RuntimeError(
                "FailoverChain exhausted – all models have been tried."
            )
        return self._chain[self._index]

    def advance(self, reason: str = "") -> bool:
        """Mark the current model as failed and move to the next one.

        Parameters
        ----------
        reason : str
            Human-readable explanation of the failure (logged for audit).

        Returns
        -------
        bool
            ``True`` if a new model is available; ``False`` if the chain
            is now exhausted.
        """
        provider, model = self._chain[self._index]
        self._failed_indices.add(self._index)
        self._attempts.append(
            FailoverAttempt(provider=provider, model=model, reason=reason)
        )
        logger.warning(
            "FailoverChain: model %s/%s failed (%s) – advancing.",
            provider,
            model,
            reason or "no reason given",
        )

        # Find the next un-failed index
        next_idx = self._index + 1
        while next_idx < len(self._chain) and next_idx in self._failed_indices:
            next_idx += 1

        if next_idx >= len(self._chain):
            logger.error("FailoverChain: all %d models exhausted.", len(self._chain))
            self._index = next_idx  # park past end
            return False

        self._index = next_idx
        new_provider, new_model = self._chain[self._index]
        logger.info(
            "FailoverChain: now using %s/%s (position %d/%d).",
            new_provider,
            new_model,
            self._index + 1,
            len(self._chain),
        )
        return True

    def reset(self) -> None:
        """Reset the chain to the primary (first) model.

        Clears all failure tracking so every model is eligible again.
        """
        self._index = 0
        self._failed_indices.clear()
        self._attempts.clear()
        logger.info("FailoverChain: reset to primary model.")

    def is_exhausted(self) -> bool:
        """Return ``True`` if every model in the chain has been tried."""
        return self._index >= len(self._chain)

    def get_llm(self) -> BaseChatModel:
        """Return a LangChain ``BaseChatModel`` for the current chain position.

        Delegates to :func:`app.core.llm.get_llm`.

        Raises
        ------
        RuntimeError
            If the chain is exhausted.
        """
        provider, model_id = self.get_current()
        return _get_llm(provider=provider, model_name=model_id)

    @property
    def attempts(self) -> list[dict]:
        """Audit log of all failover attempts.

        Each entry contains ``provider``, ``model``, ``reason``, and
        ``timestamp``.
        """
        return [a.to_dict() for a in self._attempts]

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def current_provider(self) -> str:
        """Shortcut for the provider of the current model."""
        return self.get_current()[0]

    @property
    def current_model(self) -> str:
        """Shortcut for the model-id of the current model."""
        return self.get_current()[1]

    @property
    def remaining(self) -> int:
        """Number of untried models still available in the chain."""
        return max(
            0,
            len(self._chain)
            - len(self._failed_indices)
            - (1 if not self.is_exhausted() else 0),
        )

    def __repr__(self) -> str:  # pragma: no cover
        if self.is_exhausted():
            status = "EXHAUSTED"
        else:
            p, m = self.get_current()
            status = f"{p}/{m} [{self._index + 1}/{len(self._chain)}]"
        return f"<FailoverChain {status}>"
