# phylum-analyze-pr-action
A GitHub Action to automatically analyze Pull Requests for changes to package manager lockfiles using Phylum.

Phylum provides a complete risk analyis of "open-source packages" (read: untrusted software from random Internet
strangers). Phylum evolved forward from legacy SCA tools to defend from supply-chain malware, malicious open-source
authors, and engineering risk, in addtion to software vulnerabilities and license risks. To learn more, please see
[our website](https://phylum.io)

This action enables users to configure thresholds for each of Phylum's five risk domain scores. If a package risk
domain score is below the threshold, the action will fail the check on the pull request. When packages fail the risk
analysis, a comment is created on the PR to summarize the issues.

## Features
- configurable risk domain thresholds
- uses [peter-evans/create-or-update-comment](https://github.com/marketplace/actions/create-or-update-comment)
  to add comments to PRs

## Getting Started
1. Create a workflow in a repository that uses the workflow definition listed below as an example
2. Be sure to include the base/default branches used for development, where the defaults are set to `master` and `main`
3. Define risk domain thresholds using `vul_threshold`, `mal_threshold`, etc. to define a score requirement
   1. For example, a Phylum project score requirement of 60 is defined as `0.6`
4. Additional inputs can be used - see [action.yml](action.yml) for full list

```yaml
on:
  pull_request:
    branches:
      - master
      - main

jobs:
  analyze_PR_with_Phylum_job:
    runs-on: ubuntu-latest
    name: A job to analyze PR with phylum
    steps:
      - uses: actions/checkout@v3
      - id: analyze-pr-test
        uses: phylum-dev/phylum-analyze-pr-action@v1
        with:
          vul_threshold: 0.6
          mal_threshold: 0.6
          eng_threshold: 0.6
          lic_threshold: 0.6
          aut_threshold: 0.6
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}
```

### Supported lockfiles
- `requirements.txt` (Python PyPI)
- `poetry.lock` (Python PyPI)
- `package-lock.json` (JavaScript/TypeScript NPM)
- `yarn.lock` (JavaScript/TypeScript NPM)
- `Gemfile.lock` (Ruby Rubygems/Bundler)

### Requirements
- active Phylum account ([Register here](https://app.phylum.io/auth/registration))
- GitHub repository secret defined: `PHYLUM_TOKEN`
  1. Ensure you've updated the Phylum CLI on a local installation to a version >= `2.0.1`
  2. Successfully authenticate using Phylum CLI to ensure the token is populated and correct
  3. Copy the token value from the output of the `phylum auth token` command
  4. Create a new GitHub secret named `PHYLUM_TOKEN` in the desired repository, through the GitHub web UI or using the gh command line tool: `gh secret set PHYLUM_TOKEN -b <token_value>`
- concrete package versions (only applicable for `requirements.txt`)
- existing Phylum project for repository (`.phylum_project` must be present)

### Known Issues
- [Issue tracker](https://github.com/phylum-dev/phylum-analyze-pr-action/issues)
- [Open bugs](https://github.com/phylum-dev/phylum-analyze-pr-action/labels/%F0%9F%95%B7%EF%B8%8F%20bug)

### Incomplete Packages
Sometimes, users will request risk analysis information for open-source packages Phylum has not yet processed.
When this occurs, Phylum cannot reasonably provide risk scoring information until those packages have been processed.

Starting with `v1.4.0`, `phylum-analyze-pr-action` will:
1. Detect the case of incomplete packages
2. Return an exit code of 0 (a "passing" mark in GitHub Action parlance)
   1. This is to avoid failing a check in the PR with incomplete information
3. Add a comment to the PR indicating that there were incomplete packages
   1. The comment will advise users to wait 30m and re-run the check on the Pull Request
   2. This will give Phylum sufficient time to download, process and analyze the incomplete packages
4. When the check is run a second time, another comment will be added to the Pull Request noting the result of the
   risk analysis operation.

### Example comment
![image](https://user-images.githubusercontent.com/132468/140830714-24acc278-0102-4613-b006-6032a62b6896.png)
