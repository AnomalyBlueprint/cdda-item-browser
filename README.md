# CDDA Item & Sprite Browser

A blazing fast, lightweight, browser-based tool for tracking tileset and sprite completion in [Cataclysm: Dark Days Ahead (CDDA)](https://github.com/CleverRaven/Cataclysm-DDA).

## What is this?
This tool dynamically extracts metadata and sprite canvas renders across all 11 official CDDA tilesets and compiles them into a highly optimized JSON file. It allows developers and artists to quickly search for items, terrains, and monsters, instantly verifying which tilesets are missing sprites for a specific entity.

## How it works
Rather than forcing a browser to load and parse over 35,000 JSON game data files, this repository utilizes GitHub Actions to:
1. Automatically pull the latest Stable and Experimental releases from the official CDDA repository.
2. Run a custom Python script (`build_light_defs.py`) that strictly extracts rendering metadata (ID, Name, Symbol, Color, Mod, Looks Like).
3. Compress the data into a single `items_defs.json` (~1MB) per version.
4. Deploy a fast, static HTML/JS frontend that can hot-swap between game versions without downloading the entire game payload.

## Local Development
If you want to run this locally against your own CDDA installation:
1. Copy `build_light_defs.py` into your CDDA root directory (where the `data` and `gfx` folders are).
2. Run `python3 build_light_defs.py`.
3. Copy the generated `items_defs.json` and the `gfx` folder into this repository's root.
4. Start a local server: `python3 -m http.server 8000` and open `ItemBrowser.html`.

## Credits & AI Usage
This tool was conceptualized by the repository owner and engineered in collaboration with **Antigravity IDE** and **Agentic AI Models**. AI tools were actively utilized to assist in the architectural design, Python data parsing logic, and the UI/UX frontend implementation.

### License
This project operates under the **Creative Commons Attribution-ShareAlike 3.0 Unported (CC-BY-SA 3.0)** License, aligning with the official Cataclysm: Dark Days Ahead license, as it processes and displays game data and graphical assets derived from the original game.
