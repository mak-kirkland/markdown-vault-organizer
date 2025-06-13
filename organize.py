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
    """Add missing parent category tags based on SUBCATEGORY_RULES"""
    tags_lower = set(t.lower() for t in tags if isinstance(t, str))
    added_tags = False

    for parent_tag, subcats in SUBCATEGORY_RULES.items():
        parent_tag = parent_tag.lower()
        for subcat in subcats:
            subcat = subcat.lower()
            if subcat in tags_lower and parent_tag not in tags_lower:
                tags_lower.add(parent_tag)
                added_tags = True

    return list(tags_lower), added_tags

def classify_file(yaml_data):
    tags = yaml_data.get("tags") or []

    # Normalize and consolidate all tags
    tags = [t.lower() for t in tags if isinstance(t, str)]
    tags = consolidate_tags(tags)

    # Ensure proper parent tags exist
    tags, _ = add_parent_tags_for_subcategories(tags)

    # Determine main folder
    main_key = None
    for key, folder in CATEGORY_RULES.items():
        if key.lower() in tags:
            main_key = key
            break

    main_folder = CATEGORY_RULES.get(main_key, DEFAULT_FOLDER)

    # Determine subfolder
    subfolder = None
    if main_key:
        subcats = SUBCATEGORY_RULES.get(main_key, [])
        for tag in tags:
            if tag in subcats:
                subfolder = tag.capitalize()
                break

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
