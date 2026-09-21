from humanizer_framework import CommunicationFramework, Message, PolicyRegistry, tutoring_request


def test_custom_channel_policy_can_be_registered_without_forking():
    policies = PolicyRegistry()
    policies.register_channel("custom_marketplace", "Use compact custom marketplace chat.")
    framework = CommunicationFramework(policies=policies)
    request = tutoring_request(
        channel="custom_marketplace",
        message_type="chat_reply",
        profile="spanish",
        conversation=[Message("user", "Нужна помощь с домашним заданием")],
    )
    package = framework.prepare(request)
    assert "compact custom marketplace" in package.system
