# Versioning Guide

Flashy uses **git tags** for versioning and **automated releases** via GitHub Actions.

## How It Works

1. **You push to main** → GitHub Actions runs tests
2. **Tests pass** → Auto-increments version and creates release ✅
3. **Tests fail** → Push blocked, no release ❌

**Version auto-increments:** v1.0.0 → v1.0.1 → v1.0.2 (patch bump)

## Creating a Release

### Simple Method (Auto-Increment)

```bash
# Just push to main - version auto-bumps
git add .
git commit -m "Add new feature"
git push origin main

# GitHub Actions:
# ✅ Runs tests
# ✅ Auto-increments: v1.0.5 → v1.0.6
# ✅ Creates release
```

### Manual Version Control

If you want to bump major/minor instead of patch:

```bash
# Create tag manually before pushing
git tag v2.0.0
git push origin main --tags

# GitHub Actions:
# ✅ Runs tests
# ✅ Uses your tag: v2.0.0
# ✅ Creates release
```

## Version Display

Users see the version on homepage:
- Comes from latest git tag
- Fallback to "dev" if no tags
- Shows as "Flashy v1.0.6"

With `FIXES=true`, also shows CHANGELOG.md content.

## Changelog

Update `CHANGELOG.md` with your changes:

```markdown
# Changelog

## Latest Release

### Added
- New awesome feature
- Another cool thing

### Fixed
- Bug fix description
```

**No version numbers needed** - they come from git tags!

## Branch Protection (Recommended)

Force tests before merging:

1. GitHub repo → Settings → Branches
2. Add rule for `main` branch
3. Enable "Require status checks to pass"
4. Select "test" as required check

## Deploying Specific Versions

```bash
# Latest
git clone https://github.com/yourusername/flashy.git

# Specific version
git clone --branch v1.0.5 https://github.com/yourusername/flashy.git
```

## Examples

```bash
# Scenario 1: Quick bug fix
git commit -m "Fix URL rewriting bug"
git push
# → v1.0.5 → v1.0.6 (auto)

# Scenario 2: New feature (minor bump)
git tag v1.1.0
git push --tags
# → v1.1.0 (manual tag)

# Scenario 3: Breaking change (major bump)
git tag v2.0.0
git push --tags
# → v2.0.0 (manual tag)
```

## Notes

- **Default:** Auto-increments patch (v1.0.0 → v1.0.1)
- **Manual tags:** Use for major/minor bumps
- **Tests required:** No passing tests = no release
- **One release per tag:** Existing tags won't re-release

---

**Keep it simple - let git tags handle versioning!** 📦