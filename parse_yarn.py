#!/usr/bin/env python3

import re
import sys
from pathlib import Path


def search(pkg_ver, search):
    for a, b in pkg_ver:
        if search in a:
            print(f"({a},{b})")


def parse_yarnpkg(line: str):
    ret_str = ""
    # resolved "https://registry.yarnpkg.com/window-size/-/window-size-0.1.0.tgz#5438cd2ea93b202efa3a19fe8887aee7c94f9c9d"
    if "yarnpkg.com" in line:
        line = line.replace("https://registry.yarnpkg.com/", "")
        yarnpkg_match = re.match(r"(.*?)(?=/)", line)
        ret_str = yarnpkg_match.group()

    # resolved "https://registry.npmjs.org/@types/styled-jsx/-/styled-jsx-2.2.8.tgz#b50d13d8a3c34036282d65194554cf186bab7234"
    elif "npmjs" in line:
        line = re.sub(r"https://registry.npmjs....", "", line)
        npmpkg_match = re.match(r"(.*?)(?=/)", line)
        ret_str = npmpkg_match.group()

    else:  # should only be npm
        print("[ERROR] yarn_parse:parse_yarnpkg found a registry link that is unknown")

    return ret_str


def parse_yarnv2_lock(changes):
    cur = 0
    name_pat = re.compile(r"[\"]?(@?.*?)(?=@).*:")
    version_pat = re.compile(r".*version: (.*)")
    resolved_pat = re.compile(r".*resolution: \"(.*?)\"")
    pkg_ver = list()

    while cur < len(changes) - 3:
        name_match = re.match(name_pat, changes[cur])
        if version_match := re.match(version_pat, changes[cur + 1]):
            if resolved_match := re.match(resolved_pat, changes[cur + 2]):
                if name_match:
                    name = name_match.groups()[0]
                else:
                    # print(f"No name - need to parse {resolved_match.groups()[0]}")
                    name = parse_yarnpkg(resolved_match.groups()[0])
                ver = version_match.groups()[0]
                pkg_ver.append((name, ver))
        cur += 1
    return pkg_ver


def parse_yarnv1_lock(changes):
    cur = 0
    name_pat = re.compile(r"[\"]?(@?.*?)(?=@).*:")
    version_pat = re.compile(r".*version \"(.*?)\"")
    resolved_pat = re.compile(r".*resolved \"(.*?)\"")
    integrity_pat = re.compile(r".*integrity.*")
    pkg_ver = list()

    # the parser breaks if the changeset only has 1 package upgraded from one version to another
    if (
        len(changes) < 4
    ):  # only 1 package was upgraded in the changeset that will trigger this
        if version_match := re.match(version_pat, changes[cur]):
            if resolved_match := re.match(resolved_pat, changes[cur + 1]):
                if integrity_match := re.match(integrity_pat, changes[cur + 2]):
                    name = parse_yarnpkg(resolved_match.groups()[0])
                    ver = version_match.groups()[0]
                    pkg_ver.append((name, ver))

    else:
        while cur < len(changes) - 3:
            name_match = re.match(name_pat, changes[cur])
            if version_match := re.match(version_pat, changes[cur + 1]):
                if resolved_match := re.match(resolved_pat, changes[cur + 2]):
                    if integrity_match := re.match(integrity_pat, changes[cur + 3]):
                        if name_match:
                            name = name_match.groups()[0]
                        else:
                            # print(f"No name - need to parse {resolved_match.groups()[0]}")
                            name = parse_yarnpkg(resolved_match.groups()[0])
                        ver = version_match.groups()[0]
                        pkg_ver.append((name, ver))
            cur += 1
    return pkg_ver


def parse_yarn_lock_changes(changes):
    lockfile_version = 1
    candidate_line = ""
    for line in changes:
        if "version" in line:
            candidate_line = line
            break
    if ":" in candidate_line:
        lockfile_version = 2

    if lockfile_version == 1:
        print("Parsed yarn v1 lockfile")
        return parse_yarnv1_lock(changes)
    else:
        print("Parsed yarn v2 lockfile")
        return parse_yarnv2_lock(changes)


def parse_yarn_lockfile(filename):
    """Take a file name and call the relevant yarn parser."""
    if not Path(filename).is_file():
        print("[ERROR] filename is not a file")
        sys.exit(1)

    with open(filename, "r") as infile:
        changes = infile.read().splitlines()
        lockfile_version = 1
        candidate_line = ""
        for line in changes:
            if "version" in line:
                candidate_line = line
                break
        if ":" in candidate_line:
            lockfile_version = 2

    if lockfile_version == 1:
        print("Parsed yarn v1 lockfile")
        return parse_yarnv1_lock(changes)
    else:
        print("Parsed yarn v2 lockfile")
        return parse_yarnv2_lock(changes)


if __name__ == "__main__":
    pkg_ver = parse_yarn_lockfile(sys.argv[1])
    print(f"Identified {len(pkg_ver)} packages")
