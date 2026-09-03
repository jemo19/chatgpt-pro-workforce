# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A mandatory per-submission ChatGPT Pro gate that separately verifies account
  entitlement, the declared model's selected state, and maximum thinking power
  reported as `Pro, 5 of 5` in the exact target conversation.
- Mode re-verification after conversation creation, reuse, resume, rebinding,
  reload, control recovery, and provider limit or fallback changes.
- Durable Pro-mode evidence, failure handling, status reporting, and regression
  coverage. A profile badge, collapsed `Pro` button, `High`, or remembered
  default no longer counts as maximum-power conversation proof.

## [1.2.0] - 2026-08-31

### Added

- A self-contained completed-research explorer with accepted-data validation,
  source/finding traceability, offline search and filters, print support, safe
  export placement, and deterministic build/verify tooling.
- A guided explorer policy and copyable `export explorer` run control.

### Changed

- Replaced the rejected green dashboard with a new shared dashboard/research
  reading system designed through a bounded ChatGPT Pro web lane.
- Reworked README wording and documented the new interface system.

## [1.1.0] - 2026-08-31

### Added

- Complete lettered guided-start menus with purpose, tradeoff, and a
  recommendation for every currently valid option.
- Exact-run dashboard verification and a bounded `dashboard troubleshoot`
  recovery intent.
- Dashboard projection diagnostics, last-known-good retention, and bounded
  connection retry states.

### Changed

- Refined the dashboard into a flatter operations ledger based on a bounded
  ChatGPT Pro web research lane and live Chrome visual acceptance.
- Expanded deterministic dashboard and guided-start coverage from the first
  public test run.

## [1.0.0] - 2026-08-31

### Added

- Guided kickoff and explicit Pro/Codex allocation profiles.
- First-use, every-invocation, and fault-triggered capability preflight.
- Bounded ChatGPT Pro research, review, calculation, synthesis, and artifact
  lanes with stable IDs and durable state.
- Safe concurrency ceiling, throttling warning, and duplicate suppression.
- Pause, usage-limit, resume, monitoring, recovery, and durable handoff flows.
- Linux, macOS, and Windows browser/desktop control guidance.
- Obsidian vault discovery, research-note structure, and native artifact index.
- Download retention and hash-bound cleanup policy.
- Sanitized loopback-only dashboard with detailed help and copyable controls.
- Dependency-free runtime helpers and public deterministic validation suites.

[Unreleased]: https://github.com/jemo19/chatgpt-pro-workforce/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/jemo19/chatgpt-pro-workforce/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jemo19/chatgpt-pro-workforce/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jemo19/chatgpt-pro-workforce/releases/tag/v1.0.0
