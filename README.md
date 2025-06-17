# Obsidian Vault Organizer 🗃️

This script automatically organizes an Obsidian vault by parsing tags in your Markdown files and moving them into structured folders based on configurable category and subcategory rules. It also updates tag-based indexes and cleans up unwanted files like redirects and templates.

## ✨ Features
- 📁 Automatically moves notes into structured folders by tag
- 🏷️ Normalizes, consolidates, and inherits parent tags
- 🧠 Infers top-level categories and nested subfolders from tags
- 🛠️ Updates YAML frontmatter with cleaned tag lists
- 📚 Maintains _indexes/ folder with tag-based note listings
- 🧹 Deletes MediaWiki-style redirects and templates
- 🔄 Works recursively across the whole vault regardless of current structure

--- 

## 📦 Requirements

- Python 3.8+
- A valid config.yaml with folder/tag rules (see below)

Install Python dependencies (if any are required):

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Your config.yaml should define how to interpret tags and folder rules:

```yaml
vault_root: path/to/your/vault
default_folder: Uncategorized
category_rules:
  people: 1_People
  locations: 2_Locations
  factions: 3_Factions
subcategory_rules:
  locations:
    Wilderness:
      - Forests
      - Seas
    Settlements:
      - Villages
      - Cities
tag_consolidation:
  person: people
  place: locations
```

## 🚀 Usage

```bash
python organize_vault.py
```

## 🗂️ Output Structure

```text
obsidian_vault/
├── 1_People/
│   └── Character_Name.md
├── 2_Locations/
│   ├── Wilderness/
│   │   └── Forests/
│   │       └── Dark_Wood.md
│   └── Settlements/
│       └── Villages/
│           └── Riverbend.md
├── 3_Factions/
│   └── ...
├── _indexes/
│   ├── _people.md
│   ├── _locations.md
│   └── ...
└── Uncategorized/
    └── Notes_Without_Tags.md
```

## 👤 Author

Created by Michael Kirkland
