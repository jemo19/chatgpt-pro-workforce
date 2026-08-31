# Support

## Before opening an issue

1. Start a fresh Codex session so skill discovery is current.
2. Run `$chatgpt-pro-workforce help` and the every-invocation readiness gate.
3. Reproduce with a disposable task and public or synthetic data when possible.
4. Record the skill version, operating system, selected route, capability
   states, run/lane IDs, expected result, and observed result.
5. Remove credentials, private prompts, browser state, local paths, customer
   information, and unrelated screenshots.

Use the bug-report issue form for reproducible defects and the feature-request
form for bounded improvements. Use a private security report for anything that
could expose data or weaken a trust boundary.

## Test-run monitoring

For live run help, provide the run ID and ask Codex to perform read-only status
and capability checks. A useful prompt is:

```text
Monitor RUN_ID during this active session. Report material state changes, verify the affected browser or computer-control layer if progress stalls, preserve current worker state, and stop for my decision before any new permission, installation, destructive action, or broader target.
```

See [docs/test-run-monitoring.md](docs/test-run-monitoring.md) for the full
checklist. Monitoring cannot continue after the active Codex session ends unless
the user starts a separately authorized monitoring facility.
