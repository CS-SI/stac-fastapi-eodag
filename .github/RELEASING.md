# Releasing

This document is intended for maintainers only.

## How to create a new release

Releases are driven by [python-semantic-release](https://python-semantic-release.readthedocs.io/), which analyzes commit messages since the last tag to determine the next version automatically.

Both the Python package and the Helm chart (`Chart.yaml` `version`/`appVersion` and `values.yaml` image tag) are updated in the same release commit.

### Prerequisites

- Your commits (or the PRs merged into `main`) follow the [Conventional Commits](https://www.conventionalcommits.org/) format.
- PR titles are enforced by the `Lint PR` workflow.

### Version bump rules

| Commit type | Version bump |
|---|---|
| `feat:` | Minor (`0.x.0`) |
| `fix:`, `perf:`, `build:` | Patch (`0.0.x`) |
| `BREAKING CHANGE` footer or `feat!:` / `fix!:` | Major (`x.0.0`) |
| `docs:`, `style:`, `test:`, `chore:`, `ci:`, `refactor:` | No release |

### Steps

1. Make sure all desired changes are merged into `main`.
2. Go to **Actions → Publish a Release** on GitHub.
3. Click **Run workflow** → **Run workflow**.
4. The workflow will:
   - Determine the next version from commits since the last tag.
   - Update `version` in `pyproject.toml` locally.
   - Update the Helm chart defaults to match the new release.
   - Create one release commit and push a `v<new_version>` tag.
5. The tag push automatically triggers the following workflows in parallel:
   - **Publish to PyPI** (`deploy.yml`)
   - **Build and publish a container image** (`package.yml`) — tagged `<version>-eodag-<eodag_version>`
   - **Release Charts** (`release.yml`) — publishes the Helm chart via GitHub Releases

> If no releasable commits are found (e.g. only `chore:` or `docs:` changes), semantic-release exits without creating a release.

## Dependency updates

Renovate opens a PR when a new `eodag` version is available.
It also updates GitHub Actions workflow versions in `.github/workflows/*.yml`.

1. Merge the Renovate PR into `main`.
2. Run **Actions → Publish a Release** when you want to publish a new version of this repository.
3. The release workflow picks up the updated `uv.lock`, calculates the new version, updates the Helm chart defaults, and pushes the release tag.
