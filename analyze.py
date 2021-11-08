#!/usr/bin/env python3
import os
import sys
import requests
import json
import re
from unidiff import PatchSet
import pathlib

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


    ''' Get the diff output from GitHub's patch-diff endpoint. We use this to understand the changed files and packages '''
    def get_PR_diff(self):
        repo = self.repo
        if '_' in repo:
            repo = repo.replace('_','-')
        url = f"https://patch-diff.githubusercontent.com/raw/{repo}/pull/{self.pr_num}.diff"
        try:
            resp = requests.get(url)
        except Exception as e:
            print(f"[ERROR] Couldn't get patch diff via url")
            sys.exit(11)
        print(f"[DEBUG] get_PR_diff: [{resp.status_code} - {len(resp.content)}]")
        return resp.content


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
        return pkg_ver

    ''' Parse yarn.lock diff to generate a list of tuples of (package_name, version) '''
    def parse_yarn_lock(self, changes):
        cur = 0
        name_pat        = re.compile(r"(.*?)@.*:")
        version_pat     = re.compile(r".*version \"(.*?)\"")
        resolved_pat    = re.compile(r".*resolved \"(.*?)\"")
        integrity_pat   = re.compile(r".*integrity.*")
        pkg_ver = list()

        while cur < len(changes)-3:
            name_match = re.match(name_pat, changes[cur])
            if version_match := re.match(version_pat, changes[cur+1]):
                if resolved_match := re.match(resolved_pat, changes[cur+2]):
                    if integrity_match := re.match(integrity_pat, changes[cur+3]):
                        name = name_match.groups()[0]
                        ver = version_match.groups()[0]
                        pkg_ver.append((name,ver))
            cur += 1
        return pkg_ver

    ''' Parse requirements.txt to generate a list of tuples of (package_name, version) '''
    def generate_pkgver(self, changes, pr_type):
        if pr_type == 'requirements.txt':
            pat = re.compile(r"(.*)==(.*)")
        elif pr_type == 'yarn.lock':
            pkg_ver_tup = self.parse_yarn_lock(changes)
            return pkg_ver_tup
        elif pr_type == 'package-lock.json':
            pkg_ver_tup = self.parse_package_lock(changes)
            return pkg_ver_tup

        no_version = 0
        pkg_ver = dict()
        pkg_ver_tup = list()

        for line in changes:
            if line == '\n':
                continue
            if match := re.match(pat, line):
                pkg,ver = match.groups()
                pkg_ver[pkg] = ver
                pkg_ver_tup.append((pkg,ver))
            else:
                no_version += 1

        if no_version > 0:
            print(f"[ERROR] Found entries that do not specify version, preventing analysis. Exiting")
            sys.exit(11)

        return pkg_ver_tup

    ''' Read phylum_analysis.json file '''
    def read_phylum_analysis(self, filename='/home/runner/phylum_analysis.json'):
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

    #TODO: generalize this
    def build_issues_list(self, package_json, issue_flags: list):
        issues = list()
        pkg_issues = package_json.get("issues")
        pkg_vulns = package_json.get("vulnerabilities")

        if 'vul' in issue_flags:
            for vuln in pkg_vulns:
                risk_level = vuln.get("risk_level")
                title = vuln.get("title")
                issues.append(('VUL', risk_level,title))

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
        diff_data = self.get_PR_diff()
        pr_type = self.determine_pr_type(diff_data)
        with open('/home/runner/prtype.txt','w') as outfile:
            outfile.write(pr_type)
        sys.exit(0)

    def run_analyze(self):
        diff_data = self.get_PR_diff()
        pr_type = self.determine_pr_type(diff_data)
        changes = self.get_diff_hunks(diff_data, pr_type)
        pkg_ver = self.generate_pkgver(changes, pr_type)
        phylum_json = self.read_phylum_analysis('/home/runner/phylum_analysis.json')
        risk_data = self.parse_risk_data(phylum_json, pkg_ver)
        project_url = self.get_project_url(phylum_json)
        returncode = 0

        # Write pr_comment.txt only if the analysis failed (self.gbl_result == 1)
        if self.gbl_failed:
            returncode += 1

            header = "## Phylum OSS Supply Chain Risk Analysis\n\n"
            header += "<details>\n<summary>Background</summary>\n<br />\nThis repository uses a GitHub Action to automatically analyze the risk of new dependencies added to requirements.txt via Pull Request. An administrator of this repository has set score requirements for Phylum's five risk domains.<br /><br />\nIf you see this comment, one or more dependencies added to the requirements.txt file in this Pull Request have failed Phylum's risk analysis.\n</details>\n\n"

            with open('/home/runner/pr_comment.txt','w') as outfile:
                outfile.write(header)
                for line in risk_data:
                    if line:
                        outfile.write(line)
                outfile.write(f"\n[View this project in Phylum UI]({project_url})")
                print(f"[DEBUG] pr_comment.txt: wrote {outfile.tell()} bytes")
        # If any packages are incomplete, add 5 to the returncode so we know the results are incomplete
        if self.gbl_incomplete == True:
            print(f"[DEBUG] {len(self.incomplete_pkgs)} packages were incomplete as of the analysis job")
            returncode += 5

        with open('/home/runner/returncode.txt','w') as resultout:
            resultout.write(str(returncode))
            print(f"[DEBUG] returncode: wrote {str(returncode)}")



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