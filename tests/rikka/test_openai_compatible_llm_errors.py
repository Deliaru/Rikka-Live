from open_llm_vtuber.agent.stateless_llm.openai_compatible_llm import AsyncLLM


class FakeAPIError(Exception):
    def __init__(self):
        super().__init__("fallback text")
        self.status_code = 401
        self.body = {
            "error": {
                "message": "invalid api key sk-secret-demo",
                "type": "authentication_error",
            }
        }


def test_openai_compatible_error_message_keeps_status_and_redacts_secret():
    llm = AsyncLLM(
        model="demo-model",
        base_url="https://llm.example.test/v1",
        llm_api_key="sk-secret-demo",
        api_mode="chat",
    )

    message = llm._format_api_error(
        "chat",
        FakeAPIError(),
        fallback="provider error",
    )

    assert "HTTP 401" in message
    assert "authentication_error" in message
    assert "demo-model" in message
    assert "https://llm.example.test/v1" in message
    assert "sk-secret-demo" not in message
    assert "[redacted]" in message


def test_responses_input_uses_output_text_for_assistant_history():
    llm = AsyncLLM(
        model="demo-model",
        base_url="https://llm.example.test/v1",
        llm_api_key="sk-demo",
        api_mode="responses",
    )

    payload = llm._responses_input(
        [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "听得到哦。"},
            {
                "role": "user",
                "content": [{"type": "text", "text": "再说一句"}],
            },
        ],
        system="system prompt",
    )

    assert payload[1]["content"][0]["type"] == "input_text"
    assert payload[2]["role"] == "assistant"
    assert payload[2]["content"][0]["type"] == "output_text"
    assert payload[3]["content"][0]["type"] == "input_text"


def test_responses_input_preserves_dynamic_tool_protocol_system_prompt():
    llm = AsyncLLM(
        model="demo-model",
        base_url="https://llm.example.test/v1",
        llm_api_key="sk-demo",
        api_mode="responses",
    )

    system = "\n\n".join(
        [
            "Return JSON with spoken_text subtitle_text reason_code",
            "【可用工具】",
            '{"type":"tool_request","calls":[{"tool":"<工具名>","args":{...}}]}',
            "- look_at_screen：截取主播侧屏幕。 args: {}",
            "- get_time：获取现在的本地日期和时间。 args: {}",
            '- web_search：搜索互联网。 args: {"query": "搜索词"}',
        ]
    )

    payload = llm._responses_input(
        [{"role": "user", "content": "帮我看看屏幕"}],
        system=system,
    )

    system_message = payload[0]
    assert system_message["role"] == "system"
    system_text = system_message["content"][0]["text"]
    assert system_message["content"][0]["type"] == "input_text"
    assert "【可用工具】" in system_text
    assert '"type":"tool_request"' in system_text
    assert "look_at_screen" in system_text
    assert "get_time" in system_text
    assert "web_search" in system_text
