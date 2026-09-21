from humanizer_framework import (
    CommunicationFramework,
    Message,
    MessageType,
    MockProvider,
    tutoring_request,
)


def test_generate_retries_when_first_answer_contains_forbidden_cta():
    provider = MockProvider(
        [
            "Давайте начнем с пробного: когда вам удобно?",
            "Понял) Тогда в основном домашки и будем разбирать.",
        ]
    )
    framework = CommunicationFramework(provider)
    request = tutoring_request(
        channel="profi",
        message_type=MessageType.CHAT_REPLY,
        profile="informatics",
        conversation=[Message("user", "Задача делать домашки")],
    )
    result = framework.generate(request)
    assert result.rewritten is True
    assert result.valid
    assert result.text == "Понял) Тогда в основном домашки и будем разбирать."
    assert len(provider.calls) == 2


def test_prepare_works_without_provider():
    framework = CommunicationFramework()
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="chinese",
        conversation=[],
    )
    package = framework.prepare(request)
    assert package.plan.action == "pitch"
