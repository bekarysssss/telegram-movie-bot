from app.core.text import normalize_text


def test_yo_and_case():
    assert normalize_text("Крёстный ОТЕЦ") == "крестный отец"


def test_punctuation_and_spaces():
    assert normalize_text("  WALL·E:   The   Movie! ") == "wall e the movie"


def test_latin_accents_stripped_but_cyrillic_й_kept():
    assert normalize_text("Léon") == "leon"
    assert normalize_text("Тёмный рыцарь Майкл") == "темный рыцарь майкл"


def test_empty():
    assert normalize_text(None) == ""
    assert normalize_text("   ") == ""
