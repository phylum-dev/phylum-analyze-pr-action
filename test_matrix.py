#!/usr/bin/env python
"""Test matrix for validating various phylum analysis output results.

Return Codes:
0 = FAIL
1 = INCOMPLETE
2 = COMPLETE_FAIL
3 = COMPLETE_SUCCESS
4 = SUCCESS
"""

import hashlib
import os
import shutil
from pathlib import Path

ENV_KEYS = [
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_RUN_ID",
]

GHAP = os.environ.get("GITHUB_ACTION_PATH")

FILES = {
    "FAIL_FILE": Path(GHAP + "/testing/fail_phylum.json").resolve(),
    "INCOMPLETE_FILE": Path(GHAP + "/testing/incomplete_phylum.json").resolve(),
    "COMPLETE_FAIL_FILE": Path(GHAP + "/testing/complete_fail_phylum.json").resolve(),
    "COMPLETE_SUCCESS_FILE": Path(
        GHAP + "/testing/complete_success_phylum.json"
    ).resolve(),
    "SUCCESS_FILE": Path(GHAP + "/testing/success_phylum.json").resolve(),
}


class TestMatrix:
    def __init__(self):
        self.env = dict()
        self.get_env_vars()

    def get_env_vars(self):
        for key in ENV_KEYS:
            temp = os.environ.get(key)
            if temp is not None:
                self.env[key] = temp

    def swap_phylum_file(self, filename):
        file = FILES.get(filename)
        home = Path.home()
        dest = home.joinpath("phylum_analysis.json")
        print(f"Copying file from {file} to {dest}")
        shutil.copy(file, dest)

        md5 = hashlib.md5(open(dest, "rb").read()).hexdigest()
        print(f"MD5 of target: {md5}")

    def run(self):
        state = int(self.env.get("GITHUB_RUN_ATTEMPT")) % 5
        print(f"state: {state}")
        if state == 0:
            self.swap_phylum_file("FAIL_FILE")
        elif state == 1:
            self.swap_phylum_file("INCOMPLETE_FILE")
        if state == 2:
            self.swap_phylum_file("COMPLETE_FAIL_FILE")
        if state == 3:
            self.swap_phylum_file("COMPLETE_SUCCESS_FILE")
        if state == 4:
            self.swap_phylum_file("SUCCESS_FILE")


if __name__ == "__main__":
    tm = TestMatrix()
    tm.run()
