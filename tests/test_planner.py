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
        channel="repetitor",
        message_type="outreach",
        profile="chinese",
        conversation=[],
    )
    result = plan(request)
    assert result.action == "pitch"
    assert result.max_chars == 420
