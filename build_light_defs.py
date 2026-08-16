import json
import glob
import os

data_dir = './data/json'
output_file = './items_defs.json'

raw_data = {}
print("Reading JSON files for lightweight extraction...")

for root_dir, dirs, files in os.walk(data_dir):
    for filename in files:
        if not filename.endswith('.json') or filename == 'modinfo.json':
            continue
        filepath = os.path.join(root_dir, filename)
        
        mod_name = '__core__'
        rel_path = os.path.relpath(filepath, data_dir)
        if rel_path.startswith('mods/'):
            parts = rel_path.split('/')
            if len(parts) > 1:
                mod_name = parts[1]
                
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
                arr = data if isinstance(data, list) else [data]
                for item in arr:
                    if isinstance(item, dict) and 'id' in item and 'type' in item:
                        item_id = item['id']
                        if isinstance(item_id, str):
                            item['_mod'] = mod_name
                            raw_data[item_id] = item
        except Exception as e:
            pass

print(f"Loaded {len(raw_data)} raw objects.")
compact_defs = {}

def parse_name(name_field):
    if isinstance(name_field, str):
        return name_field
    elif isinstance(name_field, dict):
        return name_field.get('str_sp', name_field.get('str', name_field.get('str_pl', '')))
    return ''

for obj_id, item in raw_data.items():
    t = item.get('type')
    if not t: continue
    
    if t not in ['ITEM', 'terrain', 'furniture', 'MONSTER', 'vehicle_part', 'AMMO', 'ARMOR', 'WEAPON', 'TOOL', 'GUN', 'BIONIC', 'mutation']:
        if t in ['AMMO', 'ARMOR', 'WEAPON', 'TOOL', 'GUN', 'BIONIC']:
            t = 'ITEM'
        else:
            continue
            
    if t not in compact_defs:
        compact_defs[t] = {}
        
    name = parse_name(item.get('name', ''))
    if not name:
        name = item.get('id', '')
        
    entry = {
        'n': name,
        's': item.get('symbol', item.get('sym', '')),
        'c': item.get('color', ''),
        'L': item.get('looks_like', ''),
        'mod': item.get('_mod', '__core__')
    }
    
    clean_entry = {k: v for k, v in entry.items() if v != ''}
    compact_defs[t][obj_id] = clean_entry

print("Extracting mods info...")
mods_list = []
for root_dir, dirs, files in os.walk(data_dir):
    for filename in files:
        if filename == 'modinfo.json':
            filepath = os.path.join(root_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    data = json.load(f)
                    arr = data if isinstance(data, list) else [data]
                    for item in arr:
                        if isinstance(item, dict) and item.get('type') == 'MOD_INFO':
                            mods_list.append({
                                'id': item.get('id', ''),
                                'name': parse_name(item.get('name', item.get('id', ''))),
                                'category': item.get('category', 'unknown')
                            })
            except: pass

out_wrapper = {'types': compact_defs, 'mods': mods_list}
print(f"Writing lightweight index to {output_file}...")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(out_wrapper, f, separators=(',', ':'))

size_kb = os.path.getsize(output_file) / 1024
print(f"Done! {output_file} is {size_kb:.0f} KB.")
