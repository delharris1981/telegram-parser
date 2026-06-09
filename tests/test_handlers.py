from parser.handlers import (
    has_cyrillic,
    is_spam_link,
    find_keyword_match,
    build_profile_link,
)


# --- has_cyrillic ---

def test_has_cyrillic_true():
    assert has_cyrillic("Привет мир") is True


def test_has_cyrillic_false_for_latin():
    assert has_cyrillic("Hello world") is False


def test_has_cyrillic_false_for_empty():
    assert has_cyrillic("") is False


def test_has_cyrillic_mixed():
    assert has_cyrillic("Price: 100 рублей") is True


# --- is_spam_link ---

def test_is_spam_link_joinchat():
    assert is_spam_link("Присоединяйся t.me/joinchat/ABC123") is True


def test_is_spam_link_plus_invite():
    assert is_spam_link("Вот ссылка t.me/+XYZ456") is True


def test_is_spam_link_normal_message():
    assert is_spam_link("Хочу купить квартиру в Москве") is False


def test_is_spam_link_regular_tme():
    assert is_spam_link("Мой канал t.me/my_channel") is False


# --- find_keyword_match ---

def test_find_keyword_match_exact():
    assert find_keyword_match("хочу купить квартиру", ["купить", "продать"]) == "купить"


def test_find_keyword_match_case_insensitive():
    assert find_keyword_match("Хочу КУПИТЬ квартиру", ["купить"]) == "купить"


def test_find_keyword_match_no_match():
    assert find_keyword_match("Добрый день", ["купить", "продать"]) is None


def test_find_keyword_match_empty_keywords():
    assert find_keyword_match("купить квартиру", []) is None


# --- build_profile_link ---

def test_build_profile_link_with_username():
    link = build_profile_link(username="ivan_petrov", sender_id=123)
    assert "https://t.me/ivan_petrov" in link
    assert "@ivan_petrov" in link


def test_build_profile_link_without_username():
    link = build_profile_link(username=None, sender_id=456)
    assert "tg://user?id=456" in link
    assert "No Username" in link


def test_build_profile_link_empty_username():
    link = build_profile_link(username="", sender_id=789)
    assert "tg://user?id=789" in link
