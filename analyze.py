#!/usr/bin/env python3
import os
import sys
import json
import re
from unidiff import PatchSet
import pathlib
from subprocess import run
import parse_yarn

ENV_KEYS = [
    "GITHUB_SHA", # for get_PR_diff; this is the SHA of the commit for the branch being merged
    "GITHUB_BASE_REF", # for get_PR_diff; this is the target branch of the merge
    "GITHUB_WORKSPACE", # for get_PR_diff; this is where the Pull Request code base is
]

FILE_PATHS = {
    "pr_type": "/home/runner/prtype.txt",
    "phylum_analysis": "/home/runner/phylum_analysis.json",
    "returncode": "/home/runner/returncode.txt",
    "pr_comment": "/home/runner/pr_comment.txt",
}

'''
    States on returncode
    0 = No comment
    1 = FAILED_COMMENT
    5 = INCOMPLETE_COMMENT then:
        4 = COMPLETE_SUCCESS_COMMENT
        1 = COMPLETE_FAILED_COMMENT
'''

# Headers for distinct comment types
DETAILS_DROPDOWN = "<details>\n<summary>Background</summary>\n<br />\nThis repository uses a GitHub Action to automatically analyze the risk of new dependencies added to requirements.txt via Pull Request. An administrator of this repository has set score requirements for Phylum's five risk domains.<br /><br />\nIf you see this comment, one or more dependencies added to the package manager lockfile in this Pull Request have failed Phylum's risk analysis.\n</details>\n\n"

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
FAILED_COMMENT +=DETAILS_DROPDOWN



class AnalyzePRForReqs():
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
                print(f"[ERROR] could not get value for required env variable os.environ.get({key})")
                sys.exit(11)
        if os.environ.get("PREVIOUS_INCOMPLETE"):
            self.previous_incomplete = True
        return

    def new_get_PR_diff(self):
        pr_commit_sha = self.env.get("GITHUB_SHA")
        target_branch = self.env.get("GITHUB_BASE_REF")
        diff_target = f"origin/{target_branch}"

        github_workspace = self.env.get("GITHUB_WORKSPACE")
        prev = os.getcwd()
        os.chdir(github_workspace)

        git_fetch_res = run("git fetch origin".split(" "))
        if git_fetch_res.returncode != 0:
            print(f"[ERROR] failed to git fetch origin")
            sys.exit(11)

        cmd = [
            "git",
            "diff",
            diff_target,
        ]
        result = run(cmd, capture_output=True)
        if result.returncode != 0:
            print(f"[ERROR] failed to git diff")
            sys.exit(11)

        os.chdir(prev)
        return result.stdout


    ''' Determine which changes are present in the diff.
        If more than one package manifest file has been changed, fail as we can't be sure which Phylum project to analyze against '''
    def determine_pr_type(self, diff_data):
        patches = PatchSet(diff_data.decode('utf-8'))
        '''
        Types = [
            requirements.txt,
            yarn.lock,
            package-lock.json,
            poetry.lock, #?
        ]
        '''
        pr_type = None
        lang = None
        conflict = False

        changes = list()
        for patchfile in patches:
            # TODO: add poetry.lock
            if 'requirements.txt' in patchfile.path:
                if not pr_type:
                    pr_type = 'requirements.txt'
                    lang = 'python'
                else:
                    if pr_type != 'requirements.txt':
                        print(f"[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset")
            if 'yarn.lock' in patchfile.path:
                if not pr_type:
                    pr_type = 'yarn.lock'
                    lang = 'javascript'
                else:
                    if pr_type != 'yarn.lock':
                        print(f"[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset")
            if 'package-lock.json' in patchfile.path:
                if not pr_type:
                    pr_type = 'package-lock.json'
                    lang = 'javascript'
                else:
                    if pr_type != 'package-lock.json':
                        print(f"[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset")
            if 'Gemfile.lock' in patchfile.path:
                if not pr_type:
                    pr_type = 'Gemfile.lock'
                    lang = 'ruby'
                else:
                    if pr_type != 'Gemfile.lock':
                        print(f"[ERROR] PR contains changes from mulitple packaging systems - cannot determine changeset")

        print(f"[DEBUG] pr_type: {pr_type}")
        return pr_type


    ''' Build a list of changes from diff hunks based on the PR_TYPE '''
    def get_diff_hunks(self, diff_data, pr_type):
        patches = PatchSet(diff_data.decode('utf-8'))

        changes = list()
        for patchfile in patches:
            if pr_type in patchfile.path:
                for hunk in patchfile:
                    for line in hunk:
                        if line.is_added:
                            changes.append(line.value)
        print(f"[DEBUG] get_reqs_hunks: found {len(changes)} changes for {pr_type}")
        return changes

    ''' Parse package-lock.json diff to generate a list of tuples of (package_name, version) '''
    def parse_package_lock(self, changes):
        cur = 0
        name_pat        = re.compile(r".*\"(.*?)\": \{")
        version_pat     = re.compile(r".*\"version\": \"(.*?)\"")
        resolved_pat    = re.compile(r".*\"resolved\": \"(.*?)\"")
        pkg_ver = list()

        while cur < len(changes)-2:
            name_match = re.match(name_pat, changes[cur])
            if version_match := re.match(version_pat, changes[cur+1]):
                if resolved_match := re.match(resolved_pat, changes[cur+2]):
                    name = name_match.groups()[0]
                    ver = version_match.groups()[0]
                    pkg_ver.append((name,ver))
            cur +=1

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    ''' Parse yarn.lock diff to generate a list of tuples of (package_name, version) '''

    def parse_yarn_lock(self, changes):
        pkg_ver = parse_yarn.parse_yarn_lock_changes(changes)
        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver

    def parse_gemfile_lock(self, changes):
        cur = 0
        name_ver_pat        = re.compile(r"\s{4}(.*?)\ \((.*?)\)")
        pkg_ver = list()

        while cur < len(changes):
            if name_ver_match := re.match(name_ver_pat, changes[cur]):
                name = name_ver_match.groups()[0]
                ver = name_ver_match.groups()[1]
                pkg_ver.append((name,ver))
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
                pkg_ver.append((name,ver))
            cur += 1

        print(f"[DEBUG]: pkg_ver length: {len(pkg_ver)}")
        return pkg_ver


    ''' Parse requirements.txt to generate a list of tuples of (package_name, version) '''
    def generate_pkgver(self, changes, pr_type):
        if pr_type == 'requirements.txt':
            #  pat = re.compile(r"(.*)==(.*)")
            pkg_ver_tup = self.parse_requirements_txt(changes)
            return pkg_ver_tup
        elif pr_type == 'yarn.lock':
            pkg_ver_tup = self.parse_yarn_lock(changes)
            return pkg_ver_tup
        elif pr_type == 'package-lock.json':
            pkg_ver_tup = self.parse_package_lock(changes)
            return pkg_ver_tup
        elif pr_type == "Gemfile.lock":
            pkg_ver_tup = self.parse_gemfile_lock(changes)
            return pkg_ver_tup

        # shouldn't get here
        return pkg_ver_tup

    ''' Read phylum_analysis.json file '''
    def read_phylum_analysis(self, filename):
        if not pathlib.Path(filename).is_file():
            print(f"[ERROR] Cannot find {filename}")
            sys.exit(11)
        with open(filename,'r') as infile:
            data = infile.read()
            phylum_analysis_json = json.loads(data)
        print(f"[DEBUG] phylum_analysis: read {len(data)} bytes")
        return phylum_analysis_json

    ''' Parse risk packages in phylum_analysis.json
        Ensure packages are in "complete" state; If not, fail
        Call check_risk_scores on individual package data '''
    def parse_risk_data(self, phylum_json, pkg_ver):
        phylum_pkgs = phylum_json.get('packages')
        risk_scores = list()
        for pkg,ver in pkg_ver:
            for elem in phylum_pkgs:
                if elem.get('name') == pkg and elem.get('version') == ver:
                    if elem.get('status') == 'complete':
                        risk_scores.append(self.check_risk_scores(elem))
                    elif elem.get('status') == 'incomplete':
                        self.incomplete_pkgs.append((pkg,ver))
                        self.gbl_incomplete = True

        return risk_scores

    ''' Check risk scores of a package against user-provided thresholds
        If a package has a risk score below the threshold, set the fail bit and
            Generate the markdown output for pr_comment.txt '''
    def check_risk_scores(self, package_json):
        riskvectors = package_json.get('riskVectors')
        failed_flag = 0
        vuln_flag = 0
        issue_flags = list()
        fail_string = f"### Package: `{package_json.get('name')}@{package_json.get('version')}` failed.\n"
        fail_string += f"|Risk Domain|Identified Score|Requirement|\n"
        fail_string += f"|-----------|----------------|-----------|\n"


        pkg_vul = riskvectors.get('vulnerability')
        pkg_mal = riskvectors.get('malicious_code')
        pkg_eng = riskvectors.get('engineering')
        pkg_lic = riskvectors.get('license')
        pkg_aut = riskvectors.get('author')
        if pkg_vul <= self.vul:
            failed_flag = 1
            vuln_flag = 1
            issue_flags.append('vul')
            fail_string += f"|Software Vulnerability|{pkg_vul*100}|{self.vul*100}|\n"
        if pkg_mal <= self.mal:
            failed_flag = 1
            issue_flags.append('mal')
            fail_string += f"|Malicious Code|{pkg_mal*100}|{self.mal*100}|\n"
        if pkg_eng <= self.eng:
            failed_flag = 1
            issue_flags.append('eng')
            fail_string += f"|Engineering|{pkg_eng*100}|{self.eng*100}|\n"
        if pkg_lic <= self.lic:
            failed_flag = 1
            issue_flags.append('lic')
            fail_string += f"|License|{pkg_lic*100}|{self.lic*100}|\n"
        if pkg_aut <= self.aut:
            failed_flag = 1
            issue_flags.append('aut')
            fail_string += f"|Author|{pkg_aut*100}|{self.aut*100}|\n"

        fail_string += "\n"
        fail_string += "#### Issues Summary\n"
        fail_string += f"|Risk Domain|Risk Level|Title|\n"
        fail_string += f"|-----------|----------|-----|\n"

        issue_list = self.build_issues_list(package_json, issue_flags)
        for rd,rl,title in issue_list:
            fail_string += f"|{rd}|{rl}|{title}|\n"

        #  return fail_string if failed_flag else None
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
        diff_data = self.new_get_PR_diff()
        pr_type = self.determine_pr_type(diff_data)
        if pr_type is None:
            pr_type = "NA"
        # with open('/home/runner/prtype.txt','w') as outfile:
        with open(FILE_PATHS.get("pr_type"),'w') as outfile:
            outfile.write(pr_type)
        sys.exit(0)

    def run_analyze(self):
        diff_data = self.new_get_PR_diff()
        pr_type = self.determine_pr_type(diff_data)
        changes = self.get_diff_hunks(diff_data, pr_type)
        pkg_ver = self.generate_pkgver(changes, pr_type)
        phylum_json = self.read_phylum_analysis(FILE_PATHS.get("phylum_analysis"))
        risk_data = self.parse_risk_data(phylum_json, pkg_ver)
        project_url = self.get_project_url(phylum_json)
        returncode = 0

        output = ""
        # Write pr_comment.txt only if the analysis failed and all pkgvers are completed(self.gbl_result == 1)
        if self.gbl_failed == True and self.gbl_incomplete == False:
            returncode = 1
            # if this is a repeated test of previously incomplete packages, set the comment based on states of failed, not incomplete and previous
            if self.previous_incomplete == True:
                output = COMPLETE_FAILED_COMMENT
            else:
                output = FAILED_COMMENT

            # write data from risk analysis
            for line in risk_data:
                if line:
                    output += line

        # If any packages are incomplete, add 5 to the returncode so we know the results are incomplete
        if self.gbl_incomplete == True:
            returncode = 5
            print(f"[DEBUG] {len(self.incomplete_pkgs)} packages were incomplete as of the analysis job")
            output = INCOMPLETE_COMMENT.replace("TKTK",str(len(self.incomplete_pkgs)))

        if self.gbl_failed == False and self.gbl_incomplete == False and self.previous_incomplete == True:
            returncode = 4
            print(f"[DEBUG] failed=False incomplete=False previous_incomplete=True")
            output = COMPLETE_SUCCESS_COMMENT

        with open(FILE_PATHS.get("returncode"),'w') as resultout:
            resultout.write(str(returncode))
            print(f"[DEBUG] returncode: wrote {str(returncode)}")

        with open(FILE_PATHS.get("pr_comment"),'w') as outfile:
            outfile.write(output)
            outfile.write(f"\n[View this project in Phylum UI]({project_url})")
            print(f"[DEBUG] pr_comment.txt: wrote {outfile.tell()} bytes")

if __name__ == "__main__":
    argv = sys.argv

    if argc := len(sys.argv) < 4:
        print(f"Usage: {argv[0]} ACTION:(analyze|pr_type) GITHUB_REPOSITORY PR_NUM VUL_THRESHOLD MAL_THRESHOLD ENG_THRESHOLD LIC_THRESHOLD AUT_THRESHOLD")
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
