def test_set_ring_watts_full_partial_and_remaining_leds(module_loader):
    module = module_loader("class_color_wheel")
    wheel = module.color_wheel(pixel_count=12, pin=5, brightness=20)

    wheel.set_ring_watts_full(500, tick=7, color="r")

    assert wheel.np.values[0] == (20, 0, 0)
    assert wheel.np.values[1] == (20, 0, 0)
    assert wheel.np.values[2] == (10, 0, 0)
    assert wheel.np.values[3:] == [(0, 0, 0)] * 9
    assert wheel.np.write_calls == 1


def test_set_ring_watts_full_overflow_uses_green_breathing(module_loader):
    module = module_loader("class_color_wheel")
    wheel = module.color_wheel(pixel_count=12, pin=5, brightness=20)

    wheel.set_ring_watts_full(2600, tick=0, color="g")

    assert wheel.np.values == [(0, 6, 0)] * 12
    assert wheel.np.write_calls == 1


def test_set_ring3_soc_clamps_high_values_and_sets_status_leds(module_loader):
    module = module_loader("class_color_wheel")
    wheel = module.color_wheel(pixel_count=12, pin=5, brightness=20)

    wheel.set_ring3_soc(150, wifi_ok=False, mqtt_ok=True)

    assert wheel.np.values[:10] == wheel._gradient[:10]
    assert wheel.np.values[10] == (0, 0, 0)
    assert wheel.np.values[11] == (10, 0, 10)


def test_set_ring1_percent_clamps_negative_values(module_loader):
    module = module_loader("class_color_wheel")
    wheel = module.color_wheel(pixel_count=12, pin=5, brightness=20)

    wheel.set_ring1_percent(-5, wifi_ok=True)

    assert wheel.np.values[:10] == [(0, 0, 0)] * 10
    assert wheel.np.values[10] == (0, 0, 0)
    assert wheel.np.values[11] == (0, 0, 10)


def test_display_percentage1_invalid_value_triggers_error_indicator(module_loader, monkeypatch):
    module = module_loader("class_color_wheel")
    wheel = module.color_wheel(pixel_count=12, pin=5, brightness=20)
    called = []
    monkeypatch.setattr(wheel, "show_error", lambda: called.append(True))

    wheel.display_percentage1(101)

    assert called == [True]