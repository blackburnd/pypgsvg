# Releasing pypgsvg to PyPI

This document describes the process for releasing new versions of pypgsvg to PyPI.

## Overview

pypgsvg uses **Trusted Publishing** via GitHub Actions, which is the modern, secure way to publish to PyPI (no API tokens needed). The release process is automated through GitHub Actions when you push a version tag.

## Prerequisites

1. **Maintainer access** to the GitHub repository
2. **Trusted Publisher** configured on PyPI (already set up for this project)
3. **Clean git state** (no uncommitted changes)
4. **All tests passing**

## Quick Release Process

### Automated Release (Recommended)

```bash
# Release a new version (e.g., 1.2.0)
./release.sh 1.2.0
```

This script will:
1. ✓ Verify git working directory is clean
2. ✓ Run all tests to ensure everything works
3. ✓ Update version in `pyproject.toml` and `setup.py`
4. ✓ Commit the version changes
5. ✓ Create an annotated git tag (e.g., `v1.2.0`)
6. ✓ Push the commit and tag to GitHub
7. ✓ Trigger GitHub Actions to publish to PyPI

### Manual Release Process

If you prefer to do it manually:

```bash
# 1. Update version in pyproject.toml and setup.py
emacs pyproject.toml  # Change version = "1.1.41" to version = "1.2.0"
emacs setup.py        # Change version="1.1.41" to version="1.2.0"

# 2. Run tests
./run-tests.sh

# 3. Commit and tag
git add pyproject.toml setup.py
git commit -m "Release version 1.2.0"
git tag -a v1.2.0 -m "Release version 1.2.0"

# 4. Push (this triggers the GitHub Action)
git push origin main
git push origin v1.2.0
```

## What Happens After Pushing a Tag

The GitHub Actions workflow (`.github/workflows/publish.yml`) automatically:

1. **Builds** the package using `python -m build`
2. **Tests** the built package to ensure it installs correctly
3. **Publishes to TestPyPI** (always, for testing)
4. **Publishes to PyPI** (only for version tags like `v1.2.0`)

You can monitor the workflow at:
https://github.com/blackburnd/pypgsvg/actions

## Version Numbering

pypgsvg follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

Examples:
- `1.1.41` → `1.1.42` (bug fix)
- `1.1.41` → `1.2.0` (new feature)
- `1.1.41` → `2.0.0` (breaking change)

## Verifying the Release

After the GitHub Action completes:

1. **Check TestPyPI**: https://test.pypi.org/project/pypgsvg/
2. **Check PyPI**: https://pypi.org/project/pypgsvg/
3. **Test installation**:
   ```bash
   pip install --upgrade pypgsvg
   pypgsvg --help
   ```

## Creating a GitHub Release

After the package is published to PyPI, create a GitHub Release:

1. Go to https://github.com/blackburnd/pypgsvg/releases/new
2. Select the tag you just pushed (e.g., `v1.2.0`)
3. Add release notes describing:
   - New features
   - Bug fixes
   - Breaking changes (if any)
   - Contributors
4. Publish the release

## Troubleshooting

### Release failed on GitHub Actions

Check the workflow logs at https://github.com/blackburnd/pypgsvg/actions

Common issues:
- **Tests failed**: Fix the tests and push a new commit
- **Build failed**: Check build dependencies in workflow
- **PyPI publish failed**: Verify Trusted Publisher configuration

### Version already exists on PyPI

PyPI does not allow re-uploading the same version. You must:
1. Increment the version number
2. Create a new release

### Rollback a release

You cannot delete a release from PyPI once published. Instead:
1. Release a new patch version (e.g., `1.2.1`) with fixes
2. Mark the problematic version as yanked on PyPI (prevents new installs)

## Manual Upload (Emergency Only)

If GitHub Actions is down, you can manually upload using `twine`:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to TestPyPI (test first!)
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```

**Note**: This requires PyPI API tokens. Trusted Publishing via GitHub Actions is strongly preferred.

## Best Practices

1. **Always run tests** before releasing
2. **Test on TestPyPI** before production PyPI
3. **Write release notes** for every release
4. **Follow semantic versioning** consistently
5. **Update CHANGELOG** (if you have one)
6. **Create GitHub Release** with notes after publishing

## Reference

- **PyPI Project**: https://pypi.org/project/pypgsvg/
- **TestPyPI Project**: https://test.pypi.org/project/pypgsvg/
- **GitHub Repository**: https://github.com/blackburnd/pypgsvg
- **GitHub Actions Workflow**: `.github/workflows/publish.yml`
- **Trusted Publishing Docs**: https://docs.pypi.org/trusted-publishers/

## Questions?

Open an issue at https://github.com/blackburnd/pypgsvg/issues
