from pathlib import Path

import pytest

from rag_modules.data_preparation import DataPreparationModule
from rag_modules.recipe_metadata import parse_query, rank_recommendations


@pytest.fixture(scope="module")
def recipe_documents():
    data_path = Path(__file__).resolve().parents[1] / "data" / "dishes"
    module = DataPreparationModule(str(data_path))
    return module.load_documents()


def _names(documents):
    return [doc.metadata["dish_name"] for doc in documents]


def test_metadata_distinguishes_soup_custard_and_drink(recipe_documents):
    by_name = {doc.metadata["dish_name"]: doc for doc in recipe_documents}

    assert by_name["西红柿鸡蛋汤"].metadata["dish_type"] == "汤"
    assert by_name["鸡蛋羹"].metadata["dish_type"] in {"蒸蛋", "羹"}
    assert by_name["蒸水蛋"].metadata["dish_type"] == "蒸蛋"
    assert by_name["酸梅汤"].metadata["dish_type"] == "饮品"


@pytest.mark.parametrize(
    ("query", "intent", "dish_name", "taste", "dish_type", "ingredient"),
    [
        ("宫保鸡丁", "recipe_lookup", "宫保鸡丁", None, None, None),
        ("红烧肉怎么做", "recipe_lookup", "红烧肉", None, None, None),
        ("我想吃辣", "recommendation", None, "辣", None, None),
        ("我想喝汤", "recommendation", None, None, "汤", None),
        ("我想吃鸡蛋", "recommendation", None, None, None, "鸡蛋"),
        ("随便聊一句和菜谱无关的话", "chat", None, None, None, None),
    ],
)
def test_parse_query_intent_and_conditions(
    recipe_documents, query, intent, dish_name, taste, dish_type, ingredient
):
    parsed = parse_query(query, _names(recipe_documents))

    assert parsed["intent"] == intent
    assert parsed["dish_name"] == dish_name
    if taste:
        assert taste in parsed["taste_tags"]
    if dish_type:
        assert parsed["dish_type"] == dish_type
    if ingredient:
        assert ingredient in parsed["ingredients"]


def test_spicy_recommendations_enforce_spicy_metadata(recipe_documents):
    parsed = parse_query("我想吃辣", _names(recipe_documents))
    results = rank_recommendations(recipe_documents, parsed)[:12]
    names = _names(results)

    assert "鸡蛋羹" not in names
    assert "蒸水蛋" not in names
    assert {"水煮肉片", "水煮牛肉", "贵州辣子鸡", "小炒肉", "尖椒炒牛肉"} <= set(names)
    assert all("辣" in doc.metadata["taste_tags"] for doc in results)


def test_soup_recommendations_exclude_egg_custard(recipe_documents):
    parsed = parse_query("我想喝汤", _names(recipe_documents))
    results = rank_recommendations(recipe_documents, parsed)[:12]
    names = _names(results)

    assert {"西红柿鸡蛋汤", "紫菜蛋花汤", "罗宋汤", "羊肉汤", "排骨苦瓜汤"} <= set(names)
    assert "鸡蛋羹" not in names
    assert "蒸水蛋" not in names
    assert all(doc.metadata["dish_type"] == "汤" for doc in results)


def test_egg_recommendations_use_ingredient_metadata(recipe_documents):
    parsed = parse_query("我想吃鸡蛋", _names(recipe_documents))
    results = rank_recommendations(recipe_documents, parsed)[:12]
    names = set(_names(results))

    assert {"西红柿炒鸡蛋", "鸡蛋火腿炒黄瓜", "洋葱炒鸡蛋", "蒸水蛋"} <= names
    assert all("鸡蛋" in doc.metadata["ingredients"] for doc in results)
