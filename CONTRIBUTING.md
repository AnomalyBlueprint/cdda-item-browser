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

You **must** serve via HTTP (not `file://`) due to `fetch()` calls and Service Worker registration:

```bash
python3 -m http.server 8000
# Then open http://localhost:8000/ItemBrowser.html
```

To regenerate local data (requires an internet connection by default):

```bash
python3 scripts/update_data.py
python3 -m http.server 8000
```

### Fast Offline Testing
If you are developing the Python pipeline and don't want to wait for 200MB ZIP downloads from the GitHub API:
1. Extract your local copy of the game.
2. Create `.cdda_local_path` in the project root containing the absolute path to that extracted folder.
3. Run `python3 scripts/update_data.py`. It will instantly bypass downloads and parse your local files.

## Making Changes

### Frontend (`ItemBrowser.html` & PWA files)
- The app is a Progressive Web App (PWA) with offline capabilities.
- When making frontend changes to `ItemBrowser.html`, you might need to bypass the Service Worker cache. In Chrome DevTools, go to **Application > Service Workers** and check **Bypass for network**, or hold Shift while refreshing.
- Do not edit files inside `public/` directly for development. Edit the source files (`ItemBrowser.html`, `manifest.json`, `service-worker.js`), and they will be copied to `public/` when `update_data.py` runs.
- Test at multiple viewport widths (desktop, tablet, mobile).

### Data Pipeline (`scripts/update_data.py`)
- To test without pushing, run `python3 scripts/update_data.py` locally.
- It will download ~200MB of data on first run (cached in `public/`), unless bypassed using `.cdda_local_path`.
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

