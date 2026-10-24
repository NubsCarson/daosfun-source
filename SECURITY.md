# Security policy

This is a faithful reconstruction and research repository, not a secured fork.
The source and byte-identical binaries intentionally retain the findings documented
in [the first pass](audit/FIRST_PASS.md) and [the second pass](audit/SECOND_PASS.md).
Do not treat a successful reproduction or test run as approval to deploy.

## Reporting another finding

Private vulnerability reporting is enabled. Submit findings through the
[private GitHub advisory form](https://github.com/lalalune/daosfun-source/security/advisories/new).
If you cannot access the form, contact the maintainer through a verified private
channel before sharing live exploit details. Do not publish private keys, credentials,
customer data, or transactions intended to exploit a live deployment in an issue.

Include the artifact SHA-256, affected entrypoint, prerequisites, expected and
observed behavior, and a minimal local reproduction with a negative control.
Distinguish a source-level hypothesis from a finding reproduced against the
captured original. Do not interact with real user funds to demonstrate impact.

## Support boundary

There is no supported production release or deployed remediation in this repository.
The [earlier remediation review](audit/PRIOR_PATCH_REVIEW.md) documents a separate
experiment and unresolved gaps. The [scope document](docs/SECURITY_SCOPE.md) records
what was reviewed and what remains outside these tests.
