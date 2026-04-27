def test_demo_lab_has_two_devices(demo_lab):  # (1)
    names = sorted(d.name for d in demo_lab)  # (2)
    assert names == ["r1", "r2"]
