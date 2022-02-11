#!/usr/bin/env python

import os
import sys
from pathlib import Path
import shutil
import hashlib

ENV_KEYS = [
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_RUN_ID",
]

FILES = {
    "FAIL_FILE": Path("./testing/fail_phylum.json"),
    "INCOMPLETE_FILE": Path("./testing/incomplete_phylum.json"),
    "COMPLETE_FAIL_FILE": Path("./testing/complete_fail_phylum.json"),
    "COMPLETE_SUCCESS_FILE": Path("./testing/complete_success_phylum.json"),
    "SUCCESS_FILE": Path("./testing/success_phylum.json"),
}

'''
0 = FAIL
1 = INCOMPLETE
2 = COMPLETE_FAIL
3 = COMPLETE_SUCCESS
4 = SUCCESS
'''

class TestMatrix:
    def __init__(self):
        self.env = dict()
        self.get_env_vars()

    def get_env_vars(self):
        for key in ENV_KEYS:
            temp = os.environ.get(key)
            if temp is not None:
                self.env[key] = temp

    def swap_phylum_file(self,filename):
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
