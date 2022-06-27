# Contributing

Contributions are welcome and appreciated!

Phylum is the future of software supply chain security and is eager to provide useful GitHub integrations.
If there is an unsupported use case for managing the security of your dependencies, we want to know about it.
If there is a way Phylum can be used to make your life as a developer easier, we want to be there for you and do it!

_You_ can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at <https://github.com/phylum-dev/phylum-analyze-pr-action/issues>.
If the bug is related to the underlying Docker image instead of the action itself, report bugs at
<https://github.com/phylum-dev/phylum-ci/issues> instead.

Please use the bug report template which should remind you to include:

* A clear and consise description of the bug
* Detailed steps to reproduce the bug
* Expected behavior
* Screenshots, where appropriate
* Additional context
  * The operating system name and version
  * Any details about the setup that might be helpful in troubleshooting

### Fix Bugs

Look through the GitHub issues for bugs to work on, which will be labeled with `bug`.

### Implement Features

Look through the GitHub issues for features to work on, which will be labeled with `enhancement`.

### Write Documentation

The action could always use more documentation, whether as part of the official phylum docs, in help/description
messages, or even on the web in blog posts, articles, and such.

### Increase Test Coverage

There can always be more and better tests to improve the overall test coverage.
Test contributions will help make the project more robust, less prone to regressions, and easier for everyone to
contribute as it will be more likely that changes are made in a way that don't break other parts of the project.
Even if there is already 100% test coverage, there may still be room for contributions.
For instance, it may be the case that certain functionality or use cases are not covered in the existing set of tests.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/phylum-dev/phylum-analyze-pr-action/issues>.

If you are proposing a feature, please use the feature request template which should remind you to:

* Explain in detail how it would work
* Keep the scope as narrow as possible, to make it easier to implement
* Provide additional context
* Add acceptance criteria

## Security Disclosures

Found a security issue in this repository? See the [security policy](./SECURITY.md)
for details on coordinated disclosure.

## Code of Conduct

Everyone participating in the `phylum-analyze-pr-action` project, and in particular in the issue tracker and pull
requests, is expected to treat other people with respect and more generally to follow the guidelines articulated in the
[Code of Conduct](./CODE_OF_CONDUCT.md).

## Local Development

Ready to contribute with code submissions and pull requests (PRs)?
Here's how to set up `phylum-analyze-pr-action` for local development.

1. Clone the `phylum-analyze-pr-action` repo locally

    ```sh
    git clone git@github.com:phylum-dev/phylum-analyze-pr-action.git
    ```

2. Create a branch for local development:

    ```sh
    git checkout -b <name-of-your-branch>
    ```

    Now you can make your changes locally.

3. If the changes are to the underlying Docker image, also check out the `phylum-ci` repo locally

    ```sh
    git clone git@github.com:phylum-dev/phylum-ci.git
    git checkout -b <name-of-your-branch>
    ```

    Reference the contribution guidelines for [the `phylum-ci` repository](https://github.com/phylum-dev/phylum-ci)
    for more detail. Updates made to the underlying image can be built and placed somewhere accessible for testing:

    ```yaml
    # Change this entry in the `action.yml` file to point to your image. Reference:
    # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsimage
    image: docker://phylumio/phylum-ci:latest
    ```

4. Commit your changes and push your branch to GitHub:

    ```sh
    git add .
    git commit -m "Description of the changes goes here"
    git push --set-upstream origin <name-of-your-branch>
    ```

5. Submit a pull request (PR) through the GitHub website

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

* Does this PR have an associated issue (i.e., `closes #<issueNum>` in the PR description)?
* Have you ensured that you have met the expected acceptance criteria?
* Have you created sufficient tests?
* Have you updated all affected documentation?

The pull request should work for all tests defined in the status checks.
