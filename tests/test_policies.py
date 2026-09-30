from humanizer_framework import CommunicationFramework, Message, PolicyRegistry, tutoring_request
from humanizer_framework.planner import plan


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


def test_language_policy_is_explicit_and_extensible():
    policies = PolicyRegistry()
    policies.register_language("de", "Write in German.")
    framework = CommunicationFramework(policies=policies)
    request = tutoring_request(
        channel="profi",
        message_type="outreach",
        profile="german",
        conversation=[],
        language="de",
    )
    package = framework.prepare(request)
    assert "Write in German." in package.system


def test_hh_channel_policy_forbids_smileys():
    from humanizer_framework import Message, MessageType, job_search_request
    from humanizer_framework.policies import render_policy

    request = job_search_request(
        channel="hh",
        message_type=MessageType.CHAT_REPLY,
        profile="frontend",
        conversation=[Message("user", "Когда удобно созвониться?")],
    )
    policy = render_policy(request, plan(request))
    assert "No smileys" in policy
