def test_is_dst_handles_transition_boundaries(module_loader):
    module = module_loader("class_ntp")

    assert module.NTPClock._is_dst(3, 30, 6) is True
    assert module.NTPClock._is_dst(3, 24, 0) is False
    assert module.NTPClock._is_dst(10, 26, 6) is False
    assert module.NTPClock._is_dst(10, 24, 4) is True


def test_sync_time_applies_cest_offset(module_loader, monkeypatch):
    module = module_loader("class_ntp")
    clock = module.NTPClock()
    module._test_doubles["utime"].localtime_value = (2026, 6, 15, 12, 34, 56, 0, 166)
    called = []
    monkeypatch.setattr(module.ntptime, "settime", lambda: called.append(True))

    class ConnectedWlan:
        def isconnected(self):
            return True

    clock.sync_time(ConnectedWlan())

    assert called == [True]
    assert clock.rtc.datetime() == (2026, 6, 15, 0, 14, 34, 56, 0)


def test_sync_time_times_out_without_wifi(module_loader):
    module = module_loader("class_ntp")
    clock = module.NTPClock()
    fake_utime = module._test_doubles["utime"]

    class OfflineWlan:
        def isconnected(self):
            return False

    try:
        clock.sync_time(OfflineWlan(), timeout_s=2)
    except OSError as exc:
        assert "WiFi not connected" in str(exc)
    else:
        raise AssertionError("Expected OSError for missing WiFi")

    assert fake_utime.sleep_ms_calls == [500, 500, 500, 500]