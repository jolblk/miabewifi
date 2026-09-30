"""Tests du calcul des frais de vente (1 % par défaut).

Lancer avec :  pytest tests/test_fees.py
(ne dépend d'aucune variable d'environnement : app/fees.py n'importe pas la config)
"""
from app.fees import compute_sale_split


def test_one_percent_on_round_prices():
    assert compute_sale_split(2000, 0.01) == (20.0, 1980.0)
    assert compute_sale_split(6000, 0.01) == (60.0, 5940.0)
    assert compute_sale_split(15000, 0.01) == (150.0, 14850.0)


def test_fee_rounds_up_to_whole_fcfa():
    # 1 % de 250 = 2,5 -> 3 (jamais moins que ce que PayGate nous prend)
    assert compute_sale_split(250, 0.01) == (3.0, 247.0)
    # 1 % de 100 = 1
    assert compute_sale_split(100, 0.01) == (1.0, 99.0)
    # 1 % de 50 = 0,5 -> 1
    assert compute_sale_split(50, 0.01) == (1.0, 49.0)


def test_no_float_artifacts():
    # 0.01 * 300 vaut 3.0000000000000004 en flottant : ne doit pas donner 4
    assert compute_sale_split(300, 0.01) == (3.0, 297.0)
    assert compute_sale_split(700, 0.01) == (7.0, 693.0)


def test_fee_plus_net_always_equals_amount():
    for montant in (1, 2, 49, 50, 99, 100, 101, 250, 333, 500, 1234, 2000, 9999, 15000):
        frais, net = compute_sale_split(montant, 0.01)
        assert frais + net == montant
        assert 0 <= frais <= montant
        assert net >= 0


def test_zero_rate_means_no_fee():
    assert compute_sale_split(2000, 0) == (0.0, 2000.0)


def test_tiny_amount_never_gives_negative_net():
    assert compute_sale_split(1, 0.01) == (1.0, 0.0)


def _raises_value_error(*args):
    try:
        compute_sale_split(*args)
    except ValueError:
        return True
    return False


def test_invalid_inputs_are_rejected():
    assert _raises_value_error(0, 0.01)
    assert _raises_value_error(-500, 0.01)
    assert _raises_value_error(1000, -0.01)
    assert _raises_value_error(1000, 1)
