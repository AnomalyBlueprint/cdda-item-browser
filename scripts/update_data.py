import os
import sys
import json
import urllib.request
import zipfile
import shutil
from datetime import datetime

HEADERS = {'User-Agent': 'CDDA-Item-Browser-CI'}
API_URL = 'https://api.github.com/repos/CleverRaven/Cataclysm-DDA/releases?per_page=30'

if 'GITHUB_TOKEN' in os.environ:
    HEADERS['Authorization'] = f"token {os.environ['GITHUB_TOKEN']}"

def fetch_releases():
    print("Fetching releases...")
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        releases = json.loads(response.read().decode())
        
    stable = next((r for r in releases if not r['prerelease']), None)
    experimental = [r for r in releases if r['prerelease']][:5]
    
    targets = []
    if stable: targets.append(stable)
    targets.extend(experimental)
    return targets

def main():
    targets = fetch_releases()
    versions_info = []
    
    os.makedirs('public/versions', exist_ok=True)
    shutil.copy('ItemBrowser.html', 'public/index.html')
    
    for idx, release in enumerate(targets):
        tag_name = release['tag_name']
        is_stable = not release['prerelease']
        
        version_id = 'latest_stable' if is_stable else tag_name
        version_name = release['name'] if release['name'] else tag_name
        
        print(f"\n[{idx+1}/{len(targets)}] Processing {version_id} ({tag_name})...")
        
        zip_url = release['zipball_url']
        zip_path = f"{version_id}.zip"
        
        print(f"  Downloading {zip_url}...")
        req = urllib.request.Request(zip_url, headers=HEADERS)
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print("  Extracting data/json and gfx...")
        extract_dir = f"extract_{version_id}"
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            root_folder = z.namelist()[0].split('/')[0]
            for file in z.namelist():
                if file.startswith(f"{root_folder}/data/json/") or file.startswith(f"{root_folder}/gfx/"):
                    z.extract(file, extract_dir)
                    
        # Setup data for build_light_defs.py
        if os.path.exists('data'):
            shutil.rmtree('data')
        
        source_data_json = os.path.join(extract_dir, root_folder, 'data', 'json')
        os.makedirs('data/json', exist_ok=True)
        if os.path.exists(source_data_json):
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
            
        source_gfx = os.path.join(extract_dir, root_folder, 'gfx')
        if os.path.exists(source_gfx):
            shutil.copytree(source_gfx, os.path.join(target_dir, 'gfx'), dirs_exist_ok=True)
            
        shutil.rmtree(extract_dir)
        if os.path.exists('data'):
            shutil.rmtree('data')
        os.remove(zip_path)
        
        published_at = release['published_at']
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
