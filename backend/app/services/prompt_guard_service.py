"""
Prompt Guard Service — Security defense against prompt injection and jailbreaks.
Powered by Groq's meta-llama/llama-prompt-guard-2-86m and meta-llama/llama-prompt-guard-2-22m models.
"""
import time
from typing import Dict, Any, Optional
import groq
from app.core.config import settings
from app.core.logging import logger


class PromptGuardService:
    """Evaluates user prompts for prompt injections and jailbreaks using Groq Prompt Guard models."""

    SUPPORTED_MODELS = [
        "meta-llama/llama-prompt-guard-2-86m",
        "meta-llama/llama-prompt-guard-2-22m",
    ]

    @classmethod
    def get_client(cls) -> Optional[groq.Groq]:
        """Get or initialize Groq client."""
        api_key = settings.GROQ_API_KEY or settings.LLM_API_KEY
        if not api_key:
            return None
        return groq.Groq(api_key=api_key)

    @classmethod
    def check_prompt(
        cls,
        prompt: str,
        model: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check a user prompt for injection or malicious intent.

        Returns:
            Dict containing:
                - is_safe (bool): True if prompt is safe
                - score (float): Threat/injection probability (0.0 to 1.0)
                - threshold (float): Configured decision threshold
                - model (str): Prompt guard model used
                - latency_ms (float): Execution time in milliseconds
                - flagged (bool): True if threat was detected
                - reason (str): Human-readable status description
        """
        active_model = model or settings.GROQ_PROMPT_GUARD_MODEL
        if active_model not in cls.SUPPORTED_MODELS:
            active_model = "meta-llama/llama-prompt-guard-2-86m"

        active_threshold = threshold if threshold is not None else settings.PROMPT_GUARD_THRESHOLD

        if not settings.PROMPT_GUARD_ENABLED:
            return {
                "is_safe": True,
                "score": 0.0,
                "threshold": active_threshold,
                "model": active_model,
                "latency_ms": 0.0,
                "flagged": False,
                "reason": "Prompt Guard is disabled in configuration.",
            }

        client = cls.get_client()
        if not client:
            logger.warning("Groq API key not configured, skipping Prompt Guard check.")
            return {
                "is_safe": True,
                "score": 0.0,
                "threshold": active_threshold,
                "model": active_model,
                "latency_ms": 0.0,
                "flagged": False,
                "reason": "Groq API key not configured. Guard bypassed in development.",
            }

        start_time = time.time()
        try:
            # Groq Prompt Guard expects standard chat completion endpoint
            response = client.chat.completions.create(
                model=active_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )

            latency_ms = round((time.time() - start_time) * 1000, 2)
            raw_content = response.choices[0].message.content.strip()

            # The model returns the probability as a string float (e.g. '0.00048899')
            try:
                score = float(raw_content)
            except ValueError:
                logger.warning(f"Unexpected Prompt Guard output: {raw_content}")
                score = 0.0

            is_safe = score < active_threshold
            flagged = not is_safe

            reason = (
                f"Prompt passed security check (Injection score: {score:.4f})"
                if is_safe
                else f"Potential prompt injection or jailbreak detected (Threat score: {score:.4f} exceeds threshold {active_threshold})"
            )

            if flagged:
                logger.warning(f"Security Alert: Prompt flagged by {active_model} with score {score:.4f}")

            return {
                "is_safe": is_safe,
                "score": round(score, 6),
                "threshold": active_threshold,
                "model": active_model,
                "latency_ms": latency_ms,
                "flagged": flagged,
                "reason": reason,
            }

        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"Prompt Guard check failed: {str(e)}", exc_info=True)
            # Default to allowing with a warning in case of transient API error
            return {
                "is_safe": True,
                "score": 0.0,
                "threshold": active_threshold,
                "model": active_model,
                "latency_ms": latency_ms,
                "flagged": False,
                "reason": f"Prompt Guard check encountered error: {str(e)}",
            }
