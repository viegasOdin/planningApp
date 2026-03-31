"""
Testes unitários para utils.py

Cobre as funções puras de processamento de strings de dependência:
- extract_ids: extrai IDs numéricos de uma string de dependência
- parse_dependencies: extrai ID, tipo e lag de uma string de dependência
"""

import numpy as np
import pytest

from utils import extract_ids, parse_dependencies


class TestExtractIds:
    """Testes para extract_ids(dependency_string)"""

    def test_returns_empty_for_nan(self):
        assert extract_ids(np.nan) == []

    def test_returns_empty_for_empty_string(self):
        assert extract_ids("") == []

    def test_returns_empty_for_whitespace_only(self):
        assert extract_ids("   ") == []

    def test_extracts_single_integer_id(self):
        assert extract_ids("123") == ["123"]

    def test_extracts_decimal_id(self):
        assert extract_ids("1.2") == ["1.2"]

    def test_extracts_multiple_ids_separated_by_semicolon(self):
        result = extract_ids("123;456;789")
        assert result == ["123", "456", "789"]

    def test_extracts_id_ignoring_type_suffix(self):
        # "123FS" → extrai apenas a parte numérica "123"
        assert extract_ids("123FS") == ["123"]

    def test_returns_empty_for_non_numeric_string(self):
        assert extract_ids("ABC") == []

    def test_extracts_ids_from_mixed_semicolon_list(self):
        # IDs com tipos diferentes separados por ponto-e-vírgula
        result = extract_ids("100FS;200SS+5;300FF")
        assert result == ["100", "200", "300"]


class TestParseDependencies:
    """Testes para parse_dependencies(dependency_string)"""

    def test_returns_empty_for_nan(self):
        assert parse_dependencies(np.nan) == []

    def test_returns_empty_for_empty_string(self):
        assert parse_dependencies("") == []

    def test_returns_empty_for_whitespace_only(self):
        assert parse_dependencies("   ") == []

    def test_defaults_type_to_fs_when_absent(self):
        result = parse_dependencies("123")
        assert result == [{"id": "123", "type": "FS", "lag": 0}]

    def test_parses_explicit_fs_type(self):
        result = parse_dependencies("123FS")
        assert result == [{"id": "123", "type": "FS", "lag": 0}]

    def test_parses_ss_type(self):
        result = parse_dependencies("123SS")
        assert result == [{"id": "123", "type": "SS", "lag": 0}]

    def test_parses_ff_type(self):
        result = parse_dependencies("456FF")
        assert result == [{"id": "456", "type": "FF", "lag": 0}]

    def test_parses_sf_type(self):
        result = parse_dependencies("789SF")
        assert result == [{"id": "789", "type": "SF", "lag": 0}]

    def test_parses_positive_lag(self):
        result = parse_dependencies("123FS+5")
        assert result == [{"id": "123", "type": "FS", "lag": 5}]

    def test_parses_negative_lag(self):
        result = parse_dependencies("123FS-3")
        assert result == [{"id": "123", "type": "FS", "lag": -3}]

    def test_parses_lag_with_whitespace(self):
        # O código faz lag_str.replace(' ', ''), então "+ 5" deve virar 5
        result = parse_dependencies("123FS+ 5")
        assert result == [{"id": "123", "type": "FS", "lag": 5}]

    def test_parses_multiple_dependencies(self):
        result = parse_dependencies("123FS;456SS+2")
        assert result == [
            {"id": "123", "type": "FS", "lag": 0},
            {"id": "456", "type": "SS", "lag": 2},
        ]

    def test_parses_decimal_id(self):
        result = parse_dependencies("1.2.3")
        assert len(result) == 1
        assert result[0]["id"] == "1.2.3"
        assert result[0]["type"] == "FS"
        assert result[0]["lag"] == 0

    def test_non_numeric_string_returns_empty(self):
        # Strings sem dígitos iniciais não produzem match
        assert parse_dependencies("ABC") == []
