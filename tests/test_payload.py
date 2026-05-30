from wingz.mission.payload import Payload, no_payload


def test_payload_mass():
    p = Payload(name="sensor", mass_kg=5.0, power_W=20.0)
    assert p.mass_kg == 5.0
    assert p.power_W == 20.0


def test_no_payload():
    p = no_payload()
    assert p.mass_kg == 0.0
    assert p.power_W == 0.0


def test_payload_defaults():
    p = Payload(name="relay")
    assert p.mass_kg == 0.0
    assert p.power_W == 0.0


def test_typical_payloads():
    from wingz.mission.payload import surveillance_payload, comms_relay_payload

    s = surveillance_payload()
    assert s.mass_kg > 0
    assert s.power_W > 0

    c = comms_relay_payload()
    assert c.mass_kg > 0
    assert c.power_W > 0
