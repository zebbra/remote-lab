from neops_remote_lab.testing.fixture import remote_lab_fixture

frr_lab = remote_lab_fixture(
    "tests/topologies/frr.yml",
    reuse_lab=True,
)
