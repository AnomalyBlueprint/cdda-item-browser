import os
import sys
import json
import urllib.request
import zipfile
import io
import shutil
import struct
from datetime import datetime

def get_png_size(filepath):
    try:
        with open(filepath, 'rb') as f:
            head = f.read(24)
            if head.startswith(b'\x89PNG\r\n\x1a\n') and head[12:16] == b'IHDR':
                return struct.unpack('>II', head[16:24])
    except Exception:
        pass
    return None, None

SCRIPT_VERSION = 1
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

def extract_sprites(val):
    if isinstance(val, int):
        return [val] if val else []
    if isinstance(val, dict):
        s = val.get('sprite', 0)
        return [s] if s else []
    if isinstance(val, list):
        res = []
        for item in val:
            if isinstance(item, int) and item:
                res.append(item)
            elif isinstance(item, dict):
                s = item.get('sprite', 0)
                if s: res.append(s)
        return res
    return []

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
                
            current_sprite_offset = 0
                
            for sheet in tiles_arrays:
                file_name = sheet.get('file', '')
                sw = sheet.get('sprite_width', base_w)
                sh = sheet.get('sprite_height', base_h)
                
                sheet_start = sheet.get('sprite_offset', sheet.get('start', None))
                if sheet_start is not None:
                    current_sprite_offset = sheet_start
                    
                actual_start = current_sprite_offset
                
                if 'tiles' in sheet:
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
                            
                        fg = extract_sprites(tile.get('fg', 0))
                        bg = extract_sprites(tile.get('bg', 0))
                        
                        if len(fg) == 1: fg = fg[0]
                        elif len(fg) == 0: fg = 0
                        
                        if len(bg) == 1: bg = bg[0]
                        elif len(bg) == 0: bg = 0
                        
                        for i in ids:
                            ts_data[i] = {
                                "file": f"gfx/{tileset}/{file_name}",
                                "fg": fg,
                                "bg": bg,
                                "sw": sw,
                                "sh": sh,
                                "start": actual_start
                            }
                            
                if file_name:
                    img_path = os.path.join(tileset_path, file_name)
                    w, h = get_png_size(img_path)
                    if w and h and sw and sh:
                        current_sprite_offset += (w // sw) * (h // sh)
                        
                        
            if ts_data:
                sprite_index[tileset] = ts_data
                
        except Exception as e:
            print(f"    Error parsing {tileset}: {e}")
            
    out_path = os.path.join(target_dir, 'sprite_index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sprite_index, f, separators=(',', ':'))

def main():
    local_path_file = '.cdda_local_path'
    targets = []
    
    if os.path.exists(local_path_file):
        with open(local_path_file, 'r') as f:
            local_path = f.read().strip()
        if os.path.exists(local_path):
            print(f"Using local CDDA data from {local_path} instead of downloading...")
            targets = [{
                'tag_name': 'local_test',
                'name': 'Local Test Version',
                'prerelease': False,
                'published_at': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                'local_extract_dir': local_path
            }]
            
    if not targets:
        targets = fetch_releases()
        
    versions_info = []
    
    # Load existing versions to skip re-downloading
    existing_versions = {}
    if os.path.exists('public/versions.json'):
        try:
            with open('public/versions.json', 'r') as f:
                for v in json.load(f):
                    existing_versions[v['id']] = v
        except Exception:
            pass
            
    os.makedirs('public/versions', exist_ok=True)
    shutil.copy('ItemBrowser.html', 'public/index.html')
    if os.path.exists('manifest.json'): shutil.copy('manifest.json', 'public/')
    if os.path.exists('service-worker.js'): shutil.copy('service-worker.js', 'public/')
    if os.path.exists('icon.svg'): shutil.copy('icon.svg', 'public/')
    
    for idx, release in enumerate(targets):
        tag_name = release.get('tag_name', 'unknown')
        is_stable = not release.get('prerelease', False)
        
        version_id = 'latest_stable' if is_stable else tag_name
        version_name = release.get('name') or tag_name
        
        print(f"\n[{idx+1}/{len(targets)}] Processing {version_id} ({tag_name})...")
        
        published_at = release.get('published_at', datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        dt = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        build_time = dt.strftime("%Y-%m-%d %H:%M UTC")
        
        target_dir = f"public/versions/{version_id}"
        
        # Check cache
        if version_id in existing_versions and 'local_extract_dir' not in release:
            cached_v = existing_versions[version_id]
            if cached_v.get('build_time') == build_time and cached_v.get('script_version') == SCRIPT_VERSION and os.path.exists(target_dir):
                print("  Already up to date. Skipping download.")
                versions_info.append(cached_v)
                continue
        
        extract_dir = release.get('local_extract_dir')
        is_local_dir = extract_dir is not None
        
        if not is_local_dir:
            dl_url = find_asset(release)
            zip_path = f"{version_id}.zip"
            
            if not os.path.exists(zip_path):
                print(f"  Downloading {dl_url}...")
                try:
                    req = urllib.request.Request(dl_url, headers=HEADERS)
                    with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                except Exception as e:
                    print(f"  Failed to download {dl_url}: {e}")
                    continue
            else:
                print(f"  Using existing local {zip_path}...")
                
            print("  Extracting data/json and gfx...")
            extract_dir = f"extract_{version_id}"
            os.makedirs(extract_dir, exist_ok=True)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    for file in z.namelist():
                        if 'data/json/' in file or 'gfx/' in file:
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
            shutil.rmtree('data', ignore_errors=True)
            
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
            
        if not is_local_dir:
            shutil.rmtree(extract_dir)
        if os.path.exists('data'):
            shutil.rmtree('data', ignore_errors=True)
        if not is_local_dir and os.path.exists(zip_path):
            os.remove(zip_path)
        
        versions_info.append({
            "id": version_id,
            "name": version_name,
            "path": f"versions/{version_id}/",
            "build_time": build_time,
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "script_version": SCRIPT_VERSION
        })
        
    print("\nWriting versions.json...")
    with open('public/versions.json', 'w') as f:
        json.dump(versions_info, f, indent=2)
        
    print("Done!")

if __name__ == '__main__':
    main()
