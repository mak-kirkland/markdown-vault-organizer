# Markdown Vault Organizer 🗃️

This script automatically organizes a Markdown vault by parsing tags in your Markdown files and moving them into structured folders based on configurable category and subcategory rules.

📜 If you want a tool to build and connect your ideas, check out my app [Chronicler](https://github.com/mak-kirkland/chronicler).

🧭 If you need to convert a MediaWiki XML dump into a clean, tag-driven vault, check out my [MediaWiki to Markdown Converter](https://github.com/mak-kirkland/mediawiki-to-markdown).

## ✨ Features
- 📁 Automatically moves notes into structured folders by tag
- 🏷️ Normalizes, consolidates, and inherits parent tags
- 🧠 Infers top-level categories and nested subfolders from tags
- 🛠️ Updates YAML frontmatter with cleaned tag lists
- 📚 Updates _indexes/ folder with tag-based note listings
- 🧹 Deletes MediaWiki-style redirects and templates
- 🔄 Works recursively across the whole vault regardless of current structure
- 🔍 Verbose mode for detailed output and easier troubleshooting

--- 

## 📦 Requirements

- Python 3.8+
- A valid config.yaml with folder/tag rules (see below)

Install Python dependencies:

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
    wilderness:
      - forests
      - seas
    settlements:
      - villages
      - cities
tag_consolidation:
  person: people
  place: locations
```

## 🚀 Usage

```bash
python organize_vault.py [--verbose]
```

| Argument    | Description           |
| ----------- | --------------------- |
| `--verbose` | Enable vebose logging |

## 🗂️ Output Structure

```text
vault_root/
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
