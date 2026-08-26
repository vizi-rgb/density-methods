import numpy as np
from core.heatmap.logic.logic import HeatmapLogic


def test_and_keeps_overlap_only():
    a = np.array([[1.0, 1.0], [0.0, 1.0]])
    b = np.array([[1.0, 0.0], [0.0, 1.0]])

    result = HeatmapLogic(a).and_(b).result()

    assert np.array_equal(result, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_or_keeps_the_max_of_either():
    a = np.array([[1.0, 0.0], [0.0, 2.0]])
    b = np.array([[0.5, 3.0], [0.0, 0.0]])

    result = HeatmapLogic(a).or_(b).result()

    assert np.array_equal(result, np.array([[1.0, 3.0], [0.0, 2.0]]))


def test_negate_flips_nonzero_and_zero():
    a = np.array([[0.0, 2.0], [5.0, 0.0]])

    result = HeatmapLogic(a).negate().result()

    assert np.array_equal(result, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_and_not_zeroes_wherever_other_is_nonzero():
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[0.0, 1.0], [0.0, 1.0]])

    result = HeatmapLogic(a).and_not(b).result()

    assert np.array_equal(result, np.array([[1.0, 0.0], [3.0, 0.0]]))


def test_and_not_preserves_fractional_intensity_where_not_excluded():
    # Regression guard: and_(negate(other)) would run fractional values
    # through np.maximum against a binary 0/1 mask, clipping 0.3 up to 1.
    # and_not must leave untouched cells exactly as they were.
    a = np.array([[0.3, 0.7]])
    b = np.array([[0.0, 1.0]])

    result = HeatmapLogic(a).and_not(b).result()

    assert np.array_equal(result, np.array([[0.3, 0.0]]))


def test_methods_chain_and_mutate_in_place():
    a = np.array([[1.0, 0.0]])
    b = np.array([[1.0, 0.0]])
    c = np.array([[0.0, 1.0]])

    logic = HeatmapLogic(a)
    result = logic.and_(b).or_(c).result()

    assert np.array_equal(result, np.array([[1.0, 1.0]]))
    assert logic.result() is result
