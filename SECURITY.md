# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | Yes |
| <1.0 | No |

## Reporting

Do not disclose suspected vulnerabilities in a public issue. Contact the maintainers privately and
include the affected version, reproduction steps, impact and any proposed mitigation.

## Dependency hygiene

The repository runs `pip-audit` in CI, uses Dependabot for dependency updates, and builds only on
Python 3.13. Runtime input is treated as untrusted and validated before assessment.
