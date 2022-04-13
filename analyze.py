#!/usr/bin/env python3
"""Analyze a GitHub PR with Phylum.

States on returncode:
0 = No comment
1 = FAILED_COMMENT
5 = INCOMPLETE_COMMENT then:
    4 = COMPLETE_SUCCESS_COMMENT
    1 = COMPLETE_FAILED_COMMENT
"""
import json
import os
import pathlib
import re
import sys
from subprocess import run

from packaging.utils import parse_sdist_filename, parse_wheel_filename
from unidiff import PatchSet

import parse_yarn

ENV_KEYS = [
    "GITHUB_SHA",  # for get_PR_diff; this is the SHA of the commit for the branch being merged
    "GITHUB_BASE_REF",  # for get_PR_diff; this is the target branch of the merge
    "GITHUB_WORKSPACE",  # for get_PR_diff; this is where the Pull Request code base is
]

FILE_PATHS = {
    "pr_type": "/home/runner/prtype.txt",
    "phylum_analysis": "/home/runner/phylum_analysis.json",
    "returncode": "/home/runner/returncode.txt",
    "pr_comment": "/home/runner/pr_comment.txt",
}

# Headers for distinct comment types
DETAILS_DROPDOWN = "<details>\n<summary>Background</summary>\n<br />\nThis repository uses a GitHub Action to automatically analyze the risk of new dependencies added via Pull Request. An administrator of this repository has set score requirements for Phylum's five risk domains.<br /><br />\nIf you see this comment, one or more dependencies added to the package manager lockfile in this Pull Request have failed Phylum's risk analysis.\n</details>\n\n"

INCOMPLETE_COMMENT = "## Phylum OSS Supply Chain Risk Analysis - INCOMPLETE\n\n"
INCOMPLETE_COMMENT += "This pull request contains TKTK package versions Phylum has not yet processed, preventing a complete risk analysis. Phylum is processing these packages currently and should complete within 30 minutes. Please wait for at least 30 minutes, then re-run the GitHub Check pertaining to `phylum-analyze-pr-action`.\n\n"
INCOMPLETE_COMMENT += DETAILS_DROPDOWN

COMPLETE_FAILED_COMMENT = "## Phylum OSS Supply Chain Risk Analysis - COMPLETE\n\n"
COMPLETE_FAILED_COMMENT += "The Phylum risk analysis is now complete.\n\n"
COMPLETE_FAILED_COMMENT += DETAILS_DROPDOWN

COMPLETE_SUCCESS_COMMENT = "## Phylum OSS Supply Chain Risk Analysis - COMPLETE\n\n"
COMPLETE_SUCCESS_COMMENT += "The Phylum risk analysis is now complete and did not identify any issues for this PR.\n\n"
COMPLETE_SUCCESS_COMMENT += DETAILS_DROPDOWN

FAILED_COMMENT = "## Phylum OSS Supply Chain Risk Analysis\n\n"
FAILED_COMMENT += DETAILS_DROPDOWN


class AnalyzePRForReqs:
    def __init__(self, repo, pr_num, vul, mal, eng, lic, aut):
        self.repo = repo
        self.pr_num = pr_num
        self.vul = float(vul)
        self.mal = float(mal)
        self.eng = float(eng)
        self.lic = float(lic)
        self.aut = float(aut)
        self.gbl_failed = False
        self.gbl_incomplete = False
        self.incomplete_pkgs = list()
        self.previous_incomplete = False
        self.env = dict()
        self.get_env_vars()

    def get_env_vars(self):
        for key in ENV_KEYS:
            temp = os.environ.get(key)
            if temp is not None:
                self.env[key] = temp
            else:
                print(
                    f"[ERROR] could not get value for required env variable os.environ.get({key})"
                )
                sys.exit(11)
        if os.environ.get("PREVIOUS_INCOMPLETE"):
            self.previous_incomplete = True
        return

    def new_get_pr_diff(self):
        target_branch = self.env.get("GITHUB_BASE_REF")
        diff_target = f"origin/{target_branch}"

        github_workspace = self.env.get("GITHUB_WORKSPACE")
        prev = os.getcwd()
        os.chdir(github_workspace)

        git_fetch_res = run("git fetch origin".split(" "))
        if git_fetch_res.returncode != 0:
            print("[ERROR] failed to git fetch origin")
            sys.exit(11)

        cmd = [
            "git",
            "diff",
            diff_target,
        ]
        result = run(cmd, capture_output=True)
        if result.returncode != 0:
            print("[ERROR] failed to git diff")
            sys.exit(11)

        os.chdir(prev)
        return result.stdout

    def determine_pr_type(self, diff_data):
        """Determine which changes are present in the diff.

        If more than one package manifest file has been changed, fail as we can't be sure which Phylum project to
        analyze against. Supported package dependency / lock files include:

        * Python
          * requirements.txt
          * poetry.lock
        * Javascript
          * yarn.lock
          * package-lock.json
        * Ruby
          * Gemfile.lock
        """
        patches = PatchSet(diff_data.decode("utf-8"))
        pr_type = None

        for patchfile in patches:
            # TODO: add poetry.lock
            if "requirements.txt" in patchfile.path:
                if not pr_type:
                    pr_type = "requirements.txt"
                else:
                    if pr_type != "requirements.txt":
                        print(
                            "[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset"
                        )
            if "poetry.lock" in patchfile.path:
                if not pr_type:
                    pr_type = "poetry.lock"
                else:
                    if pr_type != "poetry.lock":
                        print(
                            "[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset"
                        )
            if "yarn.lock" in patchfile.path:
                if not pr_type:
                    pr_type = "yarn.lock"
                else:
                    if pr_type != "yarn.lock":
                        print(
                            "[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset"
                        )
            if "package-lock.json" in patchfile.path:
                if not pr_type:
                    pr_type = "package-lock.json"
                else:
                    if pr_type != "package-lock.json":
                        print(
                            "[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset"
                        )
            if "Gemfile.lock" in patchfile.path:
                if not pr_type:
                    pr_type = "Gemfile.lock"
                else:
                    if pr_type != "Gemfile.lock":
                        print(
                            "[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset"
                        )

        print(f"[DEBUG] pr_type: {pr_type}")
        return pr_type

    def get_diff_hunks(self, diff_data, pr_type):
        """Build a list of changes from diff hunks based on the PR_TYPE."""
        patches = PatchSet(diff_data.decode("utf-8"))

        changes = list()
        for patchfile in patches:
            if pr_type in patchfile.path:
                for hunk in patchfile:
                    for line in hunk:
                        if line.is_added:
                            changes.append(line.value)
        print(f"[DEBUG] get_reqs_hunks: found {len(changes)} changes for {pr_type}")
        return changes

    def parse_package_lock(self, changes):
        """Parse package-lock.json diff to generate a list of tuples of (package_name, version)."""
        cur = 0
        name_pat = re.compile(r".*\"(.*?)\": \{")
        version_pat = re.compile(r".*\"version\": \"(.*?)\"")
        resolved_pat = re.compile(r".*\"resolved\": \"(.*?)\"")
        pkg_ver = list()

        while cur < len(changes) - 2:
            name_match = re.match(name_pat, changes[cur])
            if version_match := re.match(version_pat, changes[cur + 1]):
                if resolved_match := re.match(resolved_pat, changes[cur + 2]):
                    name = name_match.groups()[0]
                    ver = version_match.groups()[0]
                    pkg_ver.append((name, ver))
            cur += 1

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    def parse_yarn_lock(self, changes):
        """Parse yarn.lock diff to generate a list of tuples of (package_name, version)."""
        pkg_ver = parse_yarn.parse_yarn_lock_changes(changes)
        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    def parse_gemfile_lock(self, changes):
        cur = 0
        name_ver_pat = re.compile(r"\s{4}(.*?)\ \((.*?)\)")
        pkg_ver = list()

        while cur < len(changes):
            if name_ver_match := re.match(name_ver_pat, changes[cur]):
                name = name_ver_match.groups()[0]
                ver = name_ver_match.groups()[1]
                pkg_ver.append((name, ver))
            cur += 1

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    def parse_requirements_txt(self, changes):
        cur = 0
        name_ver_pat = re.compile(r"(.*)==(.*)")
        pkg_ver = list()

        while cur < len(changes):
            if name_ver_match := re.match(name_ver_pat, changes[cur]):
                name = name_ver_match.groups()[0]
                ver = name_ver_match.groups()[1]
                pkg_ver.append((name, ver))
            cur += 1

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    def parse_poetry_lock(self, changes):
        """Parse lines added to a poetry.lock file to identify package names and versions."""
        file_name_pat = re.compile(
            r"""^       # match beginning of string
            \s{4}       # start with four spaces
            {file       # start of the mapping for a file
            \s=\s       # whitespace separated mapping assignment operator
            "(.*?)"     # non-greedy capture group for the file name
            """,
            re.VERBOSE,
        )
        pkg_ver = set()

        for change in changes:
            if pattern_match := re.match(file_name_pat, change):
                filename = pattern_match.groups()[0]
                if filename.endswith(".tar.gz"):
                    name, ver = parse_sdist_filename(filename)
                    pkg_ver.add((name, str(ver)))
                elif filename.endswith(".whl"):
                    name, ver, *_ = parse_wheel_filename(filename)
                    pkg_ver.add((name, str(ver)))

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return list(pkg_ver)

    def generate_pkgver(self, changes, pr_type):
        """Parse dependency file to generate a list of tuples of (package_name, version)."""
        if pr_type == "requirements.txt":
            return self.parse_requirements_txt(changes)
        if pr_type == "poetry.lock":
            return self.parse_poetry_lock(changes)
        if pr_type == "yarn.lock":
            return self.parse_yarn_lock(changes)
        if pr_type == "package-lock.json":
            return self.parse_package_lock(changes)
        if pr_type == "Gemfile.lock":
            return self.parse_gemfile_lock(changes)
        return None

    def read_phylum_analysis(self, filename):
        """Read phylum_analysis.json file."""
        if not pathlib.Path(filename).is_file():
            print(f"[ERROR] Cannot find {filename}")
            sys.exit(11)
        with open(filename, "r", encoding="utf-8") as infile:
            data = infile.read()
            phylum_analysis_json = json.loads(data)
        print(f"[DEBUG] phylum_analysis: read {len(data)} bytes")
        return phylum_analysis_json

    def parse_risk_data(self, phylum_json, pkg_ver):
        """Parse risk packages in phylum_analysis.json file.

        Packages that are in a completed analysis state will be included in the risk score report.
        Packages that have not completed analysis will be included with other incomplete packages
        and the overall PR will be allowed to pass, but with a note about re-running again later.
        """
        phylum_pkgs = phylum_json.get("packages")
        risk_scores = list()
        for pkg, ver in pkg_ver:
            for phylum_pkg in phylum_pkgs:
                if phylum_pkg.get("name") == pkg and phylum_pkg.get("version") == ver:
                    if phylum_pkg.get("status") == "complete":
                        risk_scores.append(self.check_risk_scores(phylum_pkg))
                    elif phylum_pkg.get("status") == "incomplete":
                        self.incomplete_pkgs.append((pkg, ver))
                        self.gbl_incomplete = True

        return risk_scores

    def check_risk_scores(self, package_json):
        """Check risk scores of a package against user-provided thresholds.

        If a package has a risk score below the threshold, set the fail bit and
        Generate the markdown output for pr_comment.txt
        """
        riskvectors = package_json.get("riskVectors")
        failed_flag = 0
        issue_flags = list()
        fail_string = f"### Package: `{package_json.get('name')}@{package_json.get('version')}` failed.\n"
        fail_string += "|Risk Domain|Identified Score|Requirement|\n"
        fail_string += "|-----------|----------------|-----------|\n"

        pkg_vul = riskvectors.get("vulnerability")
        pkg_mal = riskvectors.get("malicious_code")
        pkg_eng = riskvectors.get("engineering")
        pkg_lic = riskvectors.get("license")
        pkg_aut = riskvectors.get("author")
        if pkg_vul <= self.vul:
            failed_flag = 1
            issue_flags.append("vul")
            fail_string += f"|Software Vulnerability|{pkg_vul*100}|{self.vul*100}|\n"
        if pkg_mal <= self.mal:
            failed_flag = 1
            issue_flags.append("mal")
            fail_string += f"|Malicious Code|{pkg_mal*100}|{self.mal*100}|\n"
        if pkg_eng <= self.eng:
            failed_flag = 1
            issue_flags.append("eng")
            fail_string += f"|Engineering|{pkg_eng*100}|{self.eng*100}|\n"
        if pkg_lic <= self.lic:
            failed_flag = 1
            issue_flags.append("lic")
            fail_string += f"|License|{pkg_lic*100}|{self.lic*100}|\n"
        if pkg_aut <= self.aut:
            failed_flag = 1
            issue_flags.append("aut")
            fail_string += f"|Author|{pkg_aut*100}|{self.aut*100}|\n"

        fail_string += "\n"
        fail_string += "#### Issues Summary\n"
        fail_string += "|Risk Domain|Risk Level|Title|\n"
        fail_string += "|-----------|----------|-----|\n"

        issue_list = self.build_issues_list(package_json, issue_flags)
        for rd, rl, title in issue_list:
            fail_string += f"|{rd}|{rl}|{title}|\n"

        if failed_flag:
            self.gbl_failed = True
            return fail_string
        else:
            return None

    def build_issues_list(self, package_json, issue_flags: list):
        issues = list()
        pkg_issues = package_json.get("issues")

        for flag in issue_flags:
            for pkg_issue in pkg_issues:
                if flag in pkg_issue.get("risk_domain"):
                    risk_domain = pkg_issue.get("risk_domain")
                    risk_level = pkg_issue.get("risk_level")
                    title = pkg_issue.get("title")
                    issues.append((risk_domain, risk_level, title))

        return issues

    def get_project_url(self, phylum_json):
        project_id = phylum_json.get("project")
        url = f"https://app.phylum.io/projects/{project_id}"
        return url

    def run_prtype(self):
        diff_data = self.new_get_pr_diff()
        pr_type = self.determine_pr_type(diff_data)
        if pr_type is None:
            pr_type = "NA"
        with open(FILE_PATHS.get("pr_type"), "w", encoding="utf-8") as outfile:
            outfile.write(pr_type)
        sys.exit(0)

    def run_analyze(self):
        diff_data = self.new_get_pr_diff()
        pr_type = self.determine_pr_type(diff_data)
        changes = self.get_diff_hunks(diff_data, pr_type)
        pkg_ver = self.generate_pkgver(changes, pr_type)
        phylum_json = self.read_phylum_analysis(FILE_PATHS.get("phylum_analysis"))
        risk_data = self.parse_risk_data(phylum_json, pkg_ver)
        project_url = self.get_project_url(phylum_json)
        returncode = 0

        output = ""
        # Write pr_comment.txt only if the analysis failed and all pkgvers are completed
        if self.gbl_failed and not self.gbl_incomplete:
            returncode = 1
            # if this is a repeated test of previously incomplete packages,
            # set the comment based on states of failed, not incomplete and previous
            if self.previous_incomplete:
                output = COMPLETE_FAILED_COMMENT
            else:
                output = FAILED_COMMENT

            # write data from risk analysis
            for line in risk_data:
                if line:
                    output += line

        # If any packages are incomplete, add 5 to the returncode so we know the results are incomplete
        if self.gbl_incomplete:
            returncode = 5
            print(
                f"[DEBUG] {len(self.incomplete_pkgs)} packages were incomplete as of the analysis job"
            )
            output = INCOMPLETE_COMMENT.replace("TKTK", str(len(self.incomplete_pkgs)))

        if not self.gbl_failed and not self.gbl_incomplete and self.previous_incomplete:
            returncode = 4
            print("[DEBUG] failed=False incomplete=False previous_incomplete=True")
            output = COMPLETE_SUCCESS_COMMENT

        with open(FILE_PATHS.get("returncode"), "w", encoding="utf-8") as resultout:
            resultout.write(str(returncode))
            print(f"[DEBUG] returncode: wrote {str(returncode)}")

        with open(FILE_PATHS.get("pr_comment"), "w", encoding="utf-8") as outfile:
            outfile.write(output)
            outfile.write(f"\n[View this project in Phylum UI]({project_url})")
            print(f"[DEBUG] pr_comment.txt: wrote {outfile.tell()} bytes")


if __name__ == "__main__":
    argv = sys.argv

    if argc := len(sys.argv) < 4:
        print(
            f"Usage: {argv[0]} ACTION:(analyze|pr_type) GITHUB_REPOSITORY PR_NUM VUL_THRESHOLD MAL_THRESHOLD ENG_THRESHOLD LIC_THRESHOLD AUT_THRESHOLD"
        )
        sys.exit(11)

    action = argv[1]
    repo = argv[2]
    pr_num = argv[3]
    if action == "pr_type":
        a = AnalyzePRForReqs(repo, pr_num, 0, 0, 0, 0, 0)
        a.run_prtype()
    vul = argv[4]
    mal = argv[5]
    eng = argv[6]
    lic = argv[7]
    aut = argv[8]

    a = AnalyzePRForReqs(repo, pr_num, vul, mal, eng, lic, aut)
    a.run_analyze()
