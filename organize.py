import os
import re
import shutil
import yaml
import json

# === CONFIGURATION ===
VAULT_ROOT = "obsidian_vault"
CATEGORY_RULES = {
    "characters": "1_People",
    "locations": "2_Locations",
    "factions": "3_Factions",
    "items": "4_Items",
    "magic": "5_Magic",
    "lore": "6_Lore",
    "races": "7_Races",
    "creatures": "8_Beastiary",
    "dragons": "1_People",
    "elves": "7_Races",
    "events": "6_Lore",
}

INFBOX_TO_CATEGORY_KEY = {
    "character": "characters",
    "location": "locations",
    "faction": "factions",
    "item": "items",
}

DEFAULT_FOLDER = "9_Miscellaneous"

SUBCATEGORY_RULES = {
    "2_Locations": {
        "cities": "Cities",
        "towns": "Towns",
        "inns": "Establishments",
        "brothels": "Establishments",
        "fighting pits": "Establishments",
        "nations": "Nations",
        "wilderness": "Wilderness",
        "forests": "Wilderness",
        "mountains": "Wilderness",
        "seas": "Wilderness",
        "ruins": "Ruins",
        "continents": "Continents",
        "roads": "Roads",
        "fortifications": "Fortifications",
    },
    "3_Factions": {
        "nobility": "Nobility",
    },
    "4_Items": {
        "weapons": "Weapons",
        "armor": "Armor",
        "minerals": "Minerals",
        "flora": "Flora",
    },
    "6_Lore": {
        "history": "History",
        "mythology": "Mythology",
        "languages": "Languages",
        "religion": "Religion",
        "conflicts": "Conflicts",  # Consolidated wars/battles here
        "events": "Events",
        "holidays": "Holidays",
    },
}

# Unified tag consolidation mapping
TAG_CONSOLIDATION = {
    # Fortifications
    "forts": "fortifications",
    "castles": "fortifications",

    "institutions": "factions",
    "organisations": "factions",
    "military units": "factions",
    "mercenary bands": "factions",

    "noble houses": "nobility",
    "notable families": "factions",

    # Settlements
    "settlement": "towns",
    "towns_and_villages": "towns",
    "towns and villages": "towns",

    # Geography
    "mountain ranges": "mountains",
    "mountain_ranges": "mountains",
    "territorial_regions": "nations",
    "territorial regions": "nations",

    # Conflicts
    "wars": "conflicts",
    "battles": "conflicts"
}

YAML_FRONTMATTER_REGEX = re.compile(r"(?s)^---\n(.*?)\n---\n")

# === FUNCTIONS ===

def display_title(title):
    """Convert to human-readable title with spaces"""
    return title.replace('_', ' ')

def parse_yaml_frontmatter(filepath):
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ Failed to read {filepath}: {e}")
        return {}

    match = YAML_FRONTMATTER_REGEX.match(content)
    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except Exception as e:
        print(f"⚠️ YAML parse error in {filepath}: {e}")
        return {}

def write_yaml_frontmatter(filepath, data, original_content):
    new_yaml = yaml.safe_dump(data, sort_keys=False).strip()
    def replacer(match):
        return f"---\n{new_yaml}\n---\n"
    new_content = YAML_FRONTMATTER_REGEX.sub(replacer, original_content, count=1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

def consolidate_tags(tags):
    """Apply all tag consolidation rules and remove replaced tags"""
    consolidated = set()
    replacements = set()

    # First normalize all input tags (lowercase, replace underscores with spaces)
    normalized_input_tags = {tag.lower().replace('_', ' ').strip() for tag in tags}

    # Process each input tag
    for input_tag in normalized_input_tags:
        # Find the replacement (if any exists)
        replacement = TAG_CONSOLIDATION.get(input_tag, input_tag)

        # Add the replacement to our consolidated set
        consolidated.add(replacement)

        # If this tag was replaced, track the original
        if replacement != input_tag:
            replacements.add(input_tag)

    # Now remove any tags that were replaced
    final_tags = [tag for tag in consolidated if tag not in replacements]

    # Convert back to the original tag format (with underscores if that was original)
    def restore_formatting(tag):
        # Check if original used underscores
        for original_tag in tags:
            if original_tag.lower().replace('_', ' ') == tag:
                return original_tag.lower()  # preserve original formatting
        return tag.replace(' ', '_')  # default to underscores

    return sorted(restore_formatting(tag) for tag in final_tags)

def add_parent_tags_for_subcategories(tags):
    """Add missing parent category tags based on SUBCATEGORY_RULES"""
    tags_lower = set(t.lower() for t in tags if isinstance(t, str))

    # Build mapping of subcategory tags to their parent categories
    subcat_to_parent = {}
    for parent_folder, subcats in SUBCATEGORY_RULES.items():
        parent_tags = [k for k, v in CATEGORY_RULES.items() if v == parent_folder]
        for subcat_tag in subcats.keys():
            for ptag in parent_tags:
                subcat_to_parent[subcat_tag.lower()] = ptag.lower()

    # Add any missing parent tags
    added_tags = False
    for tag in tags_lower.copy():
        if tag in subcat_to_parent:
            parent_tag = subcat_to_parent[tag]
            if parent_tag not in tags_lower:
                tags_lower.add(parent_tag)
                added_tags = True

    return list(tags_lower), added_tags

def classify_file(yaml_data):
    infobox = yaml_data.get("infobox", "")
    tags = yaml_data.get("tags") or []

    # Get category from infobox if available
    infobox_key = ""
    if isinstance(infobox, str):
        infobox_key = INFBOX_TO_CATEGORY_KEY.get(infobox.lower().strip(), "")

    # Normalize and consolidate all tags
    tags = [t.lower() for t in tags if isinstance(t, str)]
    tags = consolidate_tags(tags)

    # Add infobox category as tag if not present
    if infobox_key and infobox_key not in tags:
        tags.append(infobox_key)

    # Ensure proper parent tags exist
    tags, _ = add_parent_tags_for_subcategories(tags)

    # Determine main folder
    main_folder = None
    if infobox_key:
        main_folder = CATEGORY_RULES.get(infobox_key)
    if not main_folder:
        for key, folder in CATEGORY_RULES.items():
            if key.lower() in tags:
                main_folder = folder
                break

    main_folder = main_folder or DEFAULT_FOLDER

    # Determine subfolder
    subfolder = None
    subcats = SUBCATEGORY_RULES.get(main_folder, {})
    for tag in tags:
        if tag in subcats:
            subfolder = subcats[tag]
            break

    return main_folder, subfolder, tags

def move_file(filepath, dest_folder, vault_root):
    dest_path_folder = os.path.join(vault_root, dest_folder)
    os.makedirs(dest_path_folder, exist_ok=True)

    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_path_folder, filename)

    # Handle naming conflicts
    base, ext = os.path.splitext(filename)
    count = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_path_folder, f"{base}_{count}{ext}")
        count += 1

    print(f"📁 Moving '{filename}' to '{dest_folder}/'")
    shutil.move(filepath, dest_path)
    return dest_path

def update_tags_in_file(filepath, new_tags):
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️ Failed to read {filepath} for updating tags: {e}")
        return False

    match = YAML_FRONTMATTER_REGEX.match(content)
    if not match:
        # Create new frontmatter if none exists
        yaml_data = {"tags": new_tags}
        new_yaml = yaml.safe_dump(yaml_data, sort_keys=False).strip()
        new_content = f"---\n{new_yaml}\n---\n\n{content}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"📝 Added new YAML frontmatter with tags in '{filepath}'")
        return True
    else:
        # Update existing frontmatter
        yaml_data = yaml.safe_load(match.group(1)) or {}
        yaml_data['tags'] = new_tags
        write_yaml_frontmatter(filepath, yaml_data, content)
        print(f"📝 Updated tags in '{filepath}'")
        return True

def extract_yaml_header(title, tags, extra_fields=None):
    yaml_data = {
        'title': display_title(title),
        'tags': [display_title(t).lower().replace(" ", "_") for t in tags]
    }
    if extra_fields:
        yaml_data.update(extra_fields)

    lines = ['---']
    for key, value in yaml_data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f'  - {json.dumps(item) if isinstance(item, str) else item}')
        else:
            lines.append(f'{key}: {json.dumps(value) if isinstance(value, str) else value}')
    lines.append('---\n')
    return "\n".join(lines)

def update_indexes(tag_to_files_map, vault_root):
    index_dir = os.path.join(vault_root, "_indexes")
    os.makedirs(index_dir, exist_ok=True)

    # Get all current index files
    current_index_files = {
        os.path.splitext(f)[0].lower(): os.path.join(index_dir, f)
        for f in os.listdir(index_dir)
        if f.endswith(".md")
    }

    # Determine the tags we now care about (consolidated ones)
    updated_tags = set(tag_to_files_map.keys())

    # Remove obsolete index files
    for tag, path in current_index_files.items():
        if tag not in updated_tags:
            os.remove(path)
            print(f"🗑️ Removed obsolete index: {tag}.md")

    # Rebuild valid index files with proper tagging
    for tag, files in tag_to_files_map.items():
        # Create YAML frontmatter with the tag
        yaml_header = extract_yaml_header(
            f"Index: {display_title(tag)}",
            [tag]  # Include the tag itself
        )

        # Create content with tag reference
        lines = [
            f"# Index for `{display_title(tag)}`",
        ]

        for filepath in sorted(files):
            note_name = os.path.splitext(os.path.basename(filepath))[0]
            relative_path = os.path.relpath(filepath, vault_root).replace("\\", "/")
            lines.append(f"- [[{relative_path}|{display_title(note_name)}]]")

        content = yaml_header + "\n".join(lines)

        index_path = os.path.join(index_dir, f"{tag}.md")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Updated index for: {tag} (with tag references)")

def organize_vault(vault_root):
    print(f"🔎 Scanning vault: {vault_root}")
    skip_folders = set(CATEGORY_RULES.values()) | {DEFAULT_FOLDER, "_indexes"}

    tag_to_files_map = {}

    for root, _, files in os.walk(vault_root):
        rel_root = os.path.relpath(root, vault_root)
        if rel_root == ".":
            rel_root = ""

        if any(rel_root.startswith(f) for f in skip_folders) or "_indexes" in rel_root.split(os.sep):
            continue

        for filename in files:
            if not filename.endswith(".md"):
                continue

            if filename.startswith("Template_"):
                filepath = os.path.join(root, filename)
                os.remove(filepath)
                print(f"🗑️ Deleted template: {filename}")
                continue

            filepath = os.path.join(root, filename)

            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                if YAML_FRONTMATTER_REGEX.sub("", content).strip().startswith("1.  REDIRECT "):
                    os.remove(filepath)
                    print(f"🗑️ Deleted redirect: {filename}")
                    continue
            except Exception as e:
                print(f"⚠️ Error checking {filename}: {e}")
                continue

            yaml_data = parse_yaml_frontmatter(filepath)
            main_folder, subfolder, updated_tags = classify_file(yaml_data)

            orig_tags = yaml_data.get("tags") or []
            orig_tags_lower = [t.lower() for t in orig_tags if isinstance(t, str)]
            updated_tags_lower = [t.lower() for t in updated_tags if isinstance(t, str)]

            if set(updated_tags_lower) != set(orig_tags_lower):
                update_tags_in_file(filepath, updated_tags)

            for tag in updated_tags_lower:
                tag_to_files_map.setdefault(tag, []).append(filepath)

            target_folder = main_folder
            if subfolder:
                target_folder = os.path.join(main_folder, subfolder)

            if rel_root != target_folder:
                move_file(filepath, target_folder, vault_root)

    update_indexes(tag_to_files_map, vault_root)
    print("✅ Vault organization complete!")

if __name__ == "__main__":
    organize_vault(VAULT_ROOT)
