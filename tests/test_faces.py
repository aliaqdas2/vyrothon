"""Unit tests for face embedding helpers."""

import numpy as np

from app.faces import embedding_to_list, find_nearest_identity
from app.models import Identity


def test_embedding_to_list_length_and_values():
    enc = np.linspace(0, 1, 128, dtype=np.float64)
    vec = embedding_to_list(enc)
    assert len(vec) == 128
    assert abs(vec[0] - 0.0) < 1e-9
    assert abs(vec[-1] - 1.0) < 1e-9


def test_find_nearest_identity_returns_none_when_empty():
    """No rows in DB -> first() is None."""
    from unittest.mock import MagicMock

    session = MagicMock()
    session.execute.return_value.first.return_value = None
    out = find_nearest_identity(session, np.zeros(128))
    assert out is None


def test_identity_model_table_name():
    assert Identity.__tablename__ == "identities"
