# Versioning

Porypal now has a single human-editable version source:

```text
VERSION
```

Do not hand-edit the scattered `vX.Y`, `X.Y`, and `X.Y.Z` strings anymore. Use the helper script instead.

## Show the current version

```bash
python scripts/bump_version.py --show
```

## Set an exact version

```bash
python scripts/bump_version.py 3.2.0
python scripts/bump_version.py v3.2.0
```

That updates:

- `VERSION`
- `pyproject.toml`
- `model/__init__.py`
- `server/app.py`
- `server/api/pipeline.py`
- `main.py` display banner (`v3.2`)
- `frontend/index.html` title (`v3.2`)
- `frontend/src/tabs/HomeTab.jsx` display strings (`v3.2`)
- `frontend/package.json`
- `frontend/package-lock.json`

## Bump patch / minor / major

```bash
python scripts/bump_version.py --patch
python scripts/bump_version.py --minor
python scripts/bump_version.py --major
```

These can be combined with release actions too:

```bash
python scripts/bump_version.py --patch --commit --tag --push
python scripts/bump_version.py --minor --commit --tag --push
```

Examples from the current `3.1.1` baseline:

- `3.1.1` + `--patch` -> `3.1.2`
- `3.1.1` + `--minor` -> `3.2.0`
- `3.1.1` + `--major` -> `4.0.0`

## Create the release commit and tag

```bash
python scripts/bump_version.py 3.2.0 --commit --tag
```

That creates:

- commit: `release: v3.2.0`
- tag: `v3.2.0`

## Push the branch and tag

```bash
python scripts/bump_version.py 3.2.0 --commit --tag --push
```

By default this pushes to `origin`.

Use a different remote if needed:

```bash
python scripts/bump_version.py 3.2.0 --commit --tag --push --remote upstream
```

## Recommended release flow

```bash
python scripts/bump_version.py --show
python scripts/bump_version.py --patch --commit --tag --push
```

## Notes

- `--push` will push both `HEAD` and the matching `vX.Y.Z` tag.
- The release workflow is already tag-driven, so pushing `v3.2.0` is what kicks off GitHub Releases.
- Commit/tag/push mode expects a clean git worktree before it runs.
- Full project version strings use `X.Y.Z`, while short display strings like the app banner/title use `vX.Y`.
