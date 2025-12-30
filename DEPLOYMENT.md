# Deployment Guide

This guide explains how to deploy `storzandbickel-ble` to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **API Token**: Generate an API token at https://pypi.org/manage/account/token/
   - For automated releases, create a token with "Upload packages" scope
   - For test releases, use TestPyPI: https://test.pypi.org/manage/account/token/
   - **📖 See [SETUP_API_KEY.md](SETUP_API_KEY.md) for detailed step-by-step instructions**

## Automated Deployment (Recommended)

The project uses GitHub Actions to automatically build and publish to PyPI when you push a version tag.

### Setup

1. **Add PyPI API Token to GitHub Secrets**:
   - Go to your repository on GitHub
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token (starts with `pypi-`)
   - Click "Add secret"

2. **Create and Push a Version Tag**:
   ```bash
   # Update version in pyproject.toml first
   # Then create and push a tag
   git tag v0.1.0
   git push origin v0.1.0
   ```

   The workflow will automatically:
   - Build the package
   - Upload to PyPI
   - Create a GitHub release

### Version Tag Format

Tags must start with `v` followed by a version number (e.g., `v0.1.0`, `v1.2.3`).

## Automatic Version Bumping

The project includes tools to automatically bump version numbers in all relevant files.

### Using bump2version (Recommended)

1. **Install bump2version**:
   ```bash
   uv pip install -e ".[dev]"
   # or
   pip install bump2version
   ```

2. **Bump version**:
   ```bash
   # Bump patch version (0.1.0 → 0.1.1)
   bump2version patch

   # Bump minor version (0.1.0 → 0.2.0)
   bump2version minor

   # Bump major version (0.1.0 → 1.0.0)
   bump2version major
   ```

   This will automatically:
   - Update version in `pyproject.toml`
   - Update version in `src/storzandbickel_ble/__init__.py`
   - Create a git commit with the version change
   - Create a git tag (e.g., `v0.1.1`)

3. **Push changes**:
   ```bash
   git push origin main
   git push origin --tags
   ```

### Using the Custom Script

Alternatively, use the provided Python script:

```bash
# Bump patch version
python scripts/bump_version.py patch

# Bump minor version
python scripts/bump_version.py minor

# Bump major version
python scripts/bump_version.py major
```

This updates both files but doesn't create commits or tags automatically. You'll need to commit and tag manually:

```bash
git add pyproject.toml src/storzandbickel_ble/__init__.py
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main && git push origin vX.Y.Z
```

### Manual Version Update

If you prefer to update versions manually, edit both files:
- `pyproject.toml`: Update `version = "X.Y.Z"`
- `src/storzandbickel_ble/__init__.py`: Update `__version__ = "X.Y.Z"`

## Manual Deployment

If you prefer to deploy manually:

### 1. Update Version

Use one of the automatic version bumping methods described above, or manually update the version in both files:
- `pyproject.toml`: Update `version = "0.1.0"`
- `src/storzandbickel_ble/__init__.py`: Update `__version__ = "0.1.0"`

### 2. Build the Package

```bash
# Install build tools
uv pip install build twine

# Build the package
python -m build
```

This creates distribution files in the `dist/` directory:
- `storzandbickel_ble-0.1.0-py3-none-any.whl` (wheel)
- `storzandbickel_ble-0.1.0.tar.gz` (source distribution)

### 3. Test on TestPyPI (Optional but Recommended)

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ storzandbickel-ble
```

### 4. Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*
```

You'll be prompted for:
- Username: `__token__`
- Password: Your PyPI API token

Or set environment variables:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-api-token-here
twine upload dist/*
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.0.1): Bug fixes, backward compatible

## Pre-release Versions

For alpha, beta, or release candidates:

```toml
version = "0.1.0a1"  # Alpha
version = "0.1.0b1"  # Beta
version = "0.1.0rc1" # Release candidate
```

## Checklist Before Releasing

- [ ] Bump version using `bump2version patch/minor/major` or `python scripts/bump_version.py patch/minor/major`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run tests: `pytest`
- [ ] Run linting: `ruff check . && ruff format .`
- [ ] Run type checking: `mypy src/`
- [ ] Verify all tests pass with coverage: `pytest --cov`
- [ ] Build locally and test: `python -m build`
- [ ] Review `README.md` for accuracy
- [ ] Create git tag: `git tag v0.1.0`
- [ ] Push tag: `git push origin v0.1.0`

## Troubleshooting

### "Package already exists" Error

If you try to upload the same version twice, PyPI will reject it. You must:
1. Bump the version number in `pyproject.toml`
2. Create a new tag
3. Build and upload again

### Authentication Errors

- Ensure your API token is valid and has "Upload packages" scope
- Check that `TWINE_USERNAME` is set to `__token__` (with underscores)
- Verify the token hasn't expired

### Build Errors

- Ensure `hatchling` is installed: `uv pip install hatchling`
- Check that `pyproject.toml` is valid
- Verify all required files are included in the build

## Post-Release

After a successful release:

1. Verify installation: `pip install storzandbickel-ble==0.1.0`
2. Check PyPI page: https://pypi.org/project/storzandbickel-ble/
3. Update documentation if needed
4. Announce the release (GitHub releases, etc.)

