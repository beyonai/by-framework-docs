from prompting import build_file_agent_system_prompt


def test_build_file_agent_system_prompt_includes_scope_guidance() -> None:
    prompt = build_file_agent_system_prompt(session_id="s1")

    assert "scope='private'" in prompt
    assert "scope='shared'" in prompt
    assert "default to scope='private'" in prompt
    assert "cross-agent sharing" in prompt
    assert "sessions/s1/" in prompt
    assert "public/" in prompt


def test_build_file_agent_system_prompt_includes_token_efficient_workflow() -> None:
    prompt = build_file_agent_system_prompt(session_id="s1")

    assert "glob_files" in prompt
    assert "output_mode='files_with_matches'" in prompt
    assert "read_file with offset/limit" in prompt
