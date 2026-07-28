"""Scoring Function Evaluator Module."""

from typing import List
from burn_job.domain.variant import ScoringResult
from burn_job.core.config import WEIGHT_LATENCY_P95, WEIGHT_RPS, WEIGHT_GC_ALLOC
from burn_job.core.logging import setup_logger

logger = setup_logger("Scorer")

class ScoringEvaluator:
    """Evaluates and ranks code variant performance metrics relative to baseline."""

    @staticmethod
    def calculate_score(
        variant_id: str,
        base_p95: float,
        var_p95: float,
        base_rps: float,
        var_rps: float,
        base_gc: float,
        var_gc: float,
    ) -> ScoringResult:
        latency_p95_delta_pct = ((base_p95 - var_p95) / base_p95 * 100.0) if base_p95 > 0 else 0.0
        rps_delta_pct = ((var_rps - base_rps) / base_rps * 100.0) if base_rps > 0 else 0.0
        gc_delta_pct = ((base_gc - var_gc) / base_gc * 100.0) if base_gc > 0 else 0.0

        score = (
            WEIGHT_LATENCY_P95 * latency_p95_delta_pct +
            WEIGHT_RPS * rps_delta_pct +
            WEIGHT_GC_ALLOC * gc_delta_pct
        )

        return ScoringResult(
            variant_id=variant_id,
            latency_p95_delta_pct=round(latency_p95_delta_pct, 2),
            rps_delta_pct=round(rps_delta_pct, 2),
            gc_delta_pct=round(gc_delta_pct, 2),
            score=round(score, 4),
            is_winner=False,
        )

    @classmethod
    def select_winner(cls, results: List[ScoringResult]) -> ScoringResult:
        if not results:
            return ScoringResult(variant_id="baseline", score=0.0, is_winner=True)

        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        winner = sorted_results[0]
        if winner.score > 0:
            winner.is_winner = True
            logger.info(f"Selected Winner Variant: {winner.variant_id} (Score: {winner.score})")
        else:
            logger.info("No variant achieved positive performance score. Retaining baseline.")
        return winner
