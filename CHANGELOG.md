# Changelog

## [0.1.0](https://github.com/Corvus400/video-capture-mcp/compare/v0.1.1...v0.1.0) (2026-05-18)


### Features

* initial public release of video-capture-mcp v0.1.0 ([a49d50d](https://github.com/Corvus400/video-capture-mcp/commit/a49d50d562be165c39812c616bad351a9d79e195))


### Bug Fixes

* prevent recording stop deadlocks ([9a61012](https://github.com/Corvus400/video-capture-mcp/commit/9a61012bb43f7fdfb5a92f2cd0950b5ee81282b1))


### Documentation

* rewrite README and add permissions/troubleshooting/development guides ([f3f5d0f](https://github.com/Corvus400/video-capture-mcp/commit/f3f5d0faaa6f7ffb6d4ae5d479131becd7de0234))

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

## [Unreleased]

## [0.1.0] - 2026-05-18

### Added

- Initial MCP server for macOS, iOS Simulator, and Android screen recording.
- Frame extraction with scene detection and fixed-fps modes.
- macOS app-window recording, window visibility checks, pointer movement, and
  hover sequences.
- Session registry cleanup for stale recording processes.
