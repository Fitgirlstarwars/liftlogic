"""
Extraction Evaluator - Quality evaluation for extraction results.

Uses LLM-as-judge pattern to evaluate faithfulness, completeness, and consistency.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import ExtractionResult, QualityScore

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient

logger = logging.getLogger(__name__)

__all__ = ["ExtractionEvaluator"]

EVALUATION_PROMPT = """You are evaluating the quality of an AI extraction from a technical document.

SOURCE TEXT (excerpt):
{source_text}

EXTRACTION RESULT:
- Components extracted: {component_count}
- Fault codes extracted: {fault_code_count}
- Tables extracted: {table_count}
- Sample fault codes: {sample_faults}
- Sample components: {sample_components}

Evaluate on these criteria (0.0 to 1.0):

1. FAITHFULNESS: Are the extracted items accurate and supported by the source?
   - 1.0 = All items are directly supported by source text
   - 0.5 = Some items have minor inaccuracies
   - 0.0 = Major hallucinations or fabrications

2. COMPLETENESS: Did the extraction capture all important information?
   - 1.0 = All fault codes, components, and tables captured
   - 0.5 = Some items missed
   - 0.0 = Most important items missed

3. CONSISTENCY: Is the extraction internally consistent?
   - 1.0 = All IDs match, no contradictions
   - 0.5 = Minor inconsistencies
   - 0.0 = Major contradictions

Return JSON:
{{
    "faithfulness": 0.0-1.0,
    "completeness": 0.0-1.0,
    "consistency": 0.0-1.0,
    "issues": ["list of specific issues found"]
}}"""


class ExtractionEvaluator:
    """
    Evaluator for extraction quality using LLM-as-judge.

    Example:
        >>> evaluator = ExtractionEvaluator(gemini_client)
        >>> score = await evaluator.evaluate(result, source_text)
        >>> print(f"Quality: {score.overall:.2f}")
    """

    def __init__(self, client: GeminiClient) -> None:
        """
        Initialize evaluator.

        Args:
            client: Gemini client for LLM-as-judge
        """
        self._client = client

    async def evaluate(
        self,
        result: ExtractionResult,
        source_text: str,
    ) -> QualityScore:
        """
        Evaluate extraction quality.

        Args:
            result: Extraction result to evaluate
            source_text: Original source text

        Returns:
            Quality scores
        """
        # Prepare prompt
        sample_faults = [f.code for f in result.fault_codes[:5]]
        sample_components = [c.id for c in result.components[:5]]

        prompt = EVALUATION_PROMPT.format(
            source_text=source_text[:5000],  # Limit source text
            component_count=len(result.components),
            fault_code_count=len(result.fault_codes),
            table_count=len(result.tables),
            sample_faults=sample_faults,
            sample_components=sample_components,
        )

        try:
            response = await self._client.generate_json(prompt)

            faithfulness = float(response.get("faithfulness", 0.5))
            completeness = float(response.get("completeness", 0.5))
            consistency = float(response.get("consistency", 0.5))
            issues = response.get("issues", [])

            score = QualityScore.compute_overall(
                faithfulness=faithfulness,
                completeness=completeness,
                consistency=consistency,
            )
            score.issues = issues

            logger.info(
                "Quality evaluation: faithfulness=%.2f, completeness=%.2f, overall=%.2f",
                faithfulness,
                completeness,
                score.overall,
            )

            return score

        except Exception as e:
            logger.warning("Quality evaluation failed: %s", e)
            return QualityScore(
                faithfulness=0.5,
                completeness=0.5,
                consistency=0.5,
                overall=0.5,
                issues=[f"Evaluation failed: {e}"],
            )

    async def evaluate_batch(
        self,
        results: list[tuple[ExtractionResult, str]],
    ) -> list[QualityScore]:
        """
        Evaluate multiple extractions.

        Args:
            results: List of (extraction_result, source_text) tuples

        Returns:
            List of quality scores
        """
        scores = []
        for result, source_text in results:
            score = await self.evaluate(result, source_text)
            scores.append(score)
        return scores
