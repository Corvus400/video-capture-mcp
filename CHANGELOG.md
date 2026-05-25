# Changelog

## [0.5.1](https://github.com/Corvus400/video-capture-mcp/compare/v0.5.0...v0.5.1) (2026-05-25)


### Documentation

* **readme:** clarify uvx quickstart setup ([#20](https://github.com/Corvus400/video-capture-mcp/issues/20)) ([327bd50](https://github.com/Corvus400/video-capture-mcp/commit/327bd509d001be6668e409290ce0d1eca56788d2))

## [0.5.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.4.0...v0.5.0) (2026-05-20)


### Features

* **mcp:** guide macOS permission setup for clients ([b927648](https://github.com/Corvus400/video-capture-mcp/commit/b92764837578383b46919f80d35b7ba3b11bba75))

## [0.4.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.3.0...v0.4.0) (2026-05-18)


### Features

* **mcp:** add parameter guidance for client LLMs ([01aa8ef](https://github.com/Corvus400/video-capture-mcp/commit/01aa8ef9db806686e7db55ecf9d12babeb331a4a))

## [0.3.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.2.1...v0.3.0) (2026-05-18)


### Features

* enrich MCP server instructions and tool descriptions for client LLM guidance ([cf42cbb](https://github.com/Corvus400/video-capture-mcp/commit/cf42cbbebb97f0890aee3284f0360fd0bdd7d5f9))

## [0.2.1](https://github.com/Corvus400/video-capture-mcp/compare/v0.2.0...v0.2.1) (2026-05-18)


### Bug Fixes

* keep local version metadata current ([20c03f3](https://github.com/Corvus400/video-capture-mcp/commit/20c03f324a4545edde2fcb7dd0df9bb2fdf62060))

## [0.2.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.1.1...v0.2.0) (2026-05-18)


### Features

* support manual macOS recording control ([c785323](https://github.com/Corvus400/video-capture-mcp/commit/c78532305fc317576f489e9888f53da20cde3f23))

## [Unreleased]

### Added

- Allow macOS full-screen and app-window recordings to run until explicit
  `stop_recording`, matching the iOS Simulator and Android workflow.
- Add `stop_all_recordings` for clearing active sessions when a client loses a
  session id.
- Add macOS `include_cursor` support and stop-result file metadata.

## [0.1.1] - 2026-05-18

### Fixed

- Prevent `stop_recording` hangs when recorder, adb, or ffmpeg subprocess output
  fills pipe buffers.
- Allow concurrent iPhone, iPad, and Android recordings by tracking active
  sessions per device instead of per target family.

## [0.1.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.1.0...v0.1.0) (2026-05-17)


### Features

* initial public release of video-capture-mcp v0.1.0 ([a49d50d](https://github.com/Corvus400/video-capture-mcp/commit/a49d50d562be165c39812c616bad351a9d79e195))


### Documentation

* rewrite README and add permissions/troubleshooting/development guides ([f3f5d0f](https://github.com/Corvus400/video-capture-mcp/commit/f3f5d0faaa6f7ffb6d4ae5d479131becd7de0234))

## [0.1.0] - 2026-05-18

### Added

- Initial MCP server for macOS, iOS Simulator, and Android screen recording.
- Frame extraction with scene detection and fixed-fps modes.
- macOS app-window recording, window visibility checks, pointer movement, and
  hover sequences.
- Session registry cleanup for stale recording processes.
