"""Regression tests ensuring MCP server instructions and tool descriptions stay informative.

These assertions guard the wiring between docs/ and the FastMCP server so that
client LLMs (Claude Code, Codex, etc.) keep receiving the guidance they need to
pick the right tool, hand-craft options, and recover from typical failures.
"""

import pytest

from video_capture_mcp import server as server_module


def test_server_instructions_cover_critical_sections() -> None:
    instructions = server_module.mcp._mcp_server.instructions
    assert instructions, "FastMCP must be constructed with instructions"
    for marker in (
        "Decision tree",
        "Target aliases",
        "Manual-stop workflow",
        "Permissions",
        "Common failure modes",
    ):
        assert marker in instructions, f"instructions missing section: {marker}"


def test_instructions_cover_new_sections() -> None:
    instructions = server_module.mcp._mcp_server.instructions
    for marker in (
        "Frame extraction context cost",
        "xcode-select --install",
        "fully restart the MCP client",
        "uvx --from video-capture-mcp python",
        "user_message",
        "Claude Code or Codex",
    ):
        assert marker in instructions, f"instructions missing: {marker}"


def _tool_descriptions() -> dict[str, str]:
    return {
        tool.name: tool.description
        for tool in server_module.mcp._tool_manager.list_tools()
    }


def test_twelve_tools_registered() -> None:
    descriptions = _tool_descriptions()
    message = f"expected 12 tools, got {len(descriptions)}: {sorted(descriptions)}"
    assert len(descriptions) == 12, message


def test_check_macos_permissions_description_is_client_facing() -> None:
    desc = _tool_descriptions()["check_macos_permissions"]
    for marker in (
        "Claude Code/Codex",
        "Screen Recording",
        "launcher process",
        "fully restarted",
        "user_message",
        "Accessibility",
    ):
        assert marker in desc, f"check_macos_permissions missing marker: {marker}"


def test_start_recording_description_includes_target_and_manual_stop() -> None:
    desc = _tool_descriptions()["start_recording"]
    for marker in ("macos", "ios_simulator", "android", "manual"):
        assert marker in desc, f"start_recording missing marker: {marker}"


def test_stop_recording_description_includes_verify_fields() -> None:
    desc = _tool_descriptions()["stop_recording"]
    for marker in ("file_exists", "file_size_bytes"):
        assert marker in desc, f"stop_recording missing marker: {marker}"


def test_extract_frames_description_includes_modes() -> None:
    desc = _tool_descriptions()["extract_frames"]
    for marker in ("scene", "fixed_fps"):
        assert marker in desc, f"extract_frames missing marker: {marker}"


def test_hover_sequence_description_mentions_app_name_and_no_click() -> None:
    desc = _tool_descriptions()["hover_sequence"]
    assert "app_name" in desc
    assert "click" in desc.lower()  # explains that it does NOT click


def test_tool_parameters_have_descriptions() -> None:
    tools = server_module.mcp._tool_manager.list_tools()
    missing: list[str] = []
    for tool in tools:
        schema = tool.parameters
        props = schema.get("properties", {})
        for pname, pschema in props.items():
            if not pschema.get("description"):
                missing.append(f"{tool.name}.{pname}")
    assert not missing, f"parameters lacking description: {missing}"


def test_extract_frames_inline_images_warns_about_context() -> None:
    tools = {t.name: t for t in server_module.mcp._tool_manager.list_tools()}
    schema = tools["extract_frames"].parameters
    inline = schema["properties"]["inline_images"]["description"]
    assert "context" in inline.lower()
    assert "false" in inline.lower()


def test_hover_sequence_points_format_explicit() -> None:
    tools = {t.name: t for t in server_module.mcp._tool_manager.list_tools()}
    pts = tools["hover_sequence"].parameters["properties"]["points"]["description"]
    assert '{"x"' in pts or '"x"' in pts
    assert "[x, y]" in pts or "x, y" in pts


@pytest.mark.asyncio
async def test_check_macos_permissions_returns_user_message(monkeypatch) -> None:
    async def fake_diagnose_screen_recording():
        return {
            "ok": False,
            "required_permission": "Screen Recording",
            "settings_path": "System Settings > Privacy & Security > Screen Recording",
            "launcher_process": "/test/python",
            "restart_required": True,
            "user_message": "Grant Screen Recording, then restart Claude Code or Codex.",
        }

    monkeypatch.setattr(
        server_module.macos, "diagnose_screen_recording", fake_diagnose_screen_recording
    )

    result = await server_module.check_macos_permissions()

    assert result["user_message"] == (
        "Grant Screen Recording, then restart Claude Code or Codex."
    )
    assert "Claude Code or Codex" in result["client_guidance"]
    assert result["ios_android_screen_recording_required"] is False
    assert result["pointer_tools_permission"] == "Accessibility"
