from parser.auto_join import compute_backoff_delay, is_russian_group


# --- compute_backoff_delay ---

def test_backoff_first_attempt_is_positive():
    delay = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
    assert delay >= 2.0


def test_backoff_increases_with_attempts():
    d0 = compute_backoff_delay(attempt=0, base=2.0, cap=300.0)
    d3 = compute_backoff_delay(attempt=3, base=2.0, cap=300.0)
    assert d3 > d0


def test_backoff_capped_at_max():
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
