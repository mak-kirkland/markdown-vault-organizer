import os
import re
import shutil
import yaml
import json

# Load configuration from YAML file
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Assign configuration to variables
VAULT_ROOT = config['vault_root']
DEFAULT_FOLDER = config['default_folder']
CATEGORY_RULES = config['category_rules']
SUBCATEGORY_RULES = config['subcategory_rules']
TAG_CONSOLIDATION = config['tag_consolidation']

YAML_FRONTMATTER_REGEX = re.compile(r"(?s)^---\n(.*?)\n---\n")

def build_subcategory_paths(subcategory_rules, category_rules):
    flat_map = {}

    def walk(parent_path, node):
        if isinstance(node, list):
            for item in node:
                walk(parent_path, item)
        elif isinstance(node, dict):
            for key, val in node.items():
                folder_name = key.capitalize()
                full_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
                flat_map[key.lower()] = full_path
                walk(full_path, val)
        elif isinstance(node, str):
            folder_name = node.capitalize()
            full_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
            flat_map[node.lower()] = full_path

    for cat_key, branches in subcategory_rules.items():
        # Get main folder from category_rules, fallback to cat_key itself if not found
        main_folder = category_rules.get(cat_key, cat_key)
        walk(main_folder, branches)

    return flat_map

# Reverse lookup: folder name (like "6_Lore") -> tag (like "lore")
FOLDER_TO_CATEGORY = {v.lower(): k.lower() for k, v in CATEGORY_RULES.items()}
# Build flat map once
SUBCATEGORY_PATHS = build_subcategory_paths(SUBCATEGORY_RULES, CATEGORY_RULES)

# === FUNCTIONS ===

def normalize_tags(tags):
    return [t.lower() for t in tags if isinstance(t, str)]

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

    if YAML_FRONTMATTER_REGEX.search(original_content):
        # Replace existing frontmatter
        def replacer(match):
            return f"---\n{new_yaml}\n---\n"
        new_content = YAML_FRONTMATTER_REGEX.sub(replacer, original_content, count=1)
    else:
        # No frontmatter exists, prepend new frontmatter block
        new_content = f"---\n{new_yaml}\n---\n\n{original_content}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

def consolidate_tags(tags):
    """Apply all tag consolidation rules and remove replaced tags"""
    consolidated = set()
    replacements = set()

    # Process each input tag
    for input_tag in tags:
        # Find the replacement (if any exists)
        replacement = TAG_CONSOLIDATION.get(input_tag, input_tag)
        # Add the replacement to our consolidated set
        consolidated.add(replacement)
        # If this tag was replaced, track the original
        if replacement != input_tag:
            replacements.add(input_tag)

    # Now remove any tags that were replaced
    final_tags = [tag for tag in consolidated if tag not in replacements]
    return final_tags

def add_parent_tags_for_subcategories(tags):
    tags = set(tags)
    added_tags = False

    for tag in list(tags):
        path = SUBCATEGORY_PATHS.get(tag)
        if not path:
            continue

        parts = path.split("/")  # e.g. "6_Lore/Mythology" -> ["6_Lore", "Mythology"]
        top_level_folder = parts[0].lower()  # e.g. "6_lore"

        # Reverse lookup folder -> tag
        top_level_tag = FOLDER_TO_CATEGORY.get(top_level_folder)

        if top_level_tag and top_level_tag not in tags:
            tags.add(top_level_tag)
            added_tags = True

        # Also add other intermediate parts if you want
        for part in parts[1:-1]:
            normalized_part = part.lower()
            if normalized_part not in tags:
                tags.add(normalized_part)
                added_tags = True

    return list(tags), added_tags

def classify_file(yaml_data):
    tags = yaml_data.get("tags") or []

    tags = normalize_tags(tags)
    tags = consolidate_tags(tags)

    tags, _ = add_parent_tags_for_subcategories(tags)

    # Find matching category keys by lowercase match
    matching_main_keys = [key for key in CATEGORY_RULES if key.lower() in tags]

    if not matching_main_keys:
        main_folder = DEFAULT_FOLDER
    else:
        # Use the first matching key's folder (or refine logic)
        main_folder = CATEGORY_RULES[matching_main_keys[0]]

    # Determine subfolder
    subfolder = None
    max_depth = -1
    for tag in tags:
        sub_path = SUBCATEGORY_PATHS.get(tag)
        if sub_path and sub_path.lower().startswith(main_folder.lower()):
            depth = sub_path.count("/")
            if depth > max_depth:
                subfolder = sub_path
                max_depth = depth

    return main_folder, subfolder, tags

def move_file(filepath, dest_folder, vault_root):
    dest_path_folder = os.path.join(vault_root, dest_folder)
    os.makedirs(dest_path_folder, exist_ok=True)

    filename = os.path.basename(filepath)
    dest_path = os.path.join(dest_path_folder, filename)

    if os.path.exists(dest_path):
        raise FileExistsError(f"❌ File already exists at destination: {dest_path}")

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
    if match:
        yaml_data = yaml.safe_load(match.group(1)) or {}
    else:
        yaml_data = {}

    yaml_data['tags'] = new_tags
    write_yaml_frontmatter(filepath, yaml_data, content)
    print(f"📝 Updated tags in '{filepath}'")
    return True

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
        # Create content with tag reference
        lines = [f"# Index for #{tag}"]

        for filepath in sorted(files):
            note_name = os.path.splitext(os.path.basename(filepath))[0]
            lines.append(f"- [[{note_name}]]")

        content = "\n".join(lines)

        index_path = os.path.join(index_dir, f"{tag}.md")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Updated index for: {tag} (with tag references)")

def organize_vault(vault_root):
    print(f"🔎 Scanning vault: {vault_root}")

    # Only skip _indexes folder explicitly; allow traversal into all others
    skip_folders = {"_indexes"}

    tag_to_files_map = {}

    for root, _, files in os.walk(vault_root):
        rel_root = os.path.relpath(root, vault_root)
        if rel_root == ".":
            rel_root = ""

        # Skip _indexes folder anywhere in path
        if "_indexes" in rel_root.split(os.sep):
            continue

        for filename in files:
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)

            # Skip template files and redirects as before
            if filename.startswith("Template_"):
                os.remove(filepath)
                print(f"🗑️ Deleted template: {filename}")
                continue

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
            orig_tags_lower = normalize_tags(orig_tags)
            updated_tags_lower = normalize_tags(updated_tags)

            if set(updated_tags_lower) != set(orig_tags_lower):
                update_tags_in_file(filepath, updated_tags)

            for tag in updated_tags_lower:
                tag_to_files_map.setdefault(tag, []).append(filepath)

            # Determine target folder relative to vault root
            target_folder = subfolder if subfolder else main_folder
            target_folder_norm = os.path.normpath(target_folder)

            # Current file folder relative to vault root
            file_current_folder = os.path.relpath(root, vault_root)
            file_current_folder_norm = os.path.normpath(file_current_folder)

            # Move if current folder is different from target folder
            if file_current_folder_norm.lower() != target_folder_norm.lower():
                try:
                    move_file(filepath, target_folder, vault_root)
                except FileExistsError as e:
                    print(f"⚠️ Skipped moving due to existing file: {e}")

    update_indexes(tag_to_files_map, vault_root)
    print("✅ Vault organization complete!")

if __name__ == "__main__":
    organize_vault(VAULT_ROOT)
