# phylum-analyze-pr-action
A GitHub Action to automatically analyze Pull Requests for changes to package manager lockfiles using Phylum.

## Supported lockfiles:
- requirements.txt (Python PyPI)
- package-lock.json (JavaScript/TypeScript NPM)
- yarn.lock (JavaScript/TypeScript NPM)

## Description:

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
