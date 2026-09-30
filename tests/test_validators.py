from humanizer_framework import Message, MessageType, job_search_request, tutoring_request
from humanizer_framework.planner import plan
from humanizer_framework.policies import default_constraints
from humanizer_framework.validators import normalize_output, validate_output


def _request():
    return tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )


def test_russian_messenger_normalization():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    value = normalize_output("Понял: всё разберём — спокойно.", constraints, "ru")
    assert "ё" not in value
    assert "—" not in value
    assert ":" not in value


def test_unplanned_trial_cta_is_hard_issue():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output(
        "Давайте начнем с пробного урока. Когда вам удобно?",
        request,
        current_plan,
        constraints,
    )
    assert any(issue.code == "unplanned_cta" and issue.hard for issue in issues)


def test_recent_template_similarity_is_detected():
    request = _request()
    request.conversation.insert(
        0,
        Message("assistant", "Понял, тогда можно разбирать домашки и закрывать пробелы по ходу."),
    )
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output(
        "Понял, тогда можно разбирать домашки и закрывать пробелы по ходу.",
        request,
        current_plan,
        constraints,
    )
    assert any(issue.code == "template_similarity" for issue in issues)


def test_known_name_is_required_in_first_tutoring_outreach():
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="office",
        conversation=[],
        context={"client_name": "Виктор"},
    )
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output(
        "Здравствуйте) С Word могу помочь. Что чаще всего приходится делать?",
        request,
        current_plan,
        constraints,
    )
    assert any(issue.code == "missing_client_name" and issue.hard for issue in issues)


def test_time_colon_survives_russian_normalization():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    value = normalize_output("Могу в 18:30. Формат: онлайн", constraints, "ru")
    assert "18:30" in value
    assert "Формат, онлайн" in value


def test_text_smiley_colon_survives_normalization():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    value = normalize_output("Привет:) Формат: онлайн", constraints, "ru")
    assert "Привет:)" in value
    assert "Формат, онлайн" in value


def test_text_smiley_colon_is_not_forbidden_issue():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output("Разберёмся:)", request, current_plan, constraints)
    assert not any(issue.code == "forbidden_colon" for issue in issues)
    issues = validate_output("Всё по плану: онлайн", request, current_plan, constraints)
    assert any(issue.code == "forbidden_colon" for issue in issues)


def test_unplanned_question_is_hard_issue():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output("Понял) А что еще нужно?", request, current_plan, constraints)
    assert any(issue.code == "unplanned_question" and issue.hard for issue in issues)


def test_fullwidth_question_mark_is_counted():
    request = tutoring_request(
        channel="telegram",
        message_type="chat_reply",
        profile="chinese",
        conversation=[Message("client", "好的")],
        language="zh",
    )
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output("还需要什么？", request, current_plan, constraints)
    assert any(issue.code == "unplanned_question" for issue in issues)


def test_truncated_application_is_flagged_as_too_short():
    request = tutoring_request(
        channel="hh",
        message_type="application",
        profile="frontend",
        conversation=[],
    )
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output(
        "Пишу по вакансии. Пять лет на React и TypeScript, сейчас делаю торговый",
        request,
        current_plan,
        constraints,
    )
    assert any(issue.code == "too_short" and not issue.hard for issue in issues)


def test_short_chat_reply_is_not_flagged_as_too_short():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output("Ок, давайте завтра.", request, current_plan, constraints)
    assert not any(issue.code == "too_short" for issue in issues)


def test_empty_output_is_hard_issue():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output("", request, current_plan, constraints)
    assert len(issues) == 1
    assert issues[0].code == "empty_message"
    assert issues[0].hard


def test_bot_role_participates_in_similarity_check():
    request = _request()
    request.conversation.insert(
        0,
        Message("bot", "Понял, тогда можно разбирать домашки и закрывать пробелы по ходу."),
    )
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    issues = validate_output(
        "Понял, тогда можно разбирать домашки и закрывать пробелы по ходу.",
        request,
        current_plan,
        constraints,
    )
    assert any(issue.code == "template_similarity" for issue in issues)


def _hh_request():
    return job_search_request(
        channel="hh",
        message_type=MessageType.CHAT_REPLY,
        profile="frontend",
        conversation=[Message("user", "Когда удобно созвониться?")],
    )


def test_smiley_is_hard_issue_for_job_search():
    request = _hh_request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    for text in ("Завтра после 15:00:)", "Хорошо))", "Отлично, спасибо)", "✓ Готов"):
        issues = validate_output(text, request, current_plan, constraints)
        assert any(issue.code == "forbidden_smiley" and issue.hard for issue in issues), text


def test_bare_paren_smiley_detected_but_enumeration_not():
    from humanizer_framework.validators import _has_smiley

    assert _has_smiley("Хорошо)")
    assert _has_smiley("Понял :)")
    assert not _has_smiley("Есть опыт (финтех, торговые терминалы).")
    assert not _has_smiley("1) опыт 2) стек 3) сроки")


def test_smiley_allowed_for_informal_russian_channels():
    request = _request()
    current_plan = plan(request)
    constraints = default_constraints(request, current_plan)
    assert constraints.forbid_smileys is False
    issues = validate_output("Понял, задача делать домашки :)", request, current_plan, constraints)
    assert not any(issue.code == "forbidden_smiley" for issue in issues)
