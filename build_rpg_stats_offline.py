import json
import glob
import os

data_dir = './data/json'
output_file = './items_defs.json'

# Step 1: Read all JSON objects into a raw dictionary mapped by ID
raw_data = {}
print("Reading JSON files...")

for root_dir, dirs, files in os.walk(data_dir):
    for filename in files:
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(root_dir, filename)
        
        # Determine the mod name (fallback to __core__)
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
                            # Attach the mod name and source file so we know where it came from
                            item['_mod'] = mod_name
                            raw_data[item_id] = item
        except Exception as e:
            pass

print(f"Loaded {len(raw_data)} raw objects.")

# Step 2: Function to resolve `copy-from` inheritance
def resolve_object(obj_id, depth=0):
    if depth > 10 or obj_id not in raw_data:
        return {}
    
    obj = raw_data[obj_id]
    
    if '_resolved' in obj:
        return obj['_resolved']
        
    parent_id = obj.get('copy-from')
    if parent_id and parent_id in raw_data:
        parent_obj = resolve_object(parent_id, depth + 1)
        # Deep merge
        merged = {}
        # Simple merge logic: copy parent, then overwrite/append from child
        # For simplicity, we just do a shallow copy then overwrite, but for lists we can try to merge if needed.
        # CDDA actual inheritance rules are complex (proportional, relative, extend, delete), 
        # but for viewing stats, a simple shallow merge is usually enough.
        merged.update(parent_obj)
        for k, v in obj.items():
            if k == 'extend' and isinstance(v, dict):
                for ek, ev in v.items():
                    if ek in merged and isinstance(merged[ek], list) and isinstance(ev, list):
                        merged[ek].extend(ev)
            elif k == 'delete' and isinstance(v, dict):
                 pass # skip complex deletes for now
            else:
                merged[k] = v
                
        obj['_resolved'] = merged
        return merged
    else:
        obj['_resolved'] = obj
        return obj

print("Resolving inheritance...")
resolved_data = {}
for obj_id in raw_data:
    resolved_data[obj_id] = resolve_object(obj_id)

# Step 3: Extract relevant stats into a compact structure
compact_defs = {}
print("Building compact stats index...")

def parse_name(name_field):
    if isinstance(name_field, str):
        return name_field
    elif isinstance(name_field, dict):
        return name_field.get('str_sp', name_field.get('str', name_field.get('str_pl', '')))
    return ''

for obj_id, item in resolved_data.items():
    t = item.get('type')
    if not t: continue
    
    # We only care about major visible types for the browser
    if t not in ['ITEM', 'terrain', 'furniture', 'MONSTER', 'vehicle_part', 'AMMO', 'ARMOR', 'WEAPON', 'TOOL', 'GUN', 'BIONIC', 'mutation']:
        # If it's a sub-type of item, map it to ITEM for the frontend categorization
        if t in ['AMMO', 'ARMOR', 'WEAPON', 'TOOL', 'GUN', 'BIONIC']:
            t = 'ITEM'
        else:
            continue
            
    if t not in compact_defs:
        compact_defs[t] = {}
        
    name = parse_name(item.get('name', ''))
    if not name:
        name = item.get('id', '')
        
    # Basic fields
    entry = {
        'n': name,
        's': item.get('symbol', item.get('sym', '')),
        'c': item.get('color', ''),
        'L': item.get('looks_like', ''),
        'mod': item.get('_mod', '__core__'),
        'desc': item.get('description', ''),
        'vol': item.get('volume', ''),
        'wt': item.get('weight', ''),
        'mat': item.get('material', []),
        'flags': item.get('flags', [])
    }
    
    # Specific fields based on original type
    orig_type = item.get('type')
    if orig_type == 'MONSTER':
        entry['hp'] = item.get('hp', 0)
        entry['speed'] = item.get('speed', 0)
        entry['dodge'] = item.get('dodge', 0)
        
        # Armor
        entry['ar_bash'] = item.get('armor_bash', 0)
        entry['ar_cut'] = item.get('armor_cut', 0)
        entry['ar_stab'] = item.get('armor_stab', 0)
        entry['ar_bullet'] = item.get('armor_bullet', 0)
        entry['ar_acid'] = item.get('armor_acid', 0)
        entry['ar_fire'] = item.get('armor_fire', 0)
        
        # Attack
        entry['m_skill'] = item.get('melee_skill', 0)
        entry['m_dice'] = item.get('melee_dice', 0)
        entry['m_sides'] = item.get('melee_dice_sides', 0)
        entry['m_cut'] = item.get('melee_cut', 0)
        
        # Behavior
        entry['aggro'] = item.get('aggression', 0)
        entry['morale'] = item.get('morale', 0)
        entry['vis_day'] = item.get('vision_day', 0)
        entry['vis_night'] = item.get('vision_night', 0)
        entry['faction'] = item.get('default_faction', '')
        entry['body'] = item.get('bodytype', '')
        entry['species'] = item.get('species', [])
        
        # Upgrades & death
        upg = item.get('upgrades', {})
        if isinstance(upg, dict) and 'into' in upg:
            entry['upgrades'] = f"into {upg.get('into')} in {upg.get('half_life', upg.get('age_grow', '?'))} days"
            
        df = item.get('death_function', {})
        if isinstance(df, dict) and 'message' in df:
            entry['on_death'] = df.get('message', '')
            
        entry['harvest'] = item.get('harvest', '')
        entry['fear'] = item.get('fear_triggers', [])
        
    elif orig_type in ['ITEM', 'ARMOR', 'WEAPON', 'TOOL', 'GUN', 'AMMO']:
        entry['bash'] = item.get('bashing', 0)
        entry['cut'] = item.get('cutting', 0)
        entry['to_hit'] = item.get('to_hit', 0)
        
        if orig_type == 'ARMOR':
            if 'armor' in item:
                entry['armor_data'] = item['armor']
            entry['covers'] = item.get('covers', [])
            
        if orig_type == 'GUN':
            entry['dmg'] = item.get('damage', {})
            entry['range'] = item.get('range', 0)
            entry['dispersion'] = item.get('dispersion', 0)
            entry['ammo'] = item.get('ammo', [])
    
    # Remove empty fields to save space
    clean_entry = {k: v for k, v in entry.items() if v != '' and v != [] and v != 0 and v != {}}
    
    compact_defs[t][obj_id] = clean_entry

# Step 4: Extract mods metadata
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
print(f"Writing detailed index to {output_file}...")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(out_wrapper, f, separators=(',', ':'))

size_kb = os.path.getsize(output_file) / 1024
print(f"Done! {output_file} is {size_kb:.0f} KB.")
