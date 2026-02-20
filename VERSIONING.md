# Versioning & Release Guide

This project uses **Semantic Versioning** (SemVer) as defined by [semver.org](https://semver.org/).

## Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

- **MAJOR**: Breaking changes to API or Home Assistant compatibility
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, backward-compatible
- **PRERELEASE**: `-alpha`, `-beta`, `-rc` for pre-release versions
- **BUILD**: Optional build metadata (not used in releases)

## Current Version

Version **0.1.0-beta.1** — First stable beta release.

## Where Version is Defined

Version must stay in sync across:
1. `manifest.json` — Home Assistant integration metadata
2. `pyproject.toml` — Python package version
3. Git tags — Release tracking

## Cutting a Release

### 1. Update Version

Edit both files to new version (e.g., `0.1.0-beta.2` or `0.1.0`):

```bash
# Update manifest.json
# Update pyproject.toml
```

### 2. Update CHANGELOG

Add new section at top of `CHANGELOG.md`:

```markdown
## [0.1.0] - 2026-02-20

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Breaking or significant change description
```

### 3. Commit Changes

```bash
git add manifest.json pyproject.toml CHANGELOG.md
git commit -m "Release version 0.1.0"
```

### 4. Create Git Tag

```bash
git tag -a v0.1.0 -m "Release v0.1.0: SMS inbox management with Lovelace card"
git push origin v0.1.0
```

### 5. Create GitHub Release

Use the tag to create a release on GitHub with:
- Title: `v0.1.0`
- Body: Copy the relevant section from `CHANGELOG.md`
- Attach any release notes or migration guides

## Pre-Release Versions

For beta/RC versions, use:

```bash
git tag -a v0.1.0-beta.2 -m "Release v0.1.0-beta.2: Bug fixes"
```

## Version Bump Decisions

### When to bump MAJOR
- Breaking changes to config flow
- Dropping support for older Home Assistant versions
- API changes to services/events that require automation updates

### When to bump MINOR
- New services or features
- New Lovelace card capabilities
- New configuration options (backward-compatible)

### When to bump PATCH
- Bug fixes
- Performance improvements
- Documentation updates
- UI refinements

## Automation (Future)

Consider setting up GitHub Actions to:
- Validate version consistency across files
- Auto-create releases on tag push
- Publish to HACS automatically
