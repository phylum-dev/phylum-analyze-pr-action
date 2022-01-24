# phylum-analyze-pr-action
A GitHub Action to automatically analyze Pull Requests for changes to package manager lockfiles using Phylum.

Phylum provides a complete risk analyis of "open-source packages" (read: untrusted software from random Internet strangers). Phylum evolved forward from legacy SCA tools to defend from supply-chain malware, malicious open-source authors, and engineering risk, in addtion to software vulnerabilities and license risks. To learn more, please see [our website](https://phylum.io)

This action enables users to configure thresholds for each of Phylum's five risk domain scores. If a package risk domain score is below the threshold, the action will fail the check on the pull request. When packages fail the risk analysis, a comment is created on the PR to summarize the issues.

## Features
- configurable risk domain thresholds
- uses [peter-evans/create-or-update-comment](https://github.com/marketplace/actions/create-or-update-comment) to add comments to PRs

## Getting Started
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
      - uses: actions/checkout@v2
      - id: analyze-pr-test
        uses: phylum-dev/phylum-analyze-pr-action@v1.3
        with:
          vul_threshold: 0.6
          mal_threshold: 0.6
          eng_threshold: 0.6
          lic_threshold: 0.6
          aut_threshold: 0.6
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}
```

### Supported lockfiles:
- requirements.txt (Python PyPI)
- package-lock.json (JavaScript/TypeScript NPM)
- yarn.lock (JavaScript/TypeScript NPM)
- Gemfile.lock (Ruby Rubygems/Bundler)

### Requirements:
- active Phylum account ([Register here](https://app.phylum.io/auth/registration))
- repository secret defined: PHYLUM_TOKEN (extracted from Phylum CLI configuration file "offline_access")
  1. Ensure you've updated the Phylum CLI on a local installation to version `1.2.0`
  2. Successfully authenticate using Phylum CLI. This will ensure the token is populated in the phylum config file ~/.phylum/settings.yaml in stanza offline_access
  3. Copy the token value in the offline_access stanza
  4. Create a new GitHub secret in the desired repository. This can be done through the GitHub web UI or using the gh command line tool: gh secret set PHYLUM_TOKEN -b <token_value>
  5. Optionally, you can remove the antiquated PHYLUM_USER and PHYLUM_PASS GitHub secrets as they are no longer used.
- concrete package versions (only applicable for requirements.txt)
- existing Phylum project for repository (`.phylum_project` must be present)

### Known Issues:
1. Incomplete packages: if Phylum hasn't yet analyzed a package requested by this action, the action will fail with an exit code of 5. This is momentarily preferable than waiting.

### Example comment
![image](https://user-images.githubusercontent.com/132468/140830714-24acc278-0102-4613-b006-6032a62b6896.png)

