# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
