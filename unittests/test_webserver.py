def test_html_renders_defaults_for_missing_state(module_loader):
    module = module_loader("class_webserver")
    server = module.Webserver({})

    html = server._html()

    assert "Battery Pack 1 SoC: 0.0%" in html
    assert "Battery Pack 2 SoC: 0.0%" in html
    assert "Battery Pack 3 SoC: 0.0%" in html
    assert "Average SoC: 0.0%" in html
    assert "AC Output: 0 W" in html
    assert "Solar Total: 0 W" in html
    assert "MQTT: disconnected" in html
    server.stop_webserver()


def test_html_uses_average_and_status(module_loader):
    module = module_loader("class_webserver")
    state = {"SOC1": 20, "SOC2": 40, "SOC3": 80, "acoutw": 1500, "totalsolarw": 900, "mqtt_ok": True}
    server = module.Webserver(state)

    html = server._html()

    assert "Average SoC: 46.7%" in html
    assert "AC Output: 1500 W" in html
    assert "Solar Total: 900 W" in html
    assert "MQTT: connected" in html
    server.stop_webserver()


def test_stop_webserver_closes_socket(module_loader):
    module = module_loader("class_webserver")
    server = module.Webserver({})

    server.stop_webserver()

    assert server._run is False
    assert server._sock.closed is True
    assert module._test_doubles["thread"].calls[0][0] == server._serve