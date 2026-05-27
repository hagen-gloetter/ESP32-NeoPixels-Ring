import io


def test_init_reads_credentials_and_casts_port(module_loader, monkeypatch):
    module = module_loader("class_mqtt")
    payload = io.StringIO('{"secretHost":"broker","secretPort":"1883","secretUser":"alice","secretPass":"pw"}')
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: payload, raising=False)
    monkeypatch.setattr(module.ujson, "load", lambda _handle: {
        "secretHost": "broker",
        "secretPort": "1883",
        "secretUser": "alice",
        "secretPass": "pw",
    })

    mqtt = module.MQTT("secrets_mqtt.json")

    assert mqtt.broker == "broker"
    assert mqtt.port == 1883
    assert mqtt.username == "alice"
    assert mqtt.password == "pw"


def test_connect_builds_client_with_keepalive(module_loader, monkeypatch):
    module = module_loader("class_mqtt")
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: io.StringIO("{}"), raising=False)
    monkeypatch.setattr(module.ujson, "load", lambda _handle: {
        "secretHost": "broker",
        "secretPort": "1884",
        "secretUser": "alice",
        "secretPass": "pw",
    })
    mqtt = module.MQTT("secrets_mqtt.json")

    client = mqtt.connect(b"client-id", keepalive=15)

    assert client.broker == "broker"
    assert client.port == 1884
    assert client.username == "alice"
    assert client.password == "pw"
    assert client.keepalive == 15
    assert client.connect_calls == 1


def test_publish_returns_false_without_client(module_loader, monkeypatch):
    module = module_loader("class_mqtt")
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: io.StringIO("{}"), raising=False)
    monkeypatch.setattr(module.ujson, "load", lambda _handle: {
        "secretHost": "broker",
        "secretPort": "1884",
        "secretUser": "alice",
        "secretPass": "pw",
    })
    mqtt = module.MQTT("secrets_mqtt.json")

    assert mqtt.publish("topic", 42) is False


def test_publish_returns_false_on_client_error(module_loader, monkeypatch):
    module = module_loader("class_mqtt")
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: io.StringIO("{}"), raising=False)
    monkeypatch.setattr(module.ujson, "load", lambda _handle: {
        "secretHost": "broker",
        "secretPort": "1884",
        "secretUser": "alice",
        "secretPass": "pw",
    })
    mqtt = module.MQTT("secrets_mqtt.json")
    client = mqtt.connect(b"client-id")
    client.raise_on_publish = RuntimeError("boom")

    assert mqtt.publish("topic", 42, retain=True) is False


def test_publish_casts_payload_to_string(module_loader, monkeypatch):
    module = module_loader("class_mqtt")
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: io.StringIO("{}"), raising=False)
    monkeypatch.setattr(module.ujson, "load", lambda _handle: {
        "secretHost": "broker",
        "secretPort": "1884",
        "secretUser": "alice",
        "secretPass": "pw",
    })
    mqtt = module.MQTT("secrets_mqtt.json")
    client = mqtt.connect(b"client-id")

    assert mqtt.publish("topic", 42, retain=True) is True
    assert client.publish_calls == [("topic", "42", True)]