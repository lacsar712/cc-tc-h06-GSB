from h06_extra_trap import armed, sample

def test_polish():
    assert armed() is True
    assert sample()["verdict"] == "超限"
