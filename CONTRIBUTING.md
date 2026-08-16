# Contributing to CDDA Item & Sprite Browser

Thanks for your interest in contributing! This is a lightweight, static web app — no build tools or frameworks required.

## Project Structure

```
ItemBrowser.html          # The entire frontend (single file — HTML + CSS + JS)
build_light_defs.py       # Extracts item definitions from CDDA data/json/
scripts/update_data.py    # CI/CD script: downloads CDDA releases, generates versions/
.github/workflows/        # GitHub Actions: runs update_data.py nightly
```

## How Data Flows

1. GitHub Actions runs `scripts/update_data.py` nightly.
2. It downloads CDDA Windows release ZIPs (which include pre-built `gfx/` tilesets).
3. It extracts `data/json/` → runs `build_light_defs.py` → `items_defs.json`
4. It parses each tileset's `tile_config.json` → `sprite_index.json`
5. All output goes to `public/versions/<version_id>/` and is deployed to `gh-pages`.

## Running Locally

You **must** serve via HTTP (not `file://`) due to `fetch()` calls:

```bash
python3 -m http.server 8000
# Then open http://localhost:8000
```

To regenerate local data (requires an internet connection):

```bash
python3 scripts/update_data.py
python3 -m http.server 8000
```

## Making Changes

### Frontend (`ItemBrowser.html`)
- Pure HTML/CSS/JS, no build step.
- Edit the file and refresh the browser.
- Test at multiple viewport widths (desktop, tablet, mobile).

### Data Pipeline (`scripts/update_data.py`)
- To test without pushing, run `python3 scripts/update_data.py` locally.
- It will download ~200MB of data on first run (cached in `public/`).
- The `public/` directory is gitignored — it's generated, not committed.

## Pull Request Guidelines

- Keep PRs focused on a single change.
- For frontend changes: include a screenshot if it affects the UI.
- For pipeline changes: describe what data changed and why.
- Don't commit anything inside `public/` or `versions/` — those are CI-generated.

## Reporting Issues

Please open a GitHub Issue with:
- What you expected to see
- What you actually saw
- Your browser and OS
- A screenshot if the issue is visual
