---
name: release
description: "Prepare and publish a new cryptobot-python release. Use when the user asks to cut a release, bump the package version, update HISTORY.md, create a git tag, or create a GitHub release."
---

# Release Skill

Create a new release for the cryptobot-python package.

## Usage

```
/release <version>
```

Where `<version>` is the new semantic version (e.g., `0.4.2`, `0.5.0`, `1.0.0`).

## Instructions

When the user invokes this skill with a version number, perform the following steps:

1. **Validate the version**: Ensure the version follows semantic versioning (X.Y.Z format). Reject pre-release or build metadata suffixes unless the user explicitly requests them.

2. **Update version files**:
   - Update the `version` field in `pyproject.toml`:
     ```bash
     sed -i '' 's/^version = ".*"/version = "<version>"/' pyproject.toml
     ```
   - Update `__version__` in `cryptobot/__init__.py`:
     ```bash
     sed -i '' 's/__version__ = ".*"/__version__ = "<version>"/' cryptobot/__init__.py
     ```
   - Verify both files match:
     ```bash
     grep 'version' pyproject.toml | head -1
     grep '__version__' cryptobot/__init__.py
     ```

3. **Ask for release notes**: Ask the user what changes should be included in the release notes.

4. **Update HISTORY.md**: Add a new entry at the top of the History section with the version number, today's date, and the release notes provided by the user.

5. **Run tests**: Execute `make test` to ensure all tests pass before proceeding. Do not continue if tests fail.

6. **Create commit**:
   ```bash
   git add pyproject.toml cryptobot/__init__.py HISTORY.md
   git commit -m "chore(release): prepare v<version> release"
   ```

7. **Create tag**:
   ```bash
   git tag -a "v<version>" -m "v<version>"
   ```

8. **Push commit and tag**:
   ```bash
   git push origin main
   git push origin "v<version>"
   ```

9. **Create GitHub release**:
   ```bash
   gh release create "v<version>" --title "v<version>" --notes "<release-notes>"
   ```
   Use the release notes from the HISTORY.md entry. For multi-line notes, use `--notes-file` with a temporary file instead.

10. **Report completion**: Provide the user with a summary of files changed and a link to the GitHub release.
