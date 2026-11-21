from inspire.extraction.hashing import canonical_hash, canonical_json


def test_hash_nao_depende_da_ordem_das_chaves() -> None:
    assert canonical_hash({"a": 1, "b": [1, 2]}) == canonical_hash({"b": [1, 2], "a": 1})


def test_hash_muda_quando_o_conteudo_muda() -> None:
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})


def test_ordem_da_lista_importa() -> None:
    assert canonical_hash({"r": [1, 2]}) != canonical_hash({"r": [2, 1]})


def test_acentos_sao_preservados_e_o_hash_e_estavel() -> None:
    assert canonical_json({"t": "Saúde"}) == '{"t":"Saúde"}'
    assert canonical_hash({"t": "Saúde"}) == canonical_hash({"t": "Saúde"})
    assert len(canonical_hash({})) == 64
