# Security Policy

## Supported Versions

| Package | Version | Supported |
|---------|---------|-----------|
| gds-framework | latest | Yes |
| gds-viz | latest | Yes |
| gds-games | latest | Yes |
| gds-stockflow | latest | Yes |
| gds-control | latest | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email **rohan@block.science** with details
3. Include steps to reproduce and potential impact
4. You will receive a response within 72 hours

## Security Measures

- Dependencies are monitored via [Dependabot](https://github.com/BlockScience/gds-core/security/dependabot)
- Code is scanned with [CodeQL](https://github.com/BlockScience/gds-core/security/code-scanning)
- CI runs `pip-audit` for known vulnerability detection
