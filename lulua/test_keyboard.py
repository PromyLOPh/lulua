import pytest

from .keyboard import defaultKeyboards, Button

def test_defaults ():
    k = defaultKeyboards['ibmpc105']
    assert k.name == 'ibmpc105'

    with pytest.raises (KeyError):
        k = defaultKeyboards['nonexistent']

    assert len (list (defaultKeyboards)) > 0

def test_keys_unique ():
    for kbd in defaultKeyboards:
        # both, ids and names must be unique
        havei = set ()
        havename = set ()
        for btn in kbd.keys ():
            assert btn.i not in havei
            havei.add (btn.i)

            assert btn.name not in havename
            havename.add (btn.name)

def test_keyboard_getRow ():
    k = defaultKeyboards['ibmpc105']
    for btn, expect in [(k['Bl1'], 0), (k['Cr1'], 1), (k['Dr1'], 2)]:
        assert k.getRow (btn) == expect
    
def test_keyboard_getattr ():
    k = defaultKeyboards['ibmpc105']
    assert k['Dr1'] == k.find ('Dr1')
    assert k['CD_ret'] == k.find ('CD_ret')
    assert k['Cr1'] != k.find ('El1')

def test_button_uniqname ():
    a = Button ('a')
    assert a.name == 'a'

    b = Button ('b')
    assert b.name == 'b'

    assert a != b

    c = Button ('a')
    assert c.name == 'a'

    assert a == c
    assert b != c

    d = dict ()
    d[a] = 1
    assert a in d
    assert b not in d
    assert c in d
    d[b] = 2
    assert b in d

