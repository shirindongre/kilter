import pytest

from kilter.eval.metrics import clopper_pearson, paired_exact


def test_clopper_pearson_known_values():
    lo, hi = clopper_pearson(8, 8)
    assert hi == 1.0 and lo == pytest.approx(0.6306, abs=1e-3)      # the "8/8 is not 100%" caveat (AIMS L-009)
    lo, hi = clopper_pearson(0, 8)
    assert lo == 0.0 and hi == pytest.approx(0.3694, abs=1e-3)
    lo, hi = clopper_pearson(4, 8)
    assert lo == pytest.approx(0.1570, abs=1e-3) and hi == pytest.approx(0.8430, abs=1e-3)
    assert clopper_pearson(0, 0) == (0.0, 1.0)


def test_interval_contains_the_point_estimate_and_narrows_with_n():
    for k, n in [(1, 10), (5, 10), (9, 10)]:
        lo, hi = clopper_pearson(k, n)
        assert lo <= k / n <= hi
    w = lambda n: (lambda lo, hi: hi - lo)(*clopper_pearson(n // 2, n))
    assert w(10) > w(100) > w(1000)


def test_paired_exact_with_no_discordant_pairs_is_not_significant():
    from kilter.defects.variants import Variant

    v = Variant("x", "bace", 0, "D5", 1, "d", "")
    rec = lambda verdict, cls: {"verdict": verdict, "findings": [{"defect_class": cls, "kind": "defect"}]}
    a = {"x": rec("OUT OF KILTER", "D5")}
    assert paired_exact([v], a, a, "D5")["p"] == 1.0
    b = {"x": rec("IN KILTER", "OTHER")}
    r = paired_exact([v], a, b, "D5")
    assert r["only_first"] == 1 and r["only_second"] == 0
