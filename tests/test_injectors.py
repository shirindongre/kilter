import ast

import pytest

from kilter.defects.variants import ALL_CLASSES, BENIGN, generate_variants


@pytest.fixture(scope="module")
def variants():
    return generate_variants()


def test_variant_counts(variants):
    clean = [v for v in variants if v.clean]
    assert len(clean) == 8
    for cls in ALL_CLASSES:
        assert sum(v.defect_class == cls for v in variants) == 8
    assert len({v.id for v in variants}) == len(variants) == 48  # 8 clean + 8 x D1..D5 (AIMS Q-005)
    assert set(BENIGN) == {"bace", "bbbp"}


def test_every_variant_parses_and_site_is_inside_file(variants):
    for v in variants:
        ast.parse(v.source)
        if not v.clean:
            assert 1 <= v.site_line <= len(v.source.splitlines()), v.id


def test_ground_truth_site_shows_the_defect(variants):
    marker = {"D1": "fit(", "D2": "concatenate", "D4": " = "}
    for v in variants:
        line = v.source.splitlines()[v.site_line - 1] if v.site_line else ""
        if v.defect_class in marker:
            assert marker[v.defect_class] in line, (v.id, line)
        if v.defect_class == "D3":
            assert "SPLIT = 'random'" in line or line.startswith("def run("), (v.id, line)


def test_each_defective_variant_differs_from_its_clean_base_only_by_the_injection(variants):
    clean = {(v.base, v.benign): v.source.splitlines() for v in variants if v.clean}
    for v in variants:
        if v.clean:
            continue
        base = clean[(v.base, v.benign)]
        diff = [l for l in v.source.splitlines() if l not in base]
        assert 0 < len(diff) <= 6, (v.id, diff)  # a single planted defect, not a rewrite


def test_d3_uses_both_modes_per_reference(variants):
    for base in BENIGN:
        d3 = [v for v in variants if v.base == base and v.defect_class == "D3"]
        assert {"SPLIT = 'random'" in v.source for v in d3} == {True, False}
