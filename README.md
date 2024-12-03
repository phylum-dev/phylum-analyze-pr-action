# Phylum Analyze PR action

[![GitHub](https://img.shields.io/github/license/phylum-dev/phylum-analyze-pr-action)][license]
[![GitHub issues](https://img.shields.io/github/issues/phylum-dev/phylum-analyze-pr-action)][issues]
![GitHub last commit](https://img.shields.io/github/last-commit/phylum-dev/phylum-analyze-pr-action)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)][CoC]

A GitHub Action to analyze dependencies with Phylum to protect your code against increasingly sophisticated attacks and get peace of mind to focus on your work.

[license]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/LICENSE
[issues]: https://github.com/phylum-dev/phylum-analyze-pr-action/issues
[CoC]: https://github.com/phylum-dev/phylum-analyze-pr-action/blob/main/CODE_OF_CONDUCT.md

## Overview

Phylum provides a complete risk analyis of "open-source packages" (read: untrusted software from random Internet
strangers). Phylum evolved forward from legacy SCA tools to defend from supply-chain malware, malicious open-source
authors, and engineering risk, in addition to software vulnerabilities and license risks. To learn more, please see
[our website](https://phylum.io).

Once configured for a repository, this action will provide analysis of project dependencies from lockfiles or manifests
during a Pull Request (PR) and output the results as a comment on the PR unless the option to skip comments is provided.
The CI job will return an error (i.e., fail the build) if any of the newly added/modified dependencies from the PR fail
to meet the established policy unless audit mode is specified.

There will be no note if no dependencies were added or modified for a given PR.
If one or more dependencies are still processing (no results available), then the note will make that clear and the CI
job will only fail if dependencies that have _completed analysis results_ do not meet the active policy.

## Prerequisites

The GitHub Actions environment is primarily supported through the use of a Docker image.
The prerequisites for using this image are:

* Ability to run a [Docker container action][container]
  * GitHub-hosted runners must use an Ubuntu runner
  * Self-hosted runners must use a Linux operating system and have Docker installed
* Access to the `phylum-dev/phylum-ci` Docker image from the [GitHub Container Registry][package]
* A [GitHub token][gh_token] with API access
  * Not required when comment generation has been skipped
  * Can be the default `GITHUB_TOKEN` provided automatically at the start of each workflow run
    * Needs at least write access for `pull-requests` scope - see [documentation][scopes]
  * Can be a personal access token (PAT) - see [documentation][PAT]
    * Needs the `repo` scope or minimally the `public_repo` scope if private repositories are not used
* A [Phylum token][phylum_tokens] with API access
  * [Contact Phylum][phylum_contact] or [register][app_register] to gain access
    * See also [`phylum auth register`][phylum_register] command documentation
  * Consider using a bot or group account for this token
  * Forked repos require the `pull_request_target` event, to allow secret access
* Access to the Phylum API endpoints
  * That usually means a connection to the internet, optionally via a proxy
  * Support for on-premises installs are not available at this time

[container]: https://docs.github.com/en/actions/creating-actions/creating-a-docker-container-action
[package]: https://github.com/phylum-dev/phylum-ci/pkgs/container/phylum-ci
[gh_token]: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
[scopes]: https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
[PAT]: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
[phylum_contact]: https://phylum.io/contact-us
[app_register]: https://app.phylum.io/register
[phylum_tokens]: https://docs.phylum.io/knowledge_base/api-keys
[phylum_register]: https://docs.phylum.io/cli/commands/phylum_auth_register

## Supported Dependency Files

If not explicitly specified, an attempt will be made to automatically detect dependency files. These include both
lockfiles and manifests. The basic difference is that manifests are where top-level dependencies are specified in their
loose form while lockfiles contain the completely resolved collection of the abstract declarations from a manifest.

Some dependency file types (e.g., Python/pip `requirements.txt`) are ambiguous in that they can be named differently
and may or may not contain strict dependencies. That is, they can be either a lockfile or a manifest. We call these
"[lockifests]." Some dependency files fail to parse as the expected lockfile type (e.g., `pip` instead of `poetry` for
`pyproject.toml` manifests).

For these situations, the recommendation is to specify the path and lockfile type explicitly in a
[`.phylum_project` file] at the root of the project repository. The easiest way to do that is with the Phylum CLI,
using the [`phylum init` command][phylum_init] and committing the generated `.phylum_project` file.

The Phylum Knowledge Base contains the list of currently [supported lockfiles][supported_lockfiles]. It is also where
information on [lockfile generation][lockfile_generation] can be found for current manifest file support.

[lockifests]: https://docs.phylum.io/cli/lockfile_generation#lockifests
[`.phylum_project` file]: https://docs.phylum.io/knowledge_base/phylum_project_files
[phylum_init]: https://docs.phylum.io/cli/commands/phylum_init
[supported_lockfiles]: https://docs.phylum.io/cli/supported_lockfiles
[lockfile_generation]: https://docs.phylum.io/cli/lockfile_generation

## Getting Started

Phylum analysis of dependencies can be added to existing CI workflows or on its own with this minimal configuration:

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
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Analyze dependencies
        uses: phylum-dev/phylum-analyze-pr-action@v2
        with:
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}
```

This configuration contains a single job, with two steps, that will only run on pull request events.
It provides debug output but otherwise does not override any of the `phylum-ci` arguments, which are all either
optional or default to secure values. Let's take a deeper dive into each part of the configuration:

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

Allowing pull requests from forked repositories requires using the `pull_request_target` event since the Phylum API
key is stored as a secret and the `pull_request` event does not provide access to secrets when the PR comes from a
fork.

```yaml
on:
  pull_request:
  # Allow PRs from forked repos to access secrets, like the Phylum API key
  pull_request_target:
```

> ⚠️ **WARNING** ⚠️
>
> Using the `pull_request_target` event for forked repositories requires additional configuration when
> [checking out the repo](#checking-out-the-repository). Be aware that such a configuration has security implications
> if done improperly. Attackers may be able to obtain repository write permissions or steal repository secrets.
> Please take the time to understand and mitigate the risks:
>
> * GitHub Security Lab: ["Preventing pwn requests"][gh_pwn]
> * GitGuardian: ["GitHub Actions Security Best Practices"][gha_security]
>
> Minimal suggestions include:
>
> * Use a separate workflow for the Phylum Analyze PR action
> * Do not provide access to any secrets beyond the Phylum API key
> * Limit the steps in the job to two: checking out the PR's code and using the Phylum action

[gh_pwn]: https://securitylab.github.com/research/github-actions-preventing-pwn-requests/
[gha_security]: https://blog.gitguardian.com/github-actions-security-cheat-sheet/

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
minimally with the `public_repo` scope if private repositories will not be used with the PAT.
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

`git` is used within the `phylum-ci` package to do things like determine if there was a dependency file change and,
when specified, report on new dependencies only. Therefore, a clone of the repository is required to ensure that
the local working copy is always pristine and history is available to pull the requested information.

```yaml
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v4
        with:
          # Specifying a depth of 0 ensures all history for all branches.
          # This input may not be required when `--all-deps` option is used.
          fetch-depth: 0
```

Allowing pull requests from forked repositories [requires using the `pull_request_target` event](#workflow-trigger)
and checking out the head of the forked repository:

```yaml
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          # Specifying the head of the forked repository's PR branch
          # is required to get any proposed dependency file changes.
          ref: ${{ github.event.pull_request.head.sha }}
```

> ⚠️ **WARNING** ⚠️
>
> Using the `pull_request_target` event for forked repositories and checking out the pull request's code has security
> implications if done improperly. Attackers may be able to obtain repository write permissions or steal repository
> secrets. Please take the time to understand and mitigate the risks:
>
> * GitHub Security Lab: ["Preventing pwn requests"][gh_pwn]
> * GitGuardian: ["GitHub Actions Security Best Practices"][gha_security]
>
> Minimal suggestions include:
>
> * Use a separate workflow for the Phylum Analyze PR action
> * Do not provide access to any secrets beyond the Phylum API key
> * Limit the steps in the job to two: checking out the PR's code and using the Phylum action

### Action Inputs

The action inputs are used to ensure the `phylum-ci` tool is able to perform its job.

A [Phylum token][phylum_tokens] with API access is required to perform analysis on project dependencies.
[Contact Phylum][phylum_contact] or [register][app_register] to gain access.
See also [`phylum auth register`][phylum_register] command documentation and consider
using a bot or group account for this token.

A [GitHub token][gh_token] with API access is required to use the API (e.g., to post comments).
It is not required when comment generation has been skipped (e.g., when in audit mode).
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
      - name: Analyze dependencies
        uses: phylum-dev/phylum-analyze-pr-action@v2
        with:
          # Contact Phylum (phylum.io/contact-us) or register (app.phylum.io/register)
          # to gain access. Consider using a bot or group account for this token. See:
          # https://docs.phylum.io/knowledge_base/api-keys
          phylum_token: ${{ secrets.PHYLUM_TOKEN }}

          # NOTE: These are examples. Specify at most one `github_token` entry line.
          #
          # Use the default `GITHUB_TOKEN` provided automatically at the start
          # of each workflow run. This entry is optional since it is the default.
          github_token: ${{ secrets.GITHUB_TOKEN }}
          # Use a personal access token (PAT)
          github_token: ${{ secrets.GITHUB_PAT }}

          # NOTE: These are examples. Only one `cmd` entry line is expected.
          #
          # Use the defaults for all the arguments and provide debug level output.
          # The default behavior is to only analyze newly added dependencies
          # against the active policy set at the Phylum project level.
          # This entry does not have to be specified since it is the default.
          cmd: phylum-ci -vv
          # Same as the previous entry, but without debug level output.
          cmd: phylum-ci
          # Consider all dependencies in analysis results instead of just the
          # newly added ones. The default is to only analyze newly added
          # dependencies, which can be useful for existing code bases that may
          # not meet established policy rules yet, but don't want to make things
          # worse. Specifying `--all-deps` can be useful for casting the widest
          # net for strict adherence to Quality Assurance (QA) standards.
          cmd: phylum-ci --all-deps
          # Force analysis for all dependencies in a manifest file.
          # This is especially useful for *workspace* manifest files where
          # there is no companion lockfile (e.g., libraries).
          cmd: phylum-ci --force-analysis --all-deps --depfile Cargo.toml
          # Some lockfile types (e.g., Python/pip `requirements.txt`) are ambiguous
          # in that they can be named differently and may or may not contain strict
          # dependencies. In these cases it is best to specify an explicit path,
          # either with the `--depfile` option or in a `.phylum_project` file:
          # https://docs.phylum.io/knowledge_base/phylum_project_files
          # The easiest way to do that is with the Phylum CLI, using the
          # `phylum init` (https://docs.phylum.io/cli/commands/phylum_init) command
          # and committing the generated `.phylum_project` file.
          cmd: phylum-ci --depfile requirements-prod.txt
          # Specify multiple explicit dependency file paths.
          cmd: phylum-ci --depfile requirements-prod.txt path/to/dependency.file
          # Exclude dependency files by gitignore-style pattern.
          cmd: phylum-ci --exclude "requirements-*.txt"
          # Specify multiple exclusion patterns.
          cmd: phylum-ci --exclude "build.gradle" "tests/fixtures/"
          cmd: |
            phylum-ci \
              --exclude "/requirements-*.txt" \
              --exclude "build.gradle" "fixtures/"
          # Perform analysis as part of an organization and/or group-owned project.
          # When an org is specified, a group name must also be specified.
          # A paid account is needed to use orgs or groups: https://phylum.io/pricing
          cmd: phylum-ci --org my_org --group my_group
          cmd: phylum-ci --group my_group
          # Analyze all dependencies in audit mode,
          # to gain insight without failing builds.
          cmd: phylum-ci --all-deps --audit
          # Install a specific version of the Phylum CLI.
          cmd: phylum-ci --phylum-release 6.5.0 --force-install
          # Mix and match for your specific use case.
          cmd: |
            phylum-ci \
              -vv \
              --org my_org \
              --group my_group \
              --depfile requirements-dev.txt \
              --depfile requirements-prod.txt path/to/dependency.file \
              --depfile Cargo.toml \
              --force-analysis \
              --all-deps
```

### Exit Codes

The Phylum Analyze PR action will return a zero (0) exit code when it completes successfully and a non-zero code
otherwise. The full and current list of exit codes is [documented here][exit_codes] and "Output Modification"
[options exist][script_options] to be strict or loose with setting them.

[exit_codes]: https://github.com/phylum-dev/phylum-ci#exit-codes

## Example Comments

> **NOTE:** Comments will not be shown when in audit mode or when comments are explicitly skipped.
> Analysis output will still be available in the logs.

---

Phylum OSS Supply Chain Risk Analysis - FAILED

![image](https://user-images.githubusercontent.com/18729796/232164049-0e394d1f-f709-403f-a12c-2fe26adfbb37.png)

---

Phylum OSS Supply Chain Risk Analysis - INCOMPLETE WITH FAILURE

![image](https://user-images.githubusercontent.com/18729796/232165295-61a4800b-0f3b-46b8-9c4b-1215b1aab83a.png)

---

Phylum OSS Supply Chain Risk Analysis - INCOMPLETE

![image](https://user-images.githubusercontent.com/18729796/232165075-25116fb4-7706-4ebf-948c-9b593c7cd28b.png)

---

Phylum OSS Supply Chain Risk Analysis - SUCCESS

![image](https://user-images.githubusercontent.com/18729796/232164498-3ce7d24a-a4ec-4df3-92b2-ab38555703b9.png)

---

## Alternatives

The default `phylum-ci` Docker image contains `git` and the installed `phylum` Python package. It also contains an
installed version of the Phylum CLI and all required tools needed for [lockfile generation][lockfile_generation].
An advantage of using the default Docker image is that the complete environment is packaged and made available with
components that are known to work together.

One disadvantage to the default image is its size. It can take a while to download and may provide more tools than
required for your specific use case. Special `slim` tags of the `phylum-ci` image are provided as an alternative.
These tags differ from the default image in that they do not contain the required tools needed for
[lockfile generation][lockfile_generation] (with the exception of the `pip` tool). The `slim` tags are significantly
smaller and allow for faster action run times. They are useful for those instances where **no** manifest files are
present and/or **only** lockfiles are used.

Using the slim image tags is possible by altering your workflow to use the image directly instead of this GitHub
Action. That is possible with either [container jobs](#container-jobs) or [container steps](#container-steps).

### Container Jobs

GitHub Actions allows for workflows to run a job within a container, using the `container:` statement in the workflow
file. These are known as container jobs. More information can be found in GitHub documentation:
["Running jobs in a container"][container_job]. To use a `slim` tag in a container job, use this minimal configuration:

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
    container:
      image: docker://ghcr.io/phylum-dev/phylum-ci:slim
      env:
        GITHUB_TOKEN: ${{ github.token }}
        PHYLUM_API_KEY: ${{ secrets.PHYLUM_TOKEN }}
    steps:
      - name: Checkout the repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Analyze dependencies
        run: phylum-ci -vv
```

The `image:` value is set to the latest slim image, but other tags are available to ensure a specific release of the
`phylum-ci` project and a specific version of the Phylum CLI. The full list of available `phylum-ci` image tags can be
viewed on [GitHub Container Registry][ghcr_tags] (preferred) or [Docker Hub][docker_hub_tags].

The `GITHUB_TOKEN` and `PHYLUM_API_KEY` environment variables are required to have those exact names. The rest of the
options are the same as [already documented](#getting-started).

[container_job]: https://docs.github.com/actions/using-jobs/running-jobs-in-a-container
[ghcr_tags]: https://github.com/phylum-dev/phylum-ci/pkgs/container/phylum-ci
[docker_hub_tags]: https://hub.docker.com/r/phylumio/phylum-ci/tags

### Container Steps

GitHub Actions allows for workflows to run a step within a container, by specifying that container image in the `uses:`
statement of the workflow step. These are known as container steps. More information can be found in
[GitHub workflow syntax documentation][container_step]. To use a `slim` tag in a container step, use this minimal
configuration:

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
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Analyze dependencies
        uses: docker://ghcr.io/phylum-dev/phylum-ci:slim
        env:
          GITHUB_TOKEN: ${{ github.token }}
          PHYLUM_API_KEY: ${{ secrets.PHYLUM_TOKEN }}
        with:
          args: phylum-ci -vv
```

The `uses:` value is set to the latest slim image, but other tags are available to ensure a specific release of the
`phylum-ci` project and a specific version of the Phylum CLI. The full list of available `phylum-ci` image tags can be
viewed on [GitHub Container Registry][ghcr_tags] (preferred) or [Docker Hub][docker_hub_tags].

The `GITHUB_TOKEN` and `PHYLUM_API_KEY` environment variables are required to have those exact names. The rest of the
options are the same as [already documented](#getting-started).

[container_step]: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsuses

## FAQs

> 💡 **INFO** 💡
>
> There are more FAQs in the [Phylum Knowledge Base][phylum_kb].

[phylum_kb]: https://docs.phylum.io/knowledge_base/faq

### Why does Phylum report a failing status check if it shows a successful analysis comment?

It is possible to get a successful Phylum analysis comment on the PR **and also** have the Phylum action report a
failing status check. This happens when one or more dependency files fails the filtering process while at least one
dependency file passes the filtering process **and** the Phylum analysis.

The failing status check is meant to serve as an indication to the repository owner that an issue exists with at least
one of the dependency files submitted, whether they intended it or not. The reasoning is that it is better to be
explicit about possible failures, allowing for review of the logs and correction, than to silently ignore the failure
and possibly allow untrusted code into the repository. An [option is provided][script_options] to explicitly ignore
non-analysis warnings and errors that would otherwise affect the exit code.

There are several reasons a dependency file may fail the filtering process and each failure will be included in the logs
as a warning. The file may not exist or it may exist, but only as an empty file. The file may fail to be parsed by
Phylum. The dependency files can be manifests or lockfiles and they can either be provided explicitly or automatically
detected when not provided. Sometimes the automatic detection will misattribute a file as a manifest or assign the wrong
lockfile type. As detailed in the ["Supported Dependency Files"](#supported-dependency-files) section, the
recommendation for this situation is to specify the path and lockfile type explicitly in a [`.phylum_project` file] at
the root of the project repository.

### Why does analysis fail for PRs from forked repositories?

Another reason why Phylum reports
[failing status checks](#why-does-phylum-report-a-failing-status-check-if-it-shows-a-successful-analysis-comment) is for
`pull_request_target` events where manifests are provided. Using `pull_request_target` events for forked repositories
has security implications if done improperly. Attackers may be able to obtain repository write permissions or steal
repository secrets. A more comprehensive enumeration of the risks can be found here:

* GitHub Security Lab: ["Preventing pwn requests"][gh_pwn]
* GitGuardian: ["GitHub Actions Security Best Practices"][gha_security]

This GitHub action disables lockfile generation to prevent arbitrary code execution in an untrusted context, like PRs
from forks. This means that provided manifests are unable to be parsed by Phylum since parsing first requires generating
a lockfile from the manifest. A unique error code and warning message is provided so as to better signal the
implication: the resolved dependencies from the manifest have NOT been analyzed by Phylum. Care should be taken to
inspect changes manually before allowing a manifest to be used in a trusted context.

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
