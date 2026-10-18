import pytest
from pipeline import clean

def row(**overrides):
    return dict(date="2025-01", axe=" Nord ", regularite_composite=91.2, ponctualite_origine=85, **overrides)

def test_duplicates_and_whitespace():
    df, n = clean([row(), row()])
    assert len(df) == 1 and n == 1 and df.iloc[0].axe == "Nord"

@pytest.mark.parametrize("field,value", [("date", "2025-13"), ("axe", " "), ("regularite_composite", 101), ("ponctualite_origine", "inconnu")])
def test_invalid(field, value):
    r = row(); r[field] = value
    with pytest.raises((ValueError, TypeError)):
        clean([r])

def test_conflicting_key():
    a, b = row(), row(); b["regularite_composite"] = 80
    with pytest.raises(ValueError, match="contradictoires"):
        clean([a, b])

def test_null_is_not_zero():
    r = row(); r["regularite_composite"] = None
    df, _ = clean([r])
    assert df.regularite_composite.isna().all()
