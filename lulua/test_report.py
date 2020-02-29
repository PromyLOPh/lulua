from decimal import Decimal

from .report import approx

def test_approx ():
    assert approx (0) == (Decimal ('0'), '')
    assert approx (0.01) == (Decimal ('0'), '')
    assert approx (0.05) == (Decimal ('0.1'), '')
    assert approx (1) == (Decimal ('1'), '')
    assert approx (100) == (Decimal ('100'), '')
    assert approx (999.9) == (Decimal ('999.9'), '')
    assert approx (999.91) == (Decimal ('999.9'), '')
    assert approx (999.99) == (Decimal ('1'), 'thousand')

    assert approx (10**3) == (Decimal ('1'), 'thousand')
    assert approx (10**6) == (Decimal ('1'), 'million')
    assert approx (10**9) == (Decimal ('1'), 'billion')
    assert approx (10**12) == (Decimal ('1000'), 'billion')


