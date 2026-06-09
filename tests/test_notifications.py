from parser.notifications import build_notification_text


def test_notification_with_username():
    text = build_notification_text(
        keyword="купить",
        group_title="Недвижимость МСК",
        username="ivan_petrov",
        sender_id=111,
        first_name="Иван",
        comment="Хочу купить квартиру",
    )
    assert "купить" in text
    assert "Недвижимость МСК" in text
    assert "https://t.me/ivan_petrov" in text
    assert "@ivan_petrov" in text
    assert "Хочу купить квартиру" in text


def test_notification_without_username_uses_tg_protocol():
    text = build_notification_text(
        keyword="продать",
        group_title="Чат",
        username=None,
        sender_id=222,
        first_name="Аноним",
        comment="Продам гараж",
    )
    assert "tg://user?id=222" in text
    assert "No Username" in text


def test_notification_html_escapes_comment():
    text = build_notification_text(
        keyword="купить",
        group_title="Чат",
        username=None,
        sender_id=333,
        first_name="Тест",
        comment="<script>alert(1)</script>",
    )
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_notification_html_escapes_group_title():
    text = build_notification_text(
        keyword="купить",
        group_title="<b>Чат</b>",
        username=None,
        sender_id=444,
        first_name="Тест",
        comment="купить",
    )
    assert "<b>Чат</b>" not in text
    assert "&lt;b&gt;Чат&lt;/b&gt;" in text
