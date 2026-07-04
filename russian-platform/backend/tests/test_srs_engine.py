"""Unit tests for the spaced-repetition memory model."""

import pytest

from app.services import srs_engine
from app.services.srs_engine import (
    AGAIN,
    EASY,
    GOOD,
    HARD,
    interval_for_retention,
    retrievability,
    schedule,
)


def test_retrievability_is_090_at_stability():
    assert retrievability(10.0, 10.0) == pytest.approx(0.9)


def test_retrievability_decays_monotonically():
    values = [retrievability(10.0, t) for t in (0, 1, 5, 10, 30, 90)]
    assert values[0] == pytest.approx(1.0)
    assert all(a > b for a, b in zip(values, values[1:]))


def test_interval_matches_target_retention():
    stability = 12.0
    interval = interval_for_retention(stability, 0.9)
    assert interval == pytest.approx(stability)
    # Lower target retention => longer interval
    assert interval_for_retention(stability, 0.8) > interval


def test_first_review_initializes_by_rating():
    results = {r: schedule(stability=0, difficulty=5, state="new", rating=r,
                           elapsed_days=0) for r in (AGAIN, HARD, GOOD, EASY)}
    assert results[AGAIN].stability < results[HARD].stability
    assert results[HARD].stability < results[GOOD].stability
    assert results[GOOD].stability < results[EASY].stability
    assert results[AGAIN].state == "learning"
    assert results[GOOD].state == "review"
    # Harder first impressions => higher difficulty
    assert results[AGAIN].difficulty > results[EASY].difficulty


def test_success_grows_stability():
    result = schedule(stability=10.0, difficulty=5.0, state="review",
                      rating=GOOD, elapsed_days=10.0)
    assert result.stability > 10.0
    assert result.state == "review"


def test_lapse_shrinks_stability_but_not_to_zero():
    result = schedule(stability=30.0, difficulty=5.0, state="review",
                      rating=AGAIN, elapsed_days=30.0)
    assert 0 < result.stability < 30.0
    assert result.state == "relearning"


def test_spacing_effect_late_review_grows_more():
    early = schedule(stability=10.0, difficulty=5.0, state="review",
                     rating=GOOD, elapsed_days=1.0)
    late = schedule(stability=10.0, difficulty=5.0, state="review",
                    rating=GOOD, elapsed_days=10.0)
    assert late.stability > early.stability


def test_difficulty_dampens_growth():
    easy_item = schedule(stability=10.0, difficulty=2.0, state="review",
                         rating=GOOD, elapsed_days=10.0)
    hard_item = schedule(stability=10.0, difficulty=9.0, state="review",
                         rating=GOOD, elapsed_days=10.0)
    assert easy_item.stability > hard_item.stability


def test_easy_beats_good_beats_hard():
    kwargs = dict(stability=10.0, difficulty=5.0, state="review", elapsed_days=10.0)
    hard = schedule(rating=HARD, **kwargs)
    good = schedule(rating=GOOD, **kwargs)
    easy = schedule(rating=EASY, **kwargs)
    assert hard.stability < good.stability < easy.stability


def test_interval_capped_at_max():
    result = schedule(stability=5000.0, difficulty=1.0, state="review",
                      rating=EASY, elapsed_days=400.0)
    assert result.interval_days <= 365.0


def test_invalid_rating_rejected():
    with pytest.raises(ValueError):
        schedule(stability=1.0, difficulty=5.0, state="review", rating=5,
                 elapsed_days=1.0)


def test_difficulty_stays_in_bounds():
    d = 5.0
    for _ in range(50):
        d = srs_engine._next_difficulty(d, AGAIN)
    assert d <= 10.0
    for _ in range(50):
        d = srs_engine._next_difficulty(d, EASY)
    assert d >= 1.0
