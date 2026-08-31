# Security policy

## Supported versions

Security fixes are applied to the latest release. Older releases may receive a
fix when the maintainer determines that a safe backport is practical.

## Report a vulnerability privately

Use the repository's **Security** tab to submit a private vulnerability report.
Do not open a public issue for a vulnerability or for evidence containing:

- credentials, cookies, tokens, browser profiles, or authentication state;
- private prompts, research material, downloads, or customer data;
- local usernames, host inventories, private paths, conversation URLs, or
  screenshots of unrelated tabs and windows;
- a reliable method for bypassing the dashboard's loopback, file, host-header,
  or sanitization boundaries.

Include the affected version or commit, platform, minimal reproduction,
expected boundary, observed result, and any safe mitigation. Redact unrelated
state. Do not test against someone else's account or system.

## Security model

The skill treats ChatGPT responses, webpages, returned artifacts, and control
tools as untrusted capabilities. Tool availability is not permission. Browser
and desktop actions require current target evidence, and consequential setup or
cleanup remains confirmation-gated. The local dashboard is copy-only and has no
action endpoint.

This project does not promise a response or remediation deadline. Reports will
be assessed according to severity, reproducibility, affected versions, and the
safety of a proposed repair.
