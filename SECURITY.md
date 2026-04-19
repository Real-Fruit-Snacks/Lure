# Security Policy

## Supported Versions

Only the latest release of Lure is supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest | :x:               |

## Reporting a Vulnerability

**Do NOT open public issues for security vulnerabilities.**

If you discover a security vulnerability in Lure, please report it responsibly:

1. **Preferred:** Use [GitHub Security Advisories](https://github.com/Real-Fruit-Snacks/Lure/security/advisories/new) to create a private report.
2. **Alternative:** Email the maintainers directly with details of the vulnerability.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment:** Within 48 hours of receipt
- **Assessment:** Within 7 days
- **Fix & Disclosure:** Within 90 days (coordinated responsible disclosure)

We follow a 90-day responsible disclosure timeline. If a fix is not released within 90 days, the reporter may disclose the vulnerability publicly.

## What is NOT a Vulnerability

Lure is an SMB coercion tool. The following behaviors are **features, not bugs**:

- Generating `.url`, `.scf`, and `.xml` payloads containing UNC paths
- Uploading payloads to user-specified SMB shares via `smbclient`
- Invoking `responder` to capture inbound NTLM authentication
- Accepting plaintext credentials via command-line flags for authenticated uploads
- Displaying color-coded terminal output

These capabilities exist by design for authorized red team engagements. Reports that simply describe Lure working as intended will be closed.

## Responsible Use

Lure is intended **exclusively** for authorized penetration testing, red team engagements, and security research. Users are responsible for ensuring they have explicit written authorization from the system owner before deploying payloads against any SMB share.

Unauthorized use against systems you do not own or do not have written permission to test is illegal in most jurisdictions and is not supported by the maintainers.
