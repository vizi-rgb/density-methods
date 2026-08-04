import pytest

from app.api.errors import ApiError
from app.api.routes.upload import _validate_heatmap_types


def test_accepts_a_valid_subset() -> None:
    assert _validate_heatmap_types(["directional", "speed"]) == ["directional", "speed"]


def test_deduplicates_repeated_values() -> None:
    assert _validate_heatmap_types(["speed", "speed", "cluster"]) == ["speed", "cluster"]


def test_rejects_unknown_type() -> None:
    with pytest.raises(ApiError) as exc_info:
        _validate_heatmap_types(["roi"])
    assert exc_info.value.status_code == 422


def test_rejects_empty_selection() -> None:
    with pytest.raises(ApiError) as exc_info:
        _validate_heatmap_types([])
    assert exc_info.value.status_code == 422
