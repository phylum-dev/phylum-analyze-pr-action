# Phylum Analyze PR action

[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-analyze-pr-action)][license]
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-analyze-pr-action)][issues]
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-analyze-pr-action)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)][CoC]

A GitHub Action using Phylum to automatically analyze Pull Requests for changes to package manager lockfiles.

[license]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/LICENSE
[issues]: https://github.com/phylum-dev/phylum-analyze-pr-action/issues
[CoC]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/CODE_OF_CONDUCT.md

## Overview

Phylum provides a complete risk analyis of "open-source packages" (read: untrusted software from random Internet
strangers). Phylum evolved forward from legacy SCA tools to defend from supply-chain malware, malicious open-source
authors, and engineering risk, in addtion to software vulnerabilities and license risks. To learn more, please see
[our website](https://phylum.io).

Once configured for a repository, this action will provide analysis of project dependencies from a lockfile during a
Pull Request (PR) and output the results as a comment on the PR.
The CI job will return an error (i.e., fail the build) if any of the newly added/modified dependencies from the PR fail
to meet the project risk thresholds for any of the five Phylum risk domains:

* Vulnerability (aka `vul`)
* Malicious Code (aka `mal`)
* Engineering (aka `eng`)
* License (aka `lic`)
* Author (aka `aut`)

See [Phylum Risk Domains documentation][risk_domains] for more detail.

**NOTE**: It is not enough to have the total project threshold set. Individual risk domain threshold values must be set,
either in the UI or with `phylum-ci` options, in order to enable analysis results for CI. Otherwise, the risk domain is
considered disabled and the overall project threshold value will be used.

There will be no note if no dependencies were added or modified for a given PR.
If one or more dependencies are still processing (no results available), then the note will make that clear and the CI
job will only fail if dependencies that have _completed analysis results_ do not meet the specified project risk
thresholds.

[risk_domains]: https://docs.phylum.io/docs/phylum-package-score#risk-domains

## Prerequisites

The GitHub Actions environment is primarily supported through the use of a Docker image.
The pre-requisites for using this image are:

* Ability to run a [Docker container action][container]
  * GitHub-hosted runners must use an Ubuntu runner
  * Self-hosted runners must use a Linux operating system and have Docker installed
* Access to the `phylum-dev/phylum-ci` Docker image from the [GitHub Container Registry][package]
* A [GitHub token][gh_token] with API access
  * Can be the default `GITHUB_TOKEN` provided automatically at the start of each workflow run
    * Needs at least write access for `pull-requests` scope - see [documentation][scopes]
  * Can be a personal access token (PAT) - see [documentation][PAT]
    * Needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time
* A `.phylum_project` file exists at the root of the repository
  * See [`phylum project`][phylum_project] and
    [`phylum project create`][phylum_project_create] command documentation

[container]: https://docs.github.com/en/actions/creating-actions/creating-a-docker-container-action
[package]: https://github.com/phylum-dev/phylum-ci/pkgs/container/phylum-ci
[gh_token]: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
[scopes]: https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
[PAT]: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
[phylum_contact]: https://phylum.io/contact-us
[app_register]: https://app.phylum.io/register
[phylum_tokens]: https://docs.phylum.io/docs/api-keys
[phylum_register]: https://docs.phylum.io/docs/phylum_auth_register
[phylum_project]: https://docs.phylum.io/docs/phylum_project
[phylum_project_create]: https://docs.phylum.io/docs/phylum_project_create

## Supported lockfiles

If not explicitly specified, an attempt will be made to automatically detect the lockfile. Some lockfile types
(e.g., Python/pip `requirements.txt`) are ambiguous in that they can be named differently and may or may not contain
strict dependencies. In these cases, it is best to specify an explicit lockfile path by using the `phylum-ci --lockfile`
option. The list of currently supported lockfiles can be found in the [Phylum Knowledge Base][supported_lockfiles].

[supported_lockfiles]: https://docs.phylum.io/docs/analyzing-dependencies

## Getting Started

Phylum analysis of dependencies can be added to existing CI workflows or on it's own with this minimal configuration:

```yaml
name: Phylum_analyze
on: pull_request
jobs:
  analyze_deps:
    name: Analyze dependencies with Phylum
    permissions:
      contents: read
      pull-requests: write
    runs-on: ubuntu-latest
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Analyze lockfile
        uses: phylum-dev/phylum-analyze-pr-action@v2
        with:
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}
```

This configuration contains a single job, with two steps, that will only run on pull request events.
It does not override any of the `phylum-ci` arguments, which are all either optional or default to secure values.
Let's take a deeper dive into each part of the configuration:

### Workflow and Job names

The workflow and job names can be named differently or included in existing workflows/jobs.

```yaml
name: Phylum_analyze                        # Name the workflow what you like
on: pull_request
jobs:
  analyze_deps:                             # Name the job what you like
    name: Analyze dependencies with Phylum  # This name is optional (defaults to job name)
```

### Workflow trigger

The Phylum Analyze PR action expects to be run in the context of a [`pull_request` webhook event][pr_hook].
This includes both [`pull_request`][pr] and [`pull_request_target`][prt] events.

[pr_hook]: https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#pull_request
[pr]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request
[prt]: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request_target

```yaml
# NOTE: These are examples. Only one definition for `on` is expected.

# Specify the `pull_request` event trigger on one line
on: pull_request

# Alternative to specify `pull_request` trigger (e.g., when other triggers are present)
on:
  pull_request:

# Specify specific branches for the `pull_request` trigger to target
on:
  pull_request:
    branches:
      - main
      - develop
```

### Permissions

When using the default `GITHUB_TOKEN` provided automatically at the start of each workflow run, it is good practice to
ensure the actions used in the workflow are given the least privileges needed to perform their intended function.
The Phylum Analyze PR actions needs at least write access for the `pull-requests` scope.
The `actions/checkout` action needs at least read access for the `contents` scope.
See the [GitHub documentation][scopes] for more info.

```yaml
    permissions:                # Ensure least privilege of actions
      contents: read            # For actions/checkout
      pull-requests: write      # For phylum-dev/phylum-analyze-pr-action
```

When using a personal access token (PAT) instead, the token should be created with the `repo` scope or
minimally the with `public_repo` scope if private repositories will not be used with the PAT.
See the [GitHub documentation][PAT] for more info.

```yaml
    permissions:                # Ensure least privilege of actions
      contents: read            # For actions/checkout
      # The phylum-dev/phylum-analyze-pr-action does not
      # need the `pull-requests` scope here if using a PAT
```

### Specifying a Runner

The Phylum Analyze PR action is a [Docker container action][container].
This requires that [GitHub-hosted runners][runners] use an Ubuntu runner.
Self-hosted runners must use a Linux operating system and have Docker installed.

[runners]: https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners

```yaml
    runs-on: ubuntu-latest
```

### Checking out the Repository

`git` is used within the `phylum-ci` package to do things like determine if there was a lockfile change and,
when specified, report on new dependencies only. Therefore, a clone of the repository is required to ensure that
the local working copy is always pristine and history is available to pull the requested information.

```yaml
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v3
        with:
          # Specifying a depth of 0 ensures all history for all branches.
          # This input may not be required when `--all-deps` option is used.
          fetch-depth: 0
```

### Action Inputs

The action inputs are used to ensure the `phylum-ci` tool is able to perform it's job.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider
using a bot or group account for this token.

A [GitHub token][gh_token] with API access is required to use the API (e.g., to post comments).
This can be the default `GITHUB_TOKEN` provided automatically at the start of each workflow run but it will need at
least write access for the `pull-requests` scope (see [documentation][scopes]).
Alternatively, it can be a [personal access token (PAT)][PAT] with the `repo` scope or minimally the `public_repo`
scope, if private repositories are not used.

The values for the `phylum_token` and `github_token` action inputs can come from repository, environment, or
organizational [encrypted secrets][encrypted_secrets].
Since they are sensitive, **care should be taken to protect them appropriately**.

The `cmd` arguments to the Docker image are the way to exert control over the execution of the Phylum analysis. The
`phylum-ci` script entry point is expected to be called. It has a number of arguments that are all optional and
defaulted to secure values. To view the arguments, their description, and default values, run the script with `--help`
output as specified in the [Usage section of the `phylum-dev/phylum-ci` repository's README][usage] or more simply
view the [script options output][script_options] for the latest release.

[encrypted_secrets]: https://docs.github.com/en/actions/security-guides/encrypted-secrets
[usage]: https://github.com/phylum-dev/phylum-ci#usage
[script_options]: https://github.com/phylum-dev/phylum-ci/blob/main/docs/script_options.md

```yaml
    steps:
      - name: Analyze lockfile
        uses: phylum-dev/phylum-analyze-pr-action@v2
        with:
          # Contact Phylum (phylum.io/contact-us) or register (app.phylum.io/register) to gain access.
          # See also `phylum auth register` (docs.phylum.io/docs/phylum_auth_register) command docs.
          # Consider using a bot or group account for this token.
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}

          # NOTE: These are examples. Only one `github_token` entry line is expected.
          #
          # Use the default `GITHUB_TOKEN` provided automatically at the start of each workflow run.
          # This entry does not have to be specified since it is the default.
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # Use a personal access token (PAT)
          github_token: ${{ secrets.GITHUB_PAT }}

          # NOTE: These are examples. Only one `cmd` entry line is expected.
          #
          # Use the defaults for all the arguments.
          # The default behavior is to only analyze newly added dependencies against
          # the risk domain threshold levels set at the Phylum project level.
          # This entry does not have to be specified since it is the default.
          cmd: phylum-ci
          # Consider all dependencies in analysis results instead of just the newly added ones.
          # The default is to only analyze newly added dependencies, which can be useful for
          # existing code bases that may not meet established project risk thresholds yet,
          # but don't want to make things worse. Specifying `--all-deps` can be useful for
          # casting the widest net for strict adherence to Quality Assurance (QA) standards.
          cmd: phylum-ci --all-deps
          # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous in that
          # they can be named differently and may or may not contain strict dependencies.
          # In these cases, it is best to specify an explicit lockfile path.
          cmd: phylum-ci --lockfile requirements-prod.txt
          # Thresholds for the five risk domains may be set at the Phylum project level.
          # They can be set differently for CI environments to "fail the build."
          cmd: |
            phylum-ci \
              --vul-threshold 60 \
              --mal-threshold 60 \
              --eng-threshold 70 \
              --lic-threshold 90 \
              --aut-threshold 80
          # Install a specific version of the Phylum CLI.
          cmd: phylum-ci --phylum-release 3.5.0 --force-install
          # Mix and match for your specific use case.
          cmd: |
            phylum-ci \
              --vul-threshold 60 \
              --mal-threshold 60 \
              --eng-threshold 70 \
              --lic-threshold 90 \
              --aut-threshold 80 \
              --lockfile requirements-prod.txt \
              --all-deps
```

## Example Comments

---

Phylum OSS Supply Chain Risk Analysis - FAILED

![image](https://user-images.githubusercontent.com/18729796/175793030-1294695d-6e72-405a-8916-444e476ab7ee.png)

---

Phylum OSS Supply Chain Risk Analysis - SUCCESS

![image](https://user-images.githubusercontent.com/18729796/175792822-860e708e-7b8f-4ae3-b43b-28912c6ec7d2.png)

---

## License

Copyright (C) 2022  Phylum, Inc.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/gpl.html> or write to `phylum@phylum.io` or `engineering@phylum.io`

## Contributing

Suggestions and help are welcome. Feel free to open an issue or otherwise contribute.
More information is available on the [contributing documentation][contributing] page.

[contributing]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/CONTRIBUTING.md

## Code of Conduct

Everyone participating in the `phylum-analyze-pr-action` project, and in particular in the issue tracker and pull
requests, is expected to treat other people with respect and more generally to follow the guidelines articulated in the
[Code of Conduct][CoC].

## Security Disclosures

Found a security issue in this repository? See the [security policy][security]
for details on coordinated disclosure.

[security]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/SECURITY.md
