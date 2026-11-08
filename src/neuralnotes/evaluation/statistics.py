"""Deterministic bootstrap intervals for evaluation metrics and comparisons."""

import random
from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil, floor, isfinite
from statistics import fmean


@dataclass(frozen=True, slots=True)
class BootstrapInterval:
    """Percentile interval around a bootstrapped sample mean."""

    sample_count: int
    mean: float
    lower: float
    upper: float
    confidence_level: float
    resamples: int


def bootstrap_mean_interval(
    values: Iterable[float],
    *,
    confidence_level: float = 0.95,
    resamples: int = 2_000,
    seed: int = 0,
) -> BootstrapInterval:
    """Estimate a percentile confidence interval for a mean using seeded resampling."""
    sample = _validated_sample(values)
    _validate_options(confidence_level, resamples, seed)
    rng = random.Random(seed)
    means = sorted(fmean(rng.choices(sample, k=len(sample))) for _ in range(resamples))
    tail = (1.0 - confidence_level) / 2.0
    return BootstrapInterval(
        sample_count=len(sample),
        mean=fmean(sample),
        lower=_percentile(means, tail),
        upper=_percentile(means, 1.0 - tail),
        confidence_level=confidence_level,
        resamples=resamples,
    )


def paired_bootstrap_difference(
    baseline: Iterable[float],
    candidate: Iterable[float],
    *,
    confidence_level: float = 0.95,
    resamples: int = 2_000,
    seed: int = 0,
) -> BootstrapInterval:
    """Estimate candidate-minus-baseline mean difference over paired queries."""
    baseline_sample = _validated_sample(baseline)
    candidate_sample = _validated_sample(candidate)
    if len(baseline_sample) != len(candidate_sample):
        raise ValueError("Paired samples must have the same number of query scores.")
    differences = tuple(
        candidate_score - baseline_score
        for baseline_score, candidate_score in zip(
            baseline_sample, candidate_sample, strict=True
        )
    )
    return bootstrap_mean_interval(
        differences,
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def _validated_sample(values: Iterable[float]) -> tuple[float, ...]:
    sample = tuple(float(value) for value in values)
    if not sample:
        raise ValueError("At least one sample value is required.")
    if not all(isfinite(value) for value in sample):
        raise ValueError("Sample values must all be finite numbers.")
    return sample


def _validate_options(confidence_level: float, resamples: int, seed: int) -> None:
    if not isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be greater than 0 and less than 1.")
    if isinstance(resamples, bool) or not isinstance(resamples, int) or resamples < 1:
        raise ValueError("resamples must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer.")


def _percentile(sorted_values: list[float], percentile: float) -> float:
    position = percentile * (len(sorted_values) - 1)
    lower_index = floor(position)
    upper_index = ceil(position)
    fraction = position - lower_index
    return (
        sorted_values[lower_index] * (1.0 - fraction)
        + sorted_values[upper_index] * fraction
    )
