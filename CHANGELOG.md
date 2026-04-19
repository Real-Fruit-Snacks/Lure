# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-04-19

### Added

- `--version` / `-V` flag reports the package version.
- Startup prerequisite check verifies `smbclient` and `responder` are on `$PATH` and exits 4 with an `apt install` hint if either is missing.
- `--name <base>` sets a custom payload basename, letting operators move away from the literal `@lure` filenames that share telemetry may flag.
- `--no-responder` drops the payload and exits, for use when a listener is already running elsewhere or when relaying via a separate tool.
- `--cleanup` deletes previously dropped payloads from the share (uses the same payload-type and `--name` flags). Implies `--no-responder`.
- `--ask-pass` prompts for the password interactively (no echo).
- `$LURE_PASSWORD` environment variable consulted when `-P` is absent. Resolution order: `-P` > `$LURE_PASSWORD` > interactive prompt.

### Changed

- Uploads now run through `subprocess.run([...])` with argv lists instead of `os.system()` with string interpolation. User-supplied values can no longer be interpreted as shell metacharacters.
- Multiple payload flags (e.g. `-u -s`) now upload in a single `smbclient` session and trigger Responder once, instead of starting Responder repeatedly between uploads.
- Payload templates are written via `Path.write_text` with proper line endings — no more double newlines from mixed `\n` + source newlines.
- Username without a resolvable password now exits 2 instead of warning and silently sending an unauthenticated request.
- Argparse help text gains metavars and descriptive strings for every flag.

### Fixed

- Triple-upload bug: when both `-U/-P` and `-o` were set, the payload could be uploaded up to three times in a single run because the upload helpers used independent `if` blocks instead of `if/elif/else`.
- Broken nested-path quoting: the old `smbclient -c` script for nested uploads (`"; cd 'subdir' ; put ..."`) was malformed and silently failed on most shares.
- Missing auth in nested mode: `-U`/`-P` credentials were dropped when `-o` was used, so authenticated uploads could never target a subdirectory.

## [1.0.0] — 2026-04-19

Initial release.

### Added

- Three coercion payload generators: `@lure.url`, `@lure.scf`, `@lure.xml`
- `-A` / `--All` flag drops all three payloads in a single `smbclient` session
- Three upload modes: anonymous, authenticated (`DOMAIN/USER%PASS`), and nested subdirectory (`-o`)
- Automatic handoff to Responder on a user-specified interface
- Catppuccin Mocha terminal palette with 24-bit ANSI escapes
- `pipx` / `pip` installable Python package with `lure` console script entry point
- GitHub Pages landing site at [real-fruit-snacks.github.io/Lure](https://real-fruit-snacks.github.io/Lure/)
