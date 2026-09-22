from humanizer_framework import Message, MessageType, tutoring_request
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
