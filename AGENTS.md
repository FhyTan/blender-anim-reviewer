# AGENTS.md

## Quick start

```bash
uv sync                 # install all deps (including dev)
uv run pytest           # run tests (requires bpy/Blender Python env)
```

## Project structure

Single-package Blender add-on (extension). No monorepo.

| Path | Purpose |
|---|---|
| `anim_reviewer/` | Add-on root, matches `blender_manifest.toml` |
| `anim_reviewer/__init__.py` | Entrypoint: `register()`/`unregister()` |
| `anim_reviewer/operators.py` | Main operator (`bpy.ops.render.anim_review`) |
| `anim_reviewer/properties.py` | RNA property groups (`VideoProperties`, `OverrideProperties`, `MetadataProperties`, `SettingsProperties`) |
| `anim_reviewer/panels.py` | UI panel (3D Viewport > N-panel > Tool > Anim Reviewer) |
| `anim_reviewer/utils.py` | FFmpeg detection, video playback (`play_video`) |
| `anim_reviewer/metadata.py` | Overlay burn-in metadata generation |
| `anim_reviewer/handlers.py` | Blender event handlers |
| `anim_reviewer/paths.py` | Path constants (`BFONT_PATH`, `TEMPLATE_ASS_PATH`, `TEMPORARY_OUTPUT_DIR`) |
| `tests/test_anim_reviewer.py` | Integration tests requiring bpy |

## Key commands

```bash
uv sync                          # install/update deps
uv run pytest                    # run all tests
uv run pytest tests/test_anim_reviewer.py -k test_name  # single test
uv run pytest -x --timeout=60    # fail-fast with timeout
blender --command extension build --source-dir ./anim_reviewer --output-dir ./dist  # build extension zip
```

## Build

```bash
build.bat  # or run the blender extension build command above
```

Output goes to `dist/`.

## Dependencies

- **Runtime**: `fonttools>=4.60.1` (bundled as wheel in `anim_reviewer/wheels/`)
- **Dev**: `bpy`, `fake-bpy-module`, `pytest`
- **System**: FFmpeg (must be on PATH, required for video processing)

## Testing quirks

- Tests require a real or mock Blender Python environment (`bpy` module). They **cannot** run standalone without `bpy` or `fake-bpy-module`.
- Test fixture `new_scene` (autouse) creates a fresh scene before each test.
- Test fixture `create_camera_and_cube` sets up a minimal scene with camera and tracked cube.
- Playblast test (`test_playblast_with_different_system_output_file_format`) is skipped on Blender >= 5.0.

> **Note**: Do not run `pytest` during development — the test environment (`bpy` 311MiB download) is not yet set up and will hang the session. Tests are only run in CI or by the developer locally.

## UV (package manager)

This project uses `uv` (not pip). Lockfile: `uv.lock`. Python requirement: `>=3.11` (`.python-version`).

- Add runtime dep: `uv add fonttools`
- Add dev dep: `uv add --dev pytest`

## Environment

- VSCode settings in `.vscode/settings.json` configure `BLENDER_USER_RESOURCES` to `.blender_dev/` and pytest args.
- `.gitignore` ignores `.venv/`, `dist/`, `blender/`, `i18n/`, `.vscode/`, `.blender_dev/`.

## Language

All code, comments, docstrings, and logging must be in English. Non-English text is only permitted in `anim_reviewer/translations.py`.

## Translations

Translations are in `anim_reviewer/translations.py` as auto-generated Blender i18n tuples. Currently has `zh_HANS` (Chinese Simplified). The comment at the top says the block can be safely moved and edited by hand.

## Version

Current: `1.0.3` (in both `pyproject.toml` and `blender_manifest.toml`).
