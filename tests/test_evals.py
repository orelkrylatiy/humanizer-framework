import json
from pathlib import Path

from humanizer_framework import CommunicationRequest, Message
from humanizer_framework.planner import plan


def test_planner_regression_fixtures():
    fixture_path = Path(__file__).parents[1] / "evals" / "fixtures.jsonl"
    for line in fixture_path.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        request = CommunicationRequest(
            channel=case["channel"],
            domain=case["domain"],
            message_type=case["message_type"],
            profile=case["profile"],
            conversation=[Message(**m) for m in case.get("conversation", [])],
            context=case.get("context", {}),
        )
        result = plan(request)
        expected = case["expect"]
        if "action" in expected:
            assert result.action == expected["action"], case["id"]
        if "allow_cta" in expected:
            assert result.allow_cta is expected["allow_cta"], case["id"]
        if "ask_question" in expected:
            assert result.ask_question is expected["ask_question"], case["id"]
        if "max_chars_lte" in expected:
            assert result.max_chars <= expected["max_chars_lte"], case["id"]
