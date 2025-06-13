# obsidian-organizer

Move .md files in a "flat" Obsidian vault into a folder and subfolder hierarchy, according to user-defined mapping rules.

The script checks the "tags" field of the YAML frontmatter of each markdown file, and moves the file to the folder associated with that tag, defined in the config.yaml file.

Note that indexes for each tag are generated. So for each tag, we have a page in `_indexes` which contains a list of links to all pages using that tag.

There are 3 important mappings:
1. CATEGORY_RULES
   ```yaml
   "tag" : "FOLDER NAME"
   ```

   This defines the top-level structure.
   
2. SUBCATEGORY_RULES
   ```yaml
   "top_level_tag1" :
   - "tag1"
   - "tag2"
   - "tag3"
   "top_level_tag2" :
   - "tag4"
   - "tag5"
   ```

   This defines the subfolders within the main category folders. E.g we can define a "locations" top-level category, with subcategories "cities", "towns" etc.
   This would automatically tag all "cities" with a "locations" tag, and move it into "Locations/Cities/file.md"

3. TAG_CONSOLIDATION
   ```yaml
   "replacement_tag" : "original_tag"
   ```

   Sometimes we might have gone a little crazy and made our tags too granular. Here we can consolidate them, e.g "human_realms" and "dwarven_kingdoms" could be removed entirely, in favour of a new tag "nations". This reduces the total number of tags

# Usage

`python3 organize.py` will re-organize a folder named `obsidian_vault` within the same directory as the script.
