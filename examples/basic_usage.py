from humanizer_framework import (
    CommunicationFramework,
    LiteLLMProvider,
    Message,
    MessageType,
    tutoring_request,
)

provider = LiteLLMProvider("zai/glm-4.7")
framework = CommunicationFramework(provider)

request = tutoring_request(
    channel="profi",
    message_type=MessageType.CHAT_REPLY,
    profile="informatics",
    conversation=[Message("user", "Задача делать домашки")],
    context={"subjects": ["informatics", "programming"]},
)

print(framework.generate(request).text)
