import os
import sys
import json
import urllib.request
import zipfile
import shutil
from datetime import datetime

HEADERS = {'User-Agent': 'CDDA-Item-Browser-CI'}
LATEST_URL = 'https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases/latest'
API_URL = 'https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases?per_page=10'

if 'GITHUB_TOKEN' in os.environ:
    HEADERS['Authorization'] = f"token {os.environ['GITHUB_TOKEN']}"

def fetch_releases():
    print("Fetching latest stable release...")
    targets = []
    
    try:
        req = urllib.request.Request(LATEST_URL, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            stable = json.loads(response.read().decode())
            targets.append(stable)
    except Exception as e:
        print(f"Warning: Could not fetch latest stable release: {e}")

    print("Fetching experimental releases...")
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        releases = json.loads(response.read().decode())
        
    experimental = [r for r in releases if r.get('prerelease')][:5]
    targets.extend(experimental)
    
    return targets

def find_asset(release):
    for asset in release.get('assets', []):
        name = asset['name'].lower()
        if 'windows' in name and ('graphics' in name or 'tiles' in name) and name.endswith('.zip'):
            return asset['browser_download_url']
    return release.get('zipball_url')

def generate_sprite_index(gfx_dir, target_dir):
    print("  Generating sprite_index.json...")
    sprite_index = {}
    
    if not os.path.exists(gfx_dir):
        print(f"    gfx dir not found: {gfx_dir}")
        return
        
    for tileset in os.listdir(gfx_dir):
        tileset_path = os.path.join(gfx_dir, tileset)
        config_path = os.path.join(tileset_path, 'tile_config.json')
        
        if not os.path.isdir(tileset_path) or not os.path.exists(config_path):
            continue
            
        try:
            with open(config_path, 'r', encoding='utf-8', errors='replace') as f:
                config = json.load(f)
                
            ts_data = {}
            base_w = 32
            base_h = 32
            
            if 'tile_info' in config and isinstance(config['tile_info'], list) and len(config['tile_info']) > 0:
                base_w = config['tile_info'][0].get('width', 32)
                base_h = config['tile_info'][0].get('height', 32)
                
            tiles_arrays = []
            if 'tiles-new' in config:
                tiles_arrays = config['tiles-new']
            elif 'tiles' in config:
                tiles_arrays = config['tiles']
                
            for sheet in tiles_arrays:
                file_name = sheet.get('file', '')
                sw = sheet.get('sprite_width', base_w)
                sh = sheet.get('sprite_height', base_h)
                
                if 'tiles' not in sheet:
                    continue
                    
                for tile in sheet['tiles']:
                    t_id = tile.get('id')
                    if not t_id:
                        continue
                        
                    if isinstance(t_id, str):
                        ids = [t_id]
                    elif isinstance(t_id, list):
                        ids = t_id
                    else:
                        continue
                        
                    fg = tile.get('fg', 0)
                    bg = tile.get('bg', 0)
                    
                    if isinstance(fg, list): fg = fg[0]
                    if isinstance(bg, list): bg = bg[0]
                    
                    if isinstance(fg, dict): fg = fg.get('weight', 0) or 0
                    
                    for i in ids:
                        # Sometimes CDDA puts nested arrays or dicts, if so just cast to string or 0
                        if isinstance(fg, (list, dict)): fg = 0
                        if isinstance(bg, (list, dict)): bg = 0
                        
                        ts_data[i] = {
                            "file": file_name,
                            "fg": fg,
                            "bg": bg,
                            "sw": sw,
                            "sh": sh
                        }
                        
            if ts_data:
                sprite_index[tileset] = ts_data
                
        except Exception as e:
            print(f"    Error parsing {tileset}: {e}")
            
    out_path = os.path.join(target_dir, 'sprite_index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sprite_index, f, separators=(',', ':'))

def main():
    targets = fetch_releases()
    versions_info = []
    
    os.makedirs('public/versions', exist_ok=True)
    shutil.copy('ItemBrowser.html', 'public/index.html')
    
    for idx, release in enumerate(targets):
        tag_name = release.get('tag_name', 'unknown')
        is_stable = not release.get('prerelease', False)
        
        version_id = 'latest_stable' if is_stable else tag_name
        version_name = release.get('name') or tag_name
        
        print(f"\n[{idx+1}/{len(targets)}] Processing {version_id} ({tag_name})...")
        
        dl_url = find_asset(release)
        zip_path = f"{version_id}.zip"
        
        print(f"  Downloading {dl_url}...")
        try:
            req = urllib.request.Request(dl_url, headers=HEADERS)
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(f"  Failed to download {dl_url}: {e}")
            continue
            
        print("  Extracting data/json and gfx...")
        extract_dir = f"extract_{version_id}"
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for file in z.namelist():
                    if '/data/json/' in file or '/gfx/' in file:
                        z.extract(file, extract_dir)
        except Exception as e:
            print(f"  Failed to extract zip: {e}")
            if os.path.exists(zip_path): os.remove(zip_path)
            continue
            
        source_data_json = None
        source_gfx = None
        for root, dirs, files in os.walk(extract_dir):
            if 'json' in dirs and os.path.basename(root) == 'data':
                source_data_json = os.path.join(root, 'json')
            if 'gfx' in dirs:
                source_gfx = os.path.join(root, 'gfx')
                
        if os.path.exists('data'):
            shutil.rmtree('data')
            
        if source_data_json:
            os.makedirs('data/json', exist_ok=True)
            for item in os.listdir(source_data_json):
                s = os.path.join(source_data_json, item)
                d = os.path.join('data/json', item)
                if os.path.isdir(s): shutil.copytree(s, d)
                else: shutil.copy2(s, d)
                
        print("  Running build_light_defs.py...")
        os.system(f"{sys.executable} build_light_defs.py")
        
        target_dir = f"public/versions/{version_id}"
        os.makedirs(target_dir, exist_ok=True)
        
        if os.path.exists('items_defs.json'):
            shutil.move('items_defs.json', os.path.join(target_dir, 'items_defs.json'))
            
        if source_gfx:
            target_gfx = os.path.join(target_dir, 'gfx')
            if os.path.exists(target_gfx):
                shutil.rmtree(target_gfx)
            shutil.copytree(source_gfx, target_gfx)
            generate_sprite_index(target_gfx, target_dir)
            
        shutil.rmtree(extract_dir)
        if os.path.exists('data'):
            shutil.rmtree('data')
        os.remove(zip_path)
        
        published_at = release.get('published_at', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        build_time = dt.strftime("%Y-%m-%d %H:%M UTC")
        
        versions_info.append({
            "id": version_id,
            "name": version_name,
            "path": f"versions/{version_id}/",
            "build_time": build_time
        })
        
    print("\nWriting versions.json...")
    with open('public/versions.json', 'w') as f:
        json.dump(versions_info, f, indent=2)
        
    print("Done!")

if __name__ == '__main__':
    main()
