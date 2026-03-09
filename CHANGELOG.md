# Changelog

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-03-09 (Session 11)

### Fixed

- **[BUG-28] `main.py` — `NameError: name '_loop_count' isn't defined` beim Boot**  
  `_update_leds()` wird direkt nach `_mqtt_connect()` aufgerufen, um den
  initialen LED-Zustand zu setzen. Die Methode übergibt `_loop_count` an
  `set_ring2_watts()` für die Pulsberechnung — aber `_loop_count` wurde erst
  *nach* diesem Aufruf definiert, was beim ersten Boot sofort crashte.  
  *Fix:* `_loop_count = 0` und `_overflow_mode = False` vor den
  `_mqtt_connect()` / `_update_leds()` Aufrufen verschoben.

---

## [Unreleased] — 2026-03-09 (Session 10)

### Changed

- **All modules — Dokumentation auf GitHub-Standard angehoben**
  - Jede Datei erhält einen Modul-Docstring mit Zweck, Dateiformat-Beispielen und
    Verwendungs-Snippet (`::`-Codeblock).
  - Alle Klassen haben `Args`/`Returns`/`Raises`/`Notes`-Sektionen im Docstring.
  - Alle öffentlichen Methoden haben vollständige Docstrings mit Parametern und
    Rückgabewerten.
  - Interne `# FIX:`-Entwicklungsnotizen aus den Datei-Headern entfernt
    (diese Informationen sind im ``CHANGELOG.md`` dokumentiert).
  - Auskommentierte Debug-Prints in `class_wifi_connection.py` entfernt.
  - `stop_all()` in `class_wifi_connection.py` erhält Docstring als Backward-
    Compatibility-Alias für `disconnect()`.
  - `ssid == None` → `ssid is None` (PEP 8 Identitätsvergleich).
  - `get_wifi_status()` gab fälschlicherweise `self.wifi.isconnected()` zurück
    statt des State-Lists — korrigiert auf `[status, ssid, ip]`.

---

## [Unreleased] — 2026-03-09 (Session 9)

### Changed

- **`class_color_wheel.py` — `set_ring1_percent()`: 10-LED-Skala mit Teillicht-Dimming**  
  Ring 1 (SoC-Anzeige) nutzt jetzt Indizes 0–9 (10 LEDs), 10 % pro LED.  
  Die nächste LED wird proportional gedimmt (z. B. 75 % → LED 0–6 volle Helligkeit,  
  LED 7 bei 50 % Helligkeit, LED 8–9 aus).  
  Der Farbgradient (rot → grün) wird auf die 10 SoC-LEDs umgerechnet, sodass  
  LED 0 = reines Rot (0 %) und LED 9 = reines Grün (100 %).  
  Index 10 (LED 11) bleibt dauerhaft aus.  
  Index 11 (LED 12) behält den WiFi-Indikator (blau 50 % / aus).

---

## [Unreleased] — 2026-03-09 (Session 8)

### Added

- **`main.py` — 3. Akku-Pack (BatteryPack3)**  
  Topic `Seplos/BatteryPack3/soc` als `TOPIC_SOC3` ergänzt und zu `_TOPICS` hinzugefügt.  
  `state["SOC3"]` im Shared-State-Dict angelegt.  
  `on_message()` behandelt das neue Topic analog zu SOC1/SOC2.  
  SoC-Mittelwert in `_update_leds()` auf drei Packs umgestellt: `(SOC1 + SOC2 + SOC3) / 3`.

- **`main.py` — Hardware-Watchdog (WDT)**  
  `machine.WDT(timeout=8000)` wird direkt vor dem Main-Loop gestartet.  
  `wdt.feed()` wird zu Beginn jedes Loop-Ticks (~100 ms) und explizit vor jedem
  blockierenden `utime.sleep()` (MQTT-Backoff) aufgerufen.  
  Wird der Main-Loop für mehr als 8 s nicht erreicht (z. B. Deadlock), startet der ESP32
  automatisch neu.

- **`class_color_wheel.py` — WiFi-Status-LED auf Ring 1 (Index 11)**  
  `set_ring1_percent()` erhält neuen Parameter `wifi_ok=True`.  
  SoC-Gradient nutzt jetzt Indizes 0–10 (11 LEDs, 100 % = volle Helligkeit auf LED 11).  
  Index 11 (LED 12, bisher nie beleuchtet bei <100 % SoC): zeigt WiFi-Status —  
  Blau 50 % Helligkeit bei aktivem WLAN, aus wenn WLAN weg.

### Changed

- **`main.py` — `MQTT_BACKOFF_MAX` von 60 auf 6 Sekunden reduziert**  
  Notwendig damit der MQTT-Backoff-Sleep das 8 s WDT-Fenster nicht überschreitet.  
  (Backoff-Schritte: 1 → 2 → 4 → 6 → 6 → …)

- **`class_wifi_connection.py` — WiFi-Verbindungs-Timeout von 10 000 ms auf 7 000 ms reduziert**  
  `try_wifi_connect()` blockiert den Main-Loop maximal 7 s; bleibt damit sicher innerhalb
  des 8 s WDT-Fensters (WDT wird am Loop-Anfang gefüllt, WiFi-Reconnect läuft dazwischen).

---

## [Unreleased] — 2026-03-09 (Session 7)

### Changed

- **`class_color_wheel.py` — neue Methode `set_ring2_watts(acoutw, solarw, tick)`**  
  Ring 2 zeigt Last und Solar auf einem geteilten Ring:
  - LED 1–6 (Indizes 0–5): Last in Rot, im Uhrzeigersinn
  - LED 12–7 (Indizes 11–6): Solar in Grün, gegen den Uhrzeigersinn
  - Maßstab: 1000 W/LED (volle Helligkeit); die Teillicht-LED wird proportional
    gedimmt, sodass ~1 W Auflösung erreichbar ist (sichtbare 500 W-Stufen)
  - Überlauf (>6000 W je Segment): alle 6 Segment-LEDs pulsieren mit
    symmetrischer Dreieckswelle, Periode ~2 s (20 Loop-Ticks)

- **`main.py` — `_update_leds()` auf `set_ring2_watts()` umgestellt**  
  Ruft die neue Methode mit `acoutw`, `totalsolarw` und `_loop_count` auf.  
  Setzt das neue Flag `_overflow_mode = True`, sobald ein Segment-Wert >6000 W,
  um per-Tick-Rendering für den Puls-Effekt zu aktivieren.

- **`main.py` — Render-Bedingung im Main-Loop erweitert**  
  LED-Update jetzt bei `state["dirty"]` **oder** `_overflow_mode`,
  damit der Atemeffekt auch ohne neue MQTT-Daten kontinuierlich animiert wird.

### Removed

- **`main.py` — `_watts_to_leds()` entfernt**  
  Hilfsfunktion wurde ausschließlich vom alten `set_ring2_channels()`-Aufruf genutzt
  und ist durch die neue wattgenaue Skalierung in `set_ring2_watts()` ersetzt.

- **`main.py` — Konstante `SOLAR_MAX_W` entfernt**  
  War nur für `_watts_to_leds()` relevant und nicht mehr benötigt.

---

## [Unreleased] — 2026-03-09 (Session 6)

### Changed

- **`main.py` — `DEBUG_ALL_TOPICS = False`**  
  Alle Topics wurden per Wildcard-Subscription bestätigt und sind korrekt.  
  Debug-Logging deaktiviert; Wildcard-Subscription `#` wird nicht mehr abonniert.

---

## [Unreleased] — 2026-03-09 (Session 5)

### Added

- **`main.py` — `DEBUG_ALL_TOPICS` Flag + Wildcard-Subscription `#`**  
  Temporäre Diagnosehilfe: wenn `DEBUG_ALL_TOPICS = True`, abonniert der Client zusätzlich  
  das MQTT-Wildcard-Topic `#` und gibt **alle** eingehenden Nachrichten als  
  `ALL: <topic> = <value>` aus. Dient zur Identifikation des korrekten Topic-Namens für  
  `acoutw` (Istwert laut ioBroker: 819 W, im State jedoch 0 — Topic stimmt nicht überein).  
  Nach Bestätigung der Topics `DEBUG_ALL_TOPICS = False` setzen.

---

## [Unreleased] — 2026-03-09 (Session 4)

### Fixed

- **[BUG-27] `main.py` — MQTT-Topic-Konstanten stimmten nicht mit Broker-Topics überein**  
  Die Topics im Code verwendeten ioBroker-Adapter-Notation mit `.` als Trenner und  
  `mqtt.0.`-Präfix. Der Broker sendet die Topics jedoch direkt mit `/` als Trenner  
  ohne Präfix. Dadurch landeten alle eingehenden Nachrichten im `unmatched`-Zweig  
  und kein LED-Wert wurde je gesetzt.  
  *Fix:* Topics auf die tatsächlich vom Broker gesendeten Werte korrigiert:

  | Alt (falsch) | Neu (korrekt) |
  |---|---|
  | `mqtt.0.Seplos.BatteryPack1.soc` | `Seplos/BatteryPack1/soc` |
  | `mqtt.0.Seplos.BatteryPack2.soc` | `Seplos/BatteryPack2/soc` |
  | `mqtt.0.solaranlage.pip.acoutw` | `solaranlage/pip/acoutw` |
  | `mqtt.0.solaranlage.pip.totalsolarw` | `solaranlage/pip/totalsolarw` |

---

## [Unreleased] — 2026-03-09 (Session 3)

### Fixed

- **[BUG-24] `main.py` — Debug-Print `utime.time() % 30 == 0` feuerte nie**  
  Nach NTP-Sync liefert `utime.time()` einen ~820-Millionen-Sekunden-Wert.  
  Bei 100 ms-Takt (10 Polls pro Sekunde) war es reiner Zufall, ob eine exakt durch 30  
  teilbare Sekunde getroffen wurde — in der Praxis feuerte der Print niemals.  
  *Fix:* Ersetzt durch einen Schleifenzähler `_loop_count`; Print alle 100 Ticks (~10 s).

- **[BUG-25] `main.py` — `umqtt.robust.check_msg()` blockierte den Main-Loop**  
  `umqtt.robust` überschreibt `check_msg()` mit interner Reconnect-Logik. Bei einem  
  stillen Socket-Abbruch versuchte die Library selbst zu reconnecten und blockierte dabei  
  den Loop komplett — keine weiteren Prints, kein LED-Update, kein Heartbeat.  
  *Fix:* Socket-Timeout von 0,5 s direkt nach `connect()` gesetzt  
  (`_mqttclient.sock.settimeout(0.5)`), sodass `check_msg()` nicht endlos blockieren kann.

- **[BUG-26] `main.py` `on_message()` — `except (ValueError, UnicodeError)` zu eng**  
  Andere Exception-Typen (z. B. `TypeError` bei unerwartetem Payload-Format) wurden  
  nicht gefangen und konnten den Callback still abbrechen lassen.  
  *Fix:* Auf `except Exception` erweitert; Exception-Typ wird mit ausgegeben.

### Added

- **`main.py` — Loop-Heartbeat alle 10 s**  
  `HEARTBEAT | STATE: {...}` wird alle 100 Ticks gedruckt. Ermöglicht zu erkennen ob  
  der Loop läuft und ob MQTT-Daten ankommen. Bleibt vorerst aktiv für die Diagnose,  
  kann nach Bestätigung der Topics ausgebaut werden.

---

## [Unreleased] — 2026-03-09 (Session 2)

### Fixed

- **[BUG-20] `class_wifi_connection.py` `try_wifi_connect()` — `AttributeError: 'module' object has no attribute 'time'`**  
  `machine.time()` does not exist in MicroPython. The call `machine.time() * 1000` used
  for the connection timeout crashed immediately on every connect attempt.  
  Because the exception was caught by the generic `except Exception`, `wifi_ssid` was set
  to `"offline"`, causing `check_connection()` to call `connect()` again in an endless loop.  
  *Fix:* Replaced `machine.time() * 1000` with `utime.ticks_ms()` and the subtraction with
  `utime.ticks_diff()` (overflow-safe MicroPython tick comparison).

- **[BUG-21] `class_wifi_connection.py` — unused imports (`WLAN`, `Timer`, `sys`, `sleep_ms`)**  
  Left-over imports from older versions wasted RAM and indicated the file had been
  reverted to a stale state.  
  *Fix:* Removed all unused imports, kept only `ujson`, `network`, `machine`, `utime`.

- **[BUG-22] `class_wifi_connection.py` `is_connected()` — `AttributeError` on `WLAN` object**  
  Method called `self.wifi.check_connection()` on a `network.WLAN` instance, which has
  no such method.  
  *Fix:* Method removed entirely (duplicate of `isconnected()`).

- **[BUG-23] `boot.py` — `webrepl.start()` called before WiFi was connected**  
  `boot.py` runs before `main.py`, so no WiFi interface is active yet when
  `webrepl.start()` is called. This caused an `OSError` in `webrepl.py` line 73 (`start`)
  on every boot.  
  *Fix:* `webrepl.start()` removed from `boot.py` and moved into `main.py`, called
  immediately after a successful `wifi.connect()` inside a `try/except` guard.

### Added

- **`class_color_wheel.py` — `blink_blue(n=3)` method**  
  New reusable method that flashes all LEDs of a ring blue `n` times (400 ms on /
  400 ms off). `show_wifi()` now delegates to `blink_blue(2)` to avoid duplicated code.

- **`main.py` — WiFi status feedback via NeoPixel rings**  
  After `wifi.connect()` returns:
  - **Success** → Ring 2 (right) blinks blue 3× via `led_ring2.blink_blue(3)`
  - **Failure** → Ring 1 (left) blinks blue 3× via `led_ring1.blink_blue(3)`

- **`main.py` — WebREPL started after successful WiFi connect**  
  `webrepl.start()` is now called in `main.py` inside the `wifi_status == "online"` branch,
  wrapped in `try/except` so a missing `webrepl_cfg.py` or failed start does not abort boot.

---

## [Unreleased] — 2026-03-09

### Fixed

#### CRITICAL — Runtime crashes

- **[BUG-01] `class_mqtt.py` `publish()` — `UnboundLocalError: errorcount`**  
  `errorcount` was a bare local variable inside `publish()` instead of `self.errorcount`.  
  Every `publish()` call that hit an exception crashed with `UnboundLocalError`.  
  The error counter and the `connection_running` flag therefore never worked.  
  *Fix:* Removed the counter entirely; reconnect responsibility moved to the caller.

- **[BUG-02] `class_webserver.py` `thread_webserver()` — `NameError: conn` before assignment**  
  When `self.websocket.accept()` itself raised an exception (e.g. on socket timeout),
  `conn` was not yet defined, so the `except` block crashed with `NameError: conn`.  
  This killed the webserver thread permanently on the first socket error.  
  *Fix:* `conn = None` before the `try` block; guarded all `conn` uses with `if conn is not None`.

- **[BUG-03] `class_webserver.py` `html_code()` — `TypeError: can only concatenate str (not float/int) to str`**  
  `SOC1` is `float`, `acoutw` is `int`; both were concatenated directly into the HTML string.  
  *Fix:* Replaced string concatenation with `.format()`.

- **[BUG-05] `main.py` `on_message()` — `TypeError`: `str` membership test on `bytes` topic**  
  `"totalsolarw" in topic` — `topic` is `bytes` in `umqtt`; comparing a `str` to `bytes`
  raises `TypeError` in MicroPython. Because this occurred inside the MQTT callback,
  the exception was silently swallowed by `umqtt.robust`, so **Ring 2 was never updated**.
  All messages fell through to the `else`-branch (SoC logic).  
  *Fix:* Use exact bytes equality: `topic == TOPIC_SOLARW`.

- **[BUG-07] `main.py` — `OSError` from `check_msg()` terminated the main loop**  
  `mqttclient.check_msg()` was called outside any `try/except`. When the MQTT broker
  disconnected (without a WiFi drop), the resulting `OSError` crashed the `while True`
  loop entirely, leaving the device in a dead state until the next watchdog reset.  
  *Fix:* Wrapped in `try/except OSError` with exponential backoff reconnect.

- **[BUG-08] `class_solar_values.py` `get_values()` — `AttributeError: self.rtc`**  
  `self.rtc` was used in `get_values()` and `get_time()` but never initialised in
  `__init__`. Any call to these methods crashed immediately.  
  *(Class is dead code and not imported anywhere — marked for removal.)*

#### HIGH — Incorrect behaviour

- **[BUG-04] `class_webserver.py` — Webserver always showed 0 / 0 / 0 / 0**  
  The webserver read its own module-level globals (`SOC1`, `SOC2`, …) which were never
  updated by `main.py`. The two modules have separate namespaces.  
  *Fix:* A shared `state` dict is passed into `Webserver.__init__()` and read by the
  render thread.

- **[BUG-06] `main.py` `on_message()` — SOC1 and SOC2 not differentiated by topic**  
  Both `BatteryPack1.soc` and `BatteryPack2.soc` messages landed in the same `else`
  branch. Each new message overwrote `SOC1` while rotating the old value into `SOC2`,
  regardless of which pack actually sent the update.  
  *Fix:* Exact topic comparison (`topic == TOPIC_SOC1` / `topic == TOPIC_SOC2`).

- **[BUG-11] `main.py` — No MQTT reconnect when broker goes down (WiFi still up)**  
  `reconnect_needed` was only set to `"yes"` on a WiFi drop. If the MQTT broker
  restarted independently, the client stayed disconnected until the next WiFi outage.  
  *Fix:* Dedicated MQTT error handler in the main loop triggers reconnect on any
  `OSError` from `check_msg()`.

- **[BUG-10] `class_wifi_connection.py` `is_connected()` — `AttributeError` on WLAN object**  
  The method called `self.wifi.check_connection()` where `self.wifi` is a
  `network.WLAN` object, which has no `check_connection()` method.  
  *Fix:* Removed the broken `is_connected()` method; `isconnected()` delegates correctly
  to `self.wifi.isconnected()`.

- **[BUG-14] `class_ntp.py` `is_dst()` — DST boundary detection off by several days**  
  Formula `previous_sunday = day - weekday + 1` is wrong for all weekdays:  
  - Monday (`weekday=0`): `day - 0 + 1 = day + 1` (tomorrow — wrong)  
  - Sunday (`weekday=6`): `day - 6 + 1 = day - 5` (five days ago — wrong)  
  This caused the time to be off by 1 hour for up to 7 days around DST transitions.  
  *Fix:* `last_sun = day - (weekday + 1) % 7`

- **[BUG-15] `class_wifi_connection.py` `connect()` — fragile SSID scan via `str(nets)`**  
  `if ssid in str(nets)` converts the entire scan result list to a string and checks for
  substring presence. This matches partial SSID names inside BSSIDs (MAC addresses),
  channel numbers, and other scan fields, potentially causing wrong network selection.  
  *Fix:* Extract `net[0]` (SSID bytes) from scan results into a set and compare using
  `ssid.encode() in scanned_ssids`.

#### MEDIUM — Performance & stability degradation

- **[BUG-09] `main.py` — Main loop slept 10 s; MQTT messages processed only once per 10 s**  
  `time.sleep(10)` at the top of the loop meant up to 10 s latency on every MQTT message.
  Combined with the blocking LED animations (up to 6 s), effective latency exceeded 16 s.  
  *Fix:* Loop tick reduced to 100 ms (`utime.sleep_ms(100)`).

- **[BUG-12] `class_color_wheel.py` — `time.sleep(0.25)` per LED inside MQTT callback**  
  `display_percentage1()` and `display_percentage2()` slept 0.25 s per LED, totalling
  up to 6 s of blocking time. These methods were called directly from `on_message()`,
  blocking MQTT processing for the full duration.  
  *Fix:* All `time.sleep()` removed from the render path. Rendering is non-blocking and
  called from the main loop only when `state["dirty"]` is `True`.

- **[BUG-13] `class_color_wheel.py` — `np.write()` called once per LED (12–48×/frame)**  
  Every pixel update wrote the entire LED strip to hardware individually, causing visible
  flicker and wasting ~450 µs × N per frame.  
  *Fix:* Set all pixels first, then call `np.write()` exactly once per ring per frame.

#### LOW — Code quality / correctness

- **[BUG-16]** Removed unused imports (`sys`, `random`, `os`, `Pin`, `Timer`, `re`,
  `network` from `class_mqtt.py` and `class_color_wheel.py`). Saved ~2–4 KB RAM.

- **[BUG-17]** `reconnect_needed = "yes"/"no"` replaced by proper boolean / direct
  reconnect logic.

- **[BUG-18]** `class_solar_values.py` identified as dead code (never imported).
  Marked with `# TODO: remove`.

- **[BUG-19]** `MQTT_Client.py` uses `paho-mqtt` (CPython only) and is not deployable
  on MicroPython. Marked with header warning.

---

### Changed

- **`class_color_wheel.py`**: Added explicit `bpp=3, timing=1` to `NeoPixel()` constructor
  for unambiguous WS2812B (800 kHz, RGB) configuration.
- **`class_color_wheel.py`**: Red→green gradient precomputed in `__init__`; no float
  arithmetic in the render hot-loop.
- **`class_color_wheel.py`**: New public methods `set_ring1_percent()` and
  `set_ring2_channels()` replace the per-pixel-sleep legacy methods as the canonical API.
  Legacy methods (`display_percentage1/2`, `set_single_color`) retained as wrappers for
  backward compatibility.
- **`class_mqtt.py`**: Added `keepalive=60` parameter to `MQTTClient` constructor.
  Default was `0` (no keepalive), allowing brokers to silently drop idle connections.
- **`main.py`**: MQTT topics extracted as named byte-string constants (`TOPIC_SOC1`, …).
- **`main.py`**: `SOLAR_MAX_W`, `BRIGHTNESS`, `LOOP_MS`, `NTP_INTERVAL_S`,
  `MQTT_BACKOFF_MAX` extracted as top-level configuration constants.
- **`main.py`**: `on_message()` callback is now side-effect-free: only writes to the
  shared `state` dict and sets `state["dirty"] = True`. All LED writes moved to
  `_update_leds()` called from the main loop.
- **`main.py`**: Exponential backoff (1 s → 2 s → … → 60 s) on MQTT reconnect attempts.
- **`class_webserver.py`**: Added `socket.SO_REUSEADDR` to prevent `EADDRINUSE` on
  warm restart. Added `finally` block to always close the connection socket.
- **`class_wifi_connection.py`**: `try_wifi_connect()` raises `OSError` on timeout
  instead of silently falling into the `except` branch by manual `break`.

---

### Removed

- `class_webserver.py`: Module-level `global SOC1/SOC2/acoutw/totalsolarw` declarations
  (were never populated from `main.py`).
- `main.py`: Dead `test == 1` branch, `kill()`, `stop_all()` functions,
  `reconnect_needed` string-flag, and `if __name__ == "__main__":` guard
  (unnecessary in MicroPython `main.py`).
- Unused imports across all modules.
