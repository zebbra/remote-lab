def test_two_routers_present(frr_lab):
    names = sorted(d.name for d in frr_lab)
    assert names == ["r1", "r2"]


def test_devices_reported_by_netlab(frr_lab):
    # `d.raw` is the full `netlab inspect` dict for each node.
    assert all(d.raw for d in frr_lab)


def test_device_names_are_stable(frr_lab):
    # reuse_lab=True means this test shares the lab from the previous two.
    assert {d.name for d in frr_lab} == {"r1", "r2"}
