from humanizer_framework import Message, tutoring_request, job_search_request
from humanizer_framework.grounding import validate_grounding


def _req(context=None, conversation=None, business_rules=None):
    return job_search_request(
        channel="hh", message_type="application", profile="frontend",
        context=context or {}, conversation=conversation or [],
        business_rules=business_rules or [],
    )


def _codes(text, request):
    return {issue.code for issue in validate_grounding(text, request)}


def test_rejects_invented_numeric_experience():
    request = _req({"experience": "5 лет, React и TypeScript"})
    assert "unsupported_number" in _codes("У меня 7 лет опыта.", request)
    assert "unsupported_number" not in _codes("У меня 5 лет опыта.", request)


def test_russian_number_words_are_checked():
    request = _req({"experience": "5 лет опыта"})
    assert "unsupported_number" not in _codes("Пять лет занимаюсь разработкой.", request)
    assert "unsupported_number" in _codes("Семь лет занимаюсь разработкой.", request)


def test_numbers_in_client_questions_can_be_reused():
    request = _req(conversation=[Message("user", "Есть опыт с React 19?")])
    assert "unsupported_number" not in _codes("Да, с React 19 знаком.", request)


def test_new_date_or_price_is_not_silently_invented():
    request = _req()
    assert "unsupported_number" in _codes("Стоимость 2000 рублей.", request)


def test_url_numbers_do_not_trigger_false_alarm():
    request = _req()
    assert "unsupported_number" not in _codes(
        "Подробности https://example.test/profile/2026", request
    )


def test_unverified_availability_is_hard_invalid():
    request = tutoring_request(
        channel="profi", message_type="chat_reply", profile="math",
        conversation=[Message("user", "Завтра в 17:00 сможете?")],
    )
    assert "unverified_availability" in _codes("Могу завтра в 17:00.", request)
    request.context["slots"] = ["завтра в 17:00"]
    assert "unverified_availability" not in _codes("Могу завтра в 17:00.", request)


def test_unsupported_management_claim_is_rejected():
    request = _req({"experience": "React, TypeScript"})
    assert "unsupported_claim" in _codes("Руководил командой из 12 человек.", request)


def test_verified_management_claim_is_allowed():
    request = _req({"experience": "Руководил командой из 12 человек."})
    assert "unsupported_claim" not in _codes("Руководил командой из 12 человек.", request)


def test_unverified_guarantee_is_rejected():
    assert "unsupported_claim" in _codes("Гарантирую результат.", _req())


def test_factual_guard_does_not_require_numbers_in_every_message():
    assert not validate_grounding(
        "Разберем домашние задания по порядку.", _req()
    )
