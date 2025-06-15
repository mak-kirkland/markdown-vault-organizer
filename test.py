import pytest
import yaml
import os
from organize import (
    normalize_tags,
    consolidate_tags,
    add_parent_tags_for_subcategories,
    classify_file,
    build_subcategory_paths,
    flatten_subcategory_order,
    CATEGORY_RULES,
    SUBCATEGORY_RULES,
    TAG_CONSOLIDATION,
    organize_vault
)

def test_normalize_tags():
    assert normalize_tags(["Ruins", "CITIES", "LoRe"]) == ["ruins", "cities", "lore"]

def test_consolidate_tags():
    original = ["towns_and_villages", "human_realms"]
    expected = ["towns", "nations"]
    assert consolidate_tags(original) == expected

def test_add_parent_tags_for_subcategories_adds_expected():
    tags = ["cities"]
    enriched_tags, added = add_parent_tags_for_subcategories(tags[:])
    assert "settlements" in enriched_tags
    assert "locations" in enriched_tags
    assert added is True

def test_add_parent_tags_for_subcategories_ignores_unknown():
    tags = ["unknown"]
    enriched_tags, added = add_parent_tags_for_subcategories(tags[:])
    assert enriched_tags == ["unknown"]
    assert added is False

def test_flatten_subcategory_order_contains_depth_order():
    order = flatten_subcategory_order(SUBCATEGORY_RULES)
    # Cities should come after settlements, but before forests
    assert order.index("cities") > order.index("settlements")
    assert order.index("forests") > order.index("cities")

def test_build_subcategory_paths_contains_expected_paths():
    paths = build_subcategory_paths(SUBCATEGORY_RULES, CATEGORY_RULES)
    assert paths["cities"].endswith("Locations/Settlements/Cities")
    assert paths["ruins"].endswith("Locations/Ruins")

def test_classify_file_prefers_deeper_path():
    yaml_data = {"tags": ["ruins", "cities"]}
    main, sub, tags = classify_file(yaml_data)
    # Cities is deeper (3 levels), so should be chosen
    assert sub.endswith("Locations/Settlements/Cities")

def test_classify_file_prefers_earlier_if_same_depth():
    yaml_data = {"tags": ["ruins", "nations"]}  # both 2 deep, but ruins should be chosen if listed earlier
    order = flatten_subcategory_order(SUBCATEGORY_RULES)
    if order.index("ruins") < order.index("nations"):
        main, sub, tags = classify_file(yaml_data)
        assert sub.endswith("Locations/Ruins")

@pytest.fixture
def sample_vault(tmp_path):
    # Create files with tags
    files = {
        "ruins_note.md": ["ruins", "nations"],
        "city_note.md": ["cities"],
        "basic_note.md": ["lore"]
    }
    for name, tags in files.items():
        content = f"---\n{yaml.dump({'tags': tags})}---\n\n#{name}"
        (tmp_path / name).write_text(content, encoding='utf-8')
    return tmp_path

def test_file_moves_correctly(sample_vault):
    organize_vault(str(sample_vault))

    assert (sample_vault / "2_Locations" / "Ruins" / "ruins_note.md").exists()
    assert (sample_vault / "2_Locations" / "Settlements" / "Cities" / "city_note.md").exists()
    assert (sample_vault / "6_Lore" / "basic_note.md").exists()
