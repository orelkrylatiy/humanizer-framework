from humanizer_framework import Message, MessageType, tutoring_request
from humanizer_framework.planner import plan


def test_short_disclosure_is_acknowledged_without_cta():
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )
    result = plan(request)
    assert result.action == "acknowledge"
    assert result.allow_cta is False
    assert result.ask_question is False
    assert result.max_chars == 180


def test_question_is_answered_without_forced_next_step():
    request = tutoring_request(
        channel="profi",
        message_type="chat_reply",
        profile="spanish",
        conversation=[Message("user", "А программирование тоже ведете?")],
    )
    result = plan(request)
    assert result.action == "answer"
    assert result.allow_cta is False


def test_outreach_has_larger_budget():
    request = tutoring_request(
        channel="repetit",
        message_type="outreach",
        profile="chinese",
        conversation=[],
    )
    result = plan(request)
    assert result.action == "pitch"
    assert result.max_chars == 420


def test_duration_question_is_not_misclassified_as_scheduling():
    request = tutoring_request(
        channel="profi",
        message_type="chat_reply",
        profile="informatics",
        conversation=[Message("client", "Сколько времени нужно на подготовку?")],
    )
    result = plan(request)
    assert result.action == "answer"
    assert result.stage == "discovery"


def test_chinese_fullwidth_question_is_detected():
    request = tutoring_request(
        channel="telegram",
        message_type="chat_reply",
        profile="chinese",
        conversation=[Message("client", "你也教编程吗？")],
        language="zh",
    )
    result = plan(request)
    assert result.action == "answer"
    assert result.allow_cta is False


def test_spanish_scheduling_is_detected():
    request = tutoring_request(
        channel="telegram",
        message_type="chat_reply",
        profile="spanish",
        conversation=[Message("client", "¿Cuándo te viene bien?")],
        language="es",
    )
    result = plan(request)
    assert result.action == "schedule"


def test_chinese_objection_is_detected():
    request = tutoring_request(
        channel="telegram",
        message_type="chat_reply",
        profile="chinese",
        conversation=[Message("client", "这个价格太贵了")],
        language="zh",
    )
    result = plan(request)
    assert result.action == "handle_objection"
