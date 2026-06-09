from unittest.mock import patch
from parser.auto_join import compute_backoff_delay, is_russian_group


# --- compute_backoff_delay ---

def test_backoff_first_attempt_is_at_least_base():
    with patch("parser.auto_join.random") as mock_r:
        mock_r.uniform.return_value = 0.5  # jitter = 0.5
        delay = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
    # deterministic=2, jitter=0.5, result=2.5
    assert delay >= 2.0


def test_backoff_increases_with_attempts():
    with patch("parser.auto_join.random") as mock_r:
        mock_r.uniform.side_effect = [0.0, 0.0]  # zero jitter both calls
        d0 = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
        d3 = compute_backoff_delay(attempt=3, base=2.0, cap=300.0)
    # d0=2.0, d3=16.0 (deterministic values with zero jitter)
    assert d3 > d0


def test_backoff_capped_at_max():
    with patch("parser.auto_join.random") as mock_r:
        mock_r.uniform.return_value = 300.0  # max possible jitter
        delay = compute_backoff_delay(attempt=50, base=2.0, cap=300.0)
    assert delay <= 300.0


# --- is_russian_group ---

def test_is_russian_group_true_from_title():
    assert is_russian_group(title="Недвижимость Москва", description=None) is True


def test_is_russian_group_true_from_description():
    assert is_russian_group(title="Real Estate", description="Квартиры в Москве") is True


def test_is_russian_group_both_latin():
    assert is_russian_group(title="Real Estate Moscow", description="Apartments for sale") is False


def test_is_russian_group_none_description():
    assert is_russian_group(title="Москва", description=None) is True
