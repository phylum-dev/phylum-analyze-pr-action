# phylum-analyze-pr-action
A GitHub Action to automatically analyze Pull Requests for changes to package manager lockfiles using Phylum.

Enables users to configure thresholds for each of Phylum's five risk domain scores. If a package risk domain score is below the threshold, the action will fail the check on the pull request. When packages fail the risk analysis, a comment is created on the PR to summarize the issues.

## Features
- configurable risk domain thresholds
- uses 

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
        uses: peterjmorgan/phylum-analyze-pr-action@master
        with:
          vul_threshold: 0.6
          mal_threshold: 0.6
          eng_threshold: 0.6
          lic_threshold: 0.6
          aut_threshold: 0.6
          phylum_username: ${{ secrets.PHYLUM_USER }}
          phylum_password: ${{ secrets.PHYLUM_PASS }}
```

### Supported lockfiles:
- requirements.txt (Python PyPI)
- package-lock.json (JavaScript/TypeScript NPM)
- yarn.lock (JavaScript/TypeScript NPM)

### Requirements:
- active Phylum account ([Register here](https://app.phylum.io/auth/registration))
- repository secrets: PHYLUM_USER and PHYLUM_PASS
- concrete package versions (only applicable for requirements.txt)
- existing Phylum project for repository (`.phylum_project` must be present)

### Example comment
![image](https://user-images.githubusercontent.com/132468/140830714-24acc278-0102-4613-b006-6032a62b6896.png)

