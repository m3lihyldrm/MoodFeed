"""Tests for SUS (System Usability Scale) Score Calculation."""

import pytest
from backend.sus import calculate_sus_score


def test_sus_score_maximum_possible():
    # Odd items 5 (contributions: 5-1=4), Even items 1 (contributions: 5-1=4)
    # Total sum = 10 * 4 = 40. SUS = 40 * 2.5 = 100.0
    responses = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]
    assert calculate_sus_score(responses) == 100.0


def test_sus_score_minimum_possible():
    # Odd items 1 (contributions: 1-1=0), Even items 5 (contributions: 5-5=0)
    # Total sum = 0. SUS = 0 * 2.5 = 0.0
    responses = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]
    assert calculate_sus_score(responses) == 0.0


def test_sus_score_all_neutral():
    # All items 3: odd (3-1=2), even (5-3=2)
    # Total sum = 10 * 2 = 20. SUS = 20 * 2.5 = 50.0
    responses = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
    assert calculate_sus_score(responses) == 50.0


def test_sus_score_all_highest_agreement():
    # All items 5: odd (5-1=4), even (5-5=0)
    # Total sum = 5 * 4 = 20. SUS = 20 * 2.5 = 50.0
    responses = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    assert calculate_sus_score(responses) == 50.0


def test_sus_score_all_lowest_agreement():
    # All items 1: odd (1-1=0), even (5-1=4)
    # Total sum = 5 * 4 = 20. SUS = 20 * 2.5 = 50.0
    responses = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    assert calculate_sus_score(responses) == 50.0


def test_sus_score_realistic_good_pilot_session():
    # Sample realistic favorable usability score
    responses = [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]
    # odd: 5 * 3 = 15, even: 5 * 3 = 15. sum = 30 -> 30 * 2.5 = 75.0
    assert calculate_sus_score(responses) == 75.0

    high_responses = [5, 2, 4, 2, 5, 1, 4, 2, 5, 1]
    # odd: (4 + 3 + 4 + 3 + 4) = 18
    # even: (3 + 3 + 4 + 3 + 4) = 17
    # sum = 35 -> 35 * 2.5 = 87.5
    assert calculate_sus_score(high_responses) == 87.5


def test_sus_score_validation_errors():
    # Invalid length (< 10 or > 10)
    with pytest.raises(ValueError, match="tam 10 soru"):
        calculate_sus_score([3, 3, 3])

    with pytest.raises(ValueError, match="tam 10 soru"):
        calculate_sus_score([3] * 11)

    # Invalid range (< 1 or > 5)
    with pytest.raises(ValueError, match="1 ile 5 arasında"):
        calculate_sus_score([0, 3, 3, 3, 3, 3, 3, 3, 3, 3])

    with pytest.raises(ValueError, match="1 ile 5 arasında"):
        calculate_sus_score([3, 6, 3, 3, 3, 3, 3, 3, 3, 3])
