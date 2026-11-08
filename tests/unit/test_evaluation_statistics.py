"""Tests for reproducible bootstrap intervals and paired comparisons."""

import pytest

from neuralnotes.evaluation.statistics import (
    bootstrap_mean_interval,
    paired_bootstrap_difference,
)


def test_bootstrap_interval_is_reproducible_and_reports_sample_mean() -> None:
    values = (0.0, 0.5, 1.0, 1.0)

    first = bootstrap_mean_interval(values, resamples=500, seed=23)
    second = bootstrap_mean_interval(values, resamples=500, seed=23)

    assert first == second
    assert first.sample_count == 4
    assert first.mean == pytest.approx(0.625)
    assert first.lower <= first.mean <= first.upper


def test_bootstrap_interval_is_degenerate_for_one_query() -> None:
    interval = bootstrap_mean_interval((0.75,), resamples=100)

    assert interval.sample_count == 1
    assert interval.lower == interval.mean == interval.upper == 0.75


def test_paired_bootstrap_resamples_query_level_differences() -> None:
    result = paired_bootstrap_difference(
        (0.1, 0.3, 0.8),
        (0.2, 0.3, 1.0),
        resamples=500,
        seed=7,
    )

    assert result.sample_count == 3
    assert result.mean == pytest.approx(0.1)
    assert result.lower <= result.mean <= result.upper


@pytest.mark.parametrize(
    ("values", "options", "message"),
    [
        ((), {}, "At least one sample"),
        ((float("nan"),), {}, "finite numbers"),
        ((1.0,), {"confidence_level": 1.0}, "confidence_level"),
        ((1.0,), {"resamples": 0}, "resamples"),
        ((1.0,), {"seed": True}, "seed"),
    ],
)
def test_bootstrap_rejects_invalid_inputs(values, options, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        bootstrap_mean_interval(values, **options)


def test_paired_bootstrap_requires_matching_sample_sizes() -> None:
    with pytest.raises(ValueError, match="same number"):
        paired_bootstrap_difference((0.1, 0.2), (0.3,))
