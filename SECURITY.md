# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x     | Yes       |

## Reporting a Vulnerability

Please report security issues through GitHub Private Security Advisories for
this repository. Do not open a public issue for a suspected vulnerability.

When reporting, include:

- The affected version or commit.
- The operating system and recording backend involved.
- A minimal reproduction, if available.
- The expected impact and any known workaround.

## Scope

In scope:

- Subprocess argument sanitization issues in commands launched by this server.
- AppleScript injection in macOS window activation or bounds lookup.
- Path traversal or unsafe writes caused by server-managed default output paths.
- Session registry file permission problems.

Out of scope:

- Authorization decisions made by the calling MCP client.
- Abuse of Screen Recording, Accessibility, adb, or Simulator permissions that
  the user intentionally granted to the server process.
- Vulnerabilities in ffmpeg, ffprobe, screencapture, xcrun, simctl, adb, or the
  operating system itself.
- Writes to an explicit `output_path` supplied by a trusted MCP client or user.

## Coordinated Disclosure

1. Report the issue through GitHub Private Security Advisories.
2. The maintainer acknowledges receipt and confirms the affected scope.
3. A fix is prepared privately and regression tests are added when practical.
4. A patched release is published.
5. The advisory is published with impact, affected versions, and mitigation
   details.
