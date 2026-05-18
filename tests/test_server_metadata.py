"""Regression tests ensuring MCP server instructions and tool descriptions stay informative.

These assertions guard the wiring between docs/ and the FastMCP server so that
client LLMs (Claude Code, Codex, etc.) keep receiving the guidance they need to
pick the right tool, hand-craft options, and recover from typical failures.
"""

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
    ):
        assert marker in instructions, f"instructions missing: {marker}"


def _tool_descriptions() -> dict[str, str]:
    return {
        tool.name: tool.description
        for tool in server_module.mcp._tool_manager.list_tools()
    }


def test_eleven_tools_registered() -> None:
    descriptions = _tool_descriptions()
    message = f"expected 11 tools, got {len(descriptions)}: {sorted(descriptions)}"
    assert len(descriptions) == 11, message


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
