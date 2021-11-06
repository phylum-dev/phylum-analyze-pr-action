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
        #  self.owner = owner
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


    def get_PR_diff(self):
        #  resp = requests.get('https://patch-diff.githubusercontent.com/raw/peterjmorgan/phylum-demo/pull/7.diff')
        repo = self.repo
        if '_' in repo:
            repo = repo.replace('_','-')
        url = f"https://patch-diff.githubusercontent.com/raw/{repo}/pull/{self.pr_num}.diff"
        try:
            resp = requests.get(url)
        except Exception as e:
            print(f"[ERROR] Couldn't get patch diff via url")
            sys.exit(11)
        print(f"[D] get_PR_diff - resp.status_code: {resp.status_code}")
        return resp.content


# get the diff hunks
    def get_reqs_hunks(self, diff_data):
        patches = PatchSet(diff_data.decode('utf-8'))

        changes = list()
        for patchfile in patches:
            # TODO: check other files
            if 'requirements.txt' in patchfile.path:
                for hunk in patchfile:
                    for line in hunk:
                        if line.is_added:
                            changes.append(line.value)
        print(f"[DEBUG] get_reqs_hunks: found {len(changes)} changes")
        return changes

    def generate_pkgver(self, changes):
        pat = re.compile(r"(.*)==(.*)")
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

    def read_phylum_analysis(self, filename='/home/runner/phylum_analysis.json'):
        if not pathlib.Path(filename).is_file():
            print(f"[ERROR] Cannot find {filename}")
            sys.exit(11)
        with open(filename,'r') as infile:
            phylum_analysis_json = json.loads(infile.read())
        print(f"[DEBUG] read {len(phylum_analysis_json)} bytes")
        return phylum_analysis_json

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
        if pkg_vul < self.vul:
            failed_flag = 1
            vuln_flag = 1
            issue_flags.append('vul')
            fail_string += f"|Software Vulnerability|{pkg_vul*100}|{self.vul*100}|\n"
        if pkg_mal < self.mal:
            failed_flag = 1
            issue_flags.append('mal')
            fail_string += f"|Malicious Code|{pkg_mal*100}|{self.mul*100}|\n"
        if pkg_eng < self.eng:
            failed_flag = 1
            issue_flags.append('eng')
            fail_string += f"|Engineering|{pkg_eng*100}|{self.eng*100}|\n"
        if pkg_lic < self.lic:
            failed_flag = 1
            issue_flags.append('lic')
            fail_string += f"|License|{pkg_lic*100}|{self.lic*100}|\n"
        if pkg_aut < self.aut:
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

    def run(self):
        diff_data = self.get_PR_diff()
        changes = self.get_reqs_hunks(diff_data)
        pkg_ver = self.generate_pkgver(changes)
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

        if self.gbl_incomplete == True:
            print(f"[DEBUG] {len(self.incomplete_pkgs)} packages were incomplete as of the analysis job")
            returncode += 5

        with open('/home/runner/returncode.txt','w') as resultout:
            resultout.write(str(returncode))


if __name__ == "__main__":
    argv = sys.argv

    if argc := len(sys.argv) < 8:
        print(f"Usage: {argv[0]} DIFF_URL VUL_THRESHOLD MAL_THRESHOLD ENG_THRESHOLD LIC_THRESHOLD AUT_THRESHOLD")
        sys.exit(11)

    #  diff_url = argv[1]
    #  owner = argv[1]
    repo = argv[1]
    pr_num = argv[2]
    vul = argv[3]
    mal = argv[4]
    eng = argv[5]
    lic = argv[6]
    aut = argv[7]

    a = AnalyzePRForReqs(repo, pr_num, vul, mal, eng, lic, aut)
    a.run()

