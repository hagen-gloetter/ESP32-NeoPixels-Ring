# ESP32 NeoPixel Solar Monitor

> **[DE ↓](#deutsch)** | **[EN ↓](#english)**

---

> **Versionen / Versions:** [`2-Rings/`](2-Rings/) — 2-Ring (stabil / stable) | [`3-Rings/`](3-Rings/) — 3-Ring (aktuell / current)

---

## Deutsch <a name="deutsch"></a>

### Projektbeschreibung

Dieses Projekt implementiert einen visuellen Echtzeit-Monitor für eine Solaranlage mit Batteriespeicher auf einem **ESP32** (MicroPython). **WS2812B-NeoPixel-Ringe** (je 12 LEDs, 5 V, RGB) zeigen den aktuellen Systemzustand auf einen Blick.

Es gibt zwei Versionen:

| Version | Ordner | Status | Beschreibung |
|---------|--------|--------|--------------|
| 2-Ring | [`2-Rings/`](2-Rings/) | Stabil | Ring 1 = SoC · Ring 2 = Last/Solar (geteilt) |
| 3-Ring | [`3-Rings/`](3-Rings/) | Aktuell | Ring 1 = Last · Ring 2 = Solar · Ring 3 = SoC + Status |

Messwerte werden per **MQTT** empfangen. WLAN und MQTT-Broker werden bei Ausfall automatisch wiederhergestellt. Ein **Hardware-Watchdog (8 s)** setzt den ESP32 automatisch zurück, wenn der Loop hängt. Eine eingebettete **Mini-Webseite** (Port 80, Auto-Refresh alle 10 s) zeigt die aktuellen Rohwerte im Browser an.

---

### Hardware

#### 3-Ring-Version (aktuell)

- **Board**: ESP32 (z. B. ESP32 DevKit V1)
- **LEDs**: 3× NeoPixel-Ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Verbindung**: WLAN (2,4 GHz), MQTT-Broker im lokalen Netz

**Verkabelung:**

```
ESP32 GPIO 25  →  DIN  Ring 1  (AC-Last, rot)
ESP32 GPIO 27  →  DIN  Ring 2  (Solarleistung, grün)
ESP32 GPIO 26  →  DIN  Ring 3  (SoC + Status)
5 V            →  +5V  alle drei Ringe
GND            →  GND  alle
```

#### 2-Ring-Version (stabil)

```
ESP32 GPIO 25  →  DIN  Ring 1  (SoC-Anzeige)
ESP32 GPIO 27  →  DIN  Ring 2  (Energie-Anzeige, geteilt)
5 V            →  +5V  beide Ringe
GND            →  GND  alle
```

> Für mehr als ~6 LEDs bei voller Helligkeit einen externen 5-V-Spannungsregler verwenden (je Ring max. ~720 mA bei Weiß-Vollhelligkeit). Bei `BRIGHTNESS = 16` reicht USB-Versorgung.

---

### LED-Anzeige im Detail

#### 3-Ring-Version (`3-Rings/`)

**Ring 1 — AC-Last (GPIO 25, rot)**

| Index | LED | Funktion |
|-------|-----|----------|
| 0–11 | 1–12 | AC-Last, 200 W/LED, max 2400 W (12 × 200 W) |

Teillicht-Dimming: z. B. 500 W → 2 volle LEDs + LED 3 bei 50 % Helligkeit.
Überlauf (> 2400 W): alle 12 LEDs pulsieren (~2 s Atemzyklus).

**Ring 2 — Solarleistung (GPIO 27, grün)**

| Index | LED | Funktion |
|-------|-----|----------|
| 0–11 | 1–12 | Solarleistung, 200 W/LED, max 2400 W |

Gleiche Skala und gleiches Überlauf-Verhalten wie Ring 1.

**Ring 3 — Batterie SoC + Status (GPIO 26)**

| Index | LED | Farbe | Funktion |
|-------|-----|-------|----------|
| 0–9 | 1–10 | Rot → Grün | SoC-Gradient, 10 %/LED, max 100 % |
| 10 | 11 | **Blau 50 %** | WiFi: online = an · offline = aus |
| 11 | 12 | **Magenta 50 %** | MQTT: verbunden = an · getrennt = aus |

Teillicht-Dimming (Ring 3): z. B. 75 % → LED 1–7 voll + LED 8 bei 50 % Helligkeit.

---

#### 2-Ring-Version (`2-Rings/`)

**Ring 1 — Batterie SoC (GPIO 25)**

| Index | LED | Funktion |
|-------|-----|----------|
| 0–9 | 1–10 | SoC-Gradient, 10 %/LED, Rot (0 %) → Grün (100 %) |
| 10 | 11 | MQTT-Status: **Magenta 50 %** = verbunden · **Aus** = getrennt |
| 11 | 12 | WiFi-Status: **Blau 50 %** = online · **Aus** = offline |

**Ring 2 — Energie (GPIO 27, geteilt)**

```
       LED 12 (Solar)
    11         1  (Last)
  10             2
  9               3
    8           4
       7     5
          6
```

| Segment | LEDs | Richtung | Farbe | Skala |
|---------|------|----------|-------|-------|
| AC-Last | 1–6 | Uhrzeigersinn | Rot | 1000 W/LED, max 6000 W |
| Solar | 12–7 | Gegen den UZS | Grün | 1000 W/LED, max 6000 W |

Bei Überlauf (> 6000 W) pulsiert das gesamte Segment (~2 s Atemzyklus).

---

### Software / Abhängigkeiten

| Komponente | Version |
|------------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Teil des MicroPython-Standardarchivs |
| `ntptime` | Teil des MicroPython-Standardarchivs |
| `neopixel` | MicroPython built-in |

---

### Unit-Tests (Host, ohne ESP32)

Für Logiktests der 3-Ring-Module gibt es den Ordner `unittests/`.
Die Tests verwenden Mocks für MicroPython-Module (`machine`, `network`, `utime`, `neopixel`, `umqtt`, `socket`) und laufen auf dem Host-System.

```bash
python3 -m pip install pytest
python3 -m pytest -q unittests
```

---

### Konfiguration

Vor dem ersten Flashen zwei JSON-Dateien im Wurzelverzeichnis des ESP32-Dateisystems anlegen:

**`secrets_wifi.json`**
```json
{
  "MeinHeimnetz": "MeinWLAN-Passwort",
  "Fallback-SSID": "anderesPW"
}
```
Mehrere Netzwerke werden unterstützt — das erste gefundene wird verwendet.

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-passwort"
}
```

Weitere Parameter am Anfang von `main.py`:

```python
BRIGHTNESS       = 16    # LED-Helligkeit (0–255); niedrig lassen für USB-Versorgung
LOOP_MS          = 100   # Haupt-Loop-Takt in Millisekunden (10 Hz)
NTP_INTERVAL_S   = 600   # NTP-Resync alle 10 Minuten
MQTT_BACKOFF_MAX = 6     # Max. MQTT-Reconnect-Delay in Sekunden (WDT-kompatibel)
```

Zusätzlich in der 3-Ring-Version:

```python
WATTS_PER_LED    = 200   # Watt pro voller LED (Ring 1 + Ring 2)
MAX_RING_W       = 2400  # Überlaufschwelle (12 × 200 W)
```

---

### MQTT-Topics

| Topic | Inhalt | Typ |
|-------|--------|-----|
| `Seplos/BatteryPack1/soc` | SoC Batteriepack 1 | float, % |
| `Seplos/BatteryPack2/soc` | SoC Batteriepack 2 | float, % |
| `Seplos/BatteryPack3/soc` | SoC Batteriepack 3 | float, % |
| `solaranlage/pip/totalsolarw` | Gesamte Solarleistung | int, W |
| `solaranlage/pip/acoutw` | AC-Ausgangsleistung (Last) | int, W |

---

### WebREPL (drahtloser Zugriff)

WebREPL ermöglicht Code-Ausführung und Dateiübertragung über WLAN — ohne USB-Kabel.

**Einmalige Einrichtung** (einmalig per USB-REPL):
```python
import webrepl_setup
```
Passwort setzen und neu starten. Danach startet WebREPL bei jedem Boot automatisch.

**Browser-Interface:** http://micropython.org/webrepl/
- Host: `ws://192.168.x.x:8266/` (IP steht im seriellen Boot-Log)

**Dateiübertragung per Kommandozeile:**
```bash
python webrepl_cli.py -p passwort 3-Rings/main.py 192.168.x.x:/main.py
```

**Thonny:** Run → Configure interpreter → MicroPython (ESP32) → WebREPL → IP + Passwort.

> **Hinweis:** Der Hardware-WDT (8 s) ist nur aktiv, solange `main.py` läuft. Ein `Ctrl+C` stoppt `main.py` und damit auch den WDT — REPL-Sitzungen sind uneingeschränkt nutzbar.

---

### Dateistruktur

#### 2-Ring-Version (`2-Rings/`)

```
2-Rings/
├── main.py                  # Hauptprogramm (2 Ringe: SoC + Last/Solar geteilt)
├── class_color_wheel.py     # NeoPixel-Treiber
├── class_mqtt.py            # MQTT-Wrapper
├── class_wifi_connection.py # WLAN-Manager
├── class_ntp.py             # NTP-Sync
├── class_webserver.py       # HTTP-Statusseite
└── MQTT_Client.py           # Desktop-Testclient (NICHT für ESP32)
```

#### 3-Ring-Version (`3-Rings/`)

```
3-Rings/
├── main.py                  # Hauptprogramm (3 Ringe: Last · Solar · SoC+Status)
├── class_color_wheel.py     # NeoPixel-Treiber + set_ring_watts_full + set_ring3_soc
├── class_mqtt.py            # MQTT-Wrapper (unverändert)
├── class_wifi_connection.py # WLAN-Manager (unverändert)
├── class_ntp.py             # NTP-Sync (unverändert)
└── class_webserver.py       # HTTP-Statusseite + MQTT-Status
```

---

### Flash / Deployment

```bash
# MicroPython flashen (einmalig)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# 3-Ring-Version übertragen (mpremote)
mpremote connect /dev/ttyUSB0 cp 3-Rings/main.py :main.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_color_wheel.py :class_color_wheel.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_mqtt.py :class_mqtt.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_wifi_connection.py :class_wifi_connection.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_ntp.py :class_ntp.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_webserver.py :class_webserver.py
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json

# 2-Ring-Version übertragen (mpremote)
# mpremote connect /dev/ttyUSB0 cp 2-Rings/main.py :main.py  (und restliche Dateien analog)
```

---

### Bekannte Einschränkungen

- `MQTT_Client.py` ist ausschließlich für Desktop-Tests gedacht und darf nicht auf den ESP32 übertragen werden.
- Bei mehr als ~6 LEDs bei voller Helligkeit externen 5-V-Regler verwenden.

---

### Changelog

Siehe [CHANGELOG.md](CHANGELOG.md) für alle Änderungen und Bugfixes.

---

### Lizenz

Siehe [LICENSE](LICENSE).

---
---

## English <a name="english"></a>

### Project Description

This project implements a real-time visual monitor for a solar power system with battery storage, running on an **ESP32** (MicroPython). **WS2812B NeoPixel rings** (12 LEDs each, 5 V, RGB) display the current system state at a glance.

Two versions are available:

| Version | Folder | Status | Description |
|---------|--------|--------|-------------|
| 2-Ring | [`2-Rings/`](2-Rings/) | Stable | Ring 1 = SoC · Ring 2 = Load/Solar (split) |
| 3-Ring | [`3-Rings/`](3-Rings/) | Current | Ring 1 = Load · Ring 2 = Solar · Ring 3 = SoC + Status |

Measurements are received via **MQTT**. WiFi and MQTT broker are automatically restored on failure. A **hardware watchdog (8 s)** resets the ESP32 if the main loop stalls. A built-in **mini web page** (port 80, auto-refresh every 10 s) shows current raw values in the browser.

---

### Hardware

#### 3-Ring version (current)

- **Board**: ESP32 (e.g. ESP32 DevKit V1)
- **LEDs**: 3× NeoPixel ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Connectivity**: WiFi (2.4 GHz), MQTT broker on the local network

**Wiring:**

```
ESP32 GPIO 25  →  DIN  Ring 1  (AC load, red)
ESP32 GPIO 27  →  DIN  Ring 2  (solar power, green)
ESP32 GPIO 26  →  DIN  Ring 3  (SoC + status)
5 V            →  +5V  all three rings
GND            →  GND  all
```

#### 2-Ring version (stable)

```
ESP32 GPIO 25  →  DIN  Ring 1  (SoC display)
ESP32 GPIO 27  →  DIN  Ring 2  (energy display, split)
5 V            →  +5V  both rings
GND            →  GND  all
```

> For more than ~6 LEDs at full brightness use an external 5 V regulator (up to ~720 mA per ring at full white brightness). At `BRIGHTNESS = 16` USB power is sufficient.

---

### LED Display Details

#### 3-Ring version (`3-Rings/`)

**Ring 1 — AC Load (GPIO 25, red)**

| Index | LED | Function |
|-------|-----|----------|
| 0–11 | 1–12 | AC load, 200 W/LED, max 2400 W (12 × 200 W) |

Partial dimming: e.g. 500 W → 2 full LEDs + LED 3 at 50 % brightness.
Overflow (> 2400 W): all 12 LEDs pulse (~2 s breathing cycle).

**Ring 2 — Solar Power (GPIO 27, green)**

| Index | LED | Function |
|-------|-----|----------|
| 0–11 | 1–12 | Solar power, 200 W/LED, max 2400 W |

Same scale and overflow behaviour as Ring 1.

**Ring 3 — Battery SoC + Status (GPIO 26)**

| Index | LED | Colour | Function |
|-------|-----|--------|----------|
| 0–9 | 1–10 | Red → Green | SoC gradient, 10 %/LED, max 100 % |
| 10 | 11 | **Blue 50 %** | WiFi: online = on · offline = off |
| 11 | 12 | **Magenta 50 %** | MQTT: connected = on · disconnected = off |

Partial dimming (Ring 3): e.g. 75 % → LEDs 1–7 full + LED 8 at 50 % brightness.

---

#### 2-Ring version (`2-Rings/`)

**Ring 1 — Battery SoC (GPIO 25)**

| Index | LED | Function |
|-------|-----|----------|
| 0–9 | 1–10 | SoC gradient, 10 %/LED, Red (0 %) → Green (100 %) |
| 10 | 11 | MQTT status: **Magenta 50 %** = connected · **Off** = disconnected |
| 11 | 12 | WiFi status: **Blue 50 %** = online · **Off** = offline |

**Ring 2 — Energy (GPIO 27, split)**

```
       LED 12 (Solar)
    11         1  (Load)
  10             2
  9               3
    8           4
       7     5
          6
```

| Segment | LEDs | Direction | Colour | Scale |
|---------|------|-----------|--------|-------|
| AC Load | 1–6 | Clockwise | Red | 1000 W/LED, max 6000 W |
| Solar | 12–7 | Counter-clockwise | Green | 1000 W/LED, max 6000 W |

Above 6000 W the affected segment pulses (~2 s breathing cycle).

---

### Software / Dependencies

| Component | Version |
|-----------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Part of the MicroPython standard archive |
| `ntptime` | Part of the MicroPython standard archive |
| `neopixel` | MicroPython built-in |

---

### Unit Tests (Host, no ESP32)

Logic tests for the 3-ring modules are located in `unittests/`.
They use mocks for MicroPython modules (`machine`, `network`, `utime`, `neopixel`, `umqtt`, `socket`) and run on a host machine.

```bash
python3 -m pip install pytest
python3 -m pytest -q unittests
```

---

### Configuration

Before the first flash, create two JSON files in the root of the ESP32 filesystem:

**`secrets_wifi.json`**
```json
{
  "MyHomeNetwork": "my-wifi-password",
  "Fallback-SSID": "other-password"
}
```
Multiple networks are supported — the first one found during a scan is used.

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-password"
}
```

Additional parameters at the top of `main.py`:

```python
BRIGHTNESS       = 16    # LED brightness (0–255); keep low for USB power supply
LOOP_MS          = 100   # Main loop tick in milliseconds (10 Hz)
NTP_INTERVAL_S   = 600   # NTP re-sync every 10 minutes
MQTT_BACKOFF_MAX = 6     # Max MQTT reconnect delay in seconds (WDT-compatible)
```

Additional constants in the 3-ring version:

```python
WATTS_PER_LED    = 200   # Watts per full LED (Ring 1 + Ring 2)
MAX_RING_W       = 2400  # Overflow threshold (12 × 200 W)
```

---

### MQTT Topics

| Topic | Content | Type |
|-------|---------|------|
| `Seplos/BatteryPack1/soc` | Battery pack 1 SoC | float, % |
| `Seplos/BatteryPack2/soc` | Battery pack 2 SoC | float, % |
| `Seplos/BatteryPack3/soc` | Battery pack 3 SoC | float, % |
| `solaranlage/pip/totalsolarw` | Total solar power | int, W |
| `solaranlage/pip/acoutw` | AC output power (load) | int, W |

---

### WebREPL (wireless access)

WebREPL allows code execution and file transfer over WiFi — without a USB cable.

**One-time setup** (once via USB REPL):
```python
import webrepl_setup
```
Set a password and reboot. After that WebREPL starts automatically on every boot.

**Browser interface:** http://micropython.org/webrepl/
- Host: `ws://192.168.x.x:8266/` (IP is shown in the serial boot log)

**Command-line file transfer:**
```bash
python webrepl_cli.py -p password 3-Rings/main.py 192.168.x.x:/main.py
```

**Thonny:** Run → Configure interpreter → MicroPython (ESP32) → WebREPL → IP + password.

> **Note:** The hardware WDT (8 s) is only active while `main.py` is running. `Ctrl+C` stops `main.py` and the WDT — REPL sessions are fully usable without time pressure.

---

### File Structure

#### 2-Ring version (`2-Rings/`)

```
2-Rings/
├── main.py                  # Main program (2 rings: SoC + split load/solar)
├── class_color_wheel.py     # NeoPixel driver
├── class_mqtt.py            # MQTT wrapper
├── class_wifi_connection.py # WiFi manager
├── class_ntp.py             # NTP sync
├── class_webserver.py       # HTTP status page
└── MQTT_Client.py           # Desktop test client (NOT for ESP32)
```

#### 3-Ring version (`3-Rings/`)

```
3-Rings/
├── main.py                  # Main program (3 rings: load · solar · SoC+status)
├── class_color_wheel.py     # NeoPixel driver + set_ring_watts_full + set_ring3_soc
├── class_mqtt.py            # MQTT wrapper (unchanged)
├── class_wifi_connection.py # WiFi manager (unchanged)
├── class_ntp.py             # NTP sync (unchanged)
└── class_webserver.py       # HTTP status page + MQTT status
```

---

### Flash / Deployment

```bash
# Flash MicroPython (once)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# Upload 3-ring version (mpremote)
mpremote connect /dev/ttyUSB0 cp 3-Rings/main.py :main.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_color_wheel.py :class_color_wheel.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_mqtt.py :class_mqtt.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_wifi_connection.py :class_wifi_connection.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_ntp.py :class_ntp.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_webserver.py :class_webserver.py
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json

# Upload 2-ring version (mpremote)
# mpremote connect /dev/ttyUSB0 cp 2-Rings/main.py :main.py  (and remaining files accordingly)
```

---

### Known Limitations

- `MQTT_Client.py` is intended for desktop testing only and must not be deployed to the ESP32.
- For more than ~6 LEDs at full brightness an external 5 V regulator is required.

---

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for all changes and bug fixes.

---

### License

See [LICENSE](LICENSE).

---

> **Versionen:** [`2-Rings/`](2-Rings/) — 2-Ring-Version (stabil) | [`3-Rings/`](3-Rings/) — 3-Ring-Version (neu)

---

## Deutsch

### Projektbeschreibung

Dieses Projekt implementiert einen visuellen Echtzeit-Monitor für eine Solaranlage mit Batteriespeicher auf einem **ESP32** (MicroPython). Zwei **WS2812B-NeoPixel-Ringe** (je 12 LEDs, 5 V, RGB) zeigen den aktuellen Systemzustand direkt und auf einen Blick:

| Ring | GPIO | Anzeige |
|------|------|---------|
| Ring 1 | 25 | Mittlerer SoC aller 3 Batteriepacks — **10 LEDs**, 10 %/LED, Farbverlauf **Rot** (leer) → **Grün** (voll), LED 12 = WiFi-Status (blau = online) |
| Ring 2 | 27 | **Geteilter Ring**: LEDs 1–6 = AC-Last in Watt (rot, im Uhrzeigersinn) · LEDs 12–7 = Solarleistung (grün, gegen den Uhrzeigersinn) |

**Ring-2-Skala:** 1000 W/LED mit proportionalem Teillicht-Dimming. Bei mehr als 6000 W je Segment pulsieren alle 6 Segment-LEDs als Überlauf-Signal (~2 s Atemzyklus).

Messwerte werden per **MQTT** empfangen. WLAN und MQTT-Broker werden bei Ausfall automatisch wiederhergestellt. Ein **Hardware-Watchdog (8 s)** setzt den ESP32 automatisch zurück, wenn der Loop hängt. Eine eingebettete **Mini-Webseite** (Port 80, Auto-Refresh alle 10 s) zeigt die aktuellen Rohwerte im Browser an.

---

### Hardware

- **Board**: ESP32 (z. B. ESP32 DevKit V1)
- **LEDs**: 2× NeoPixel-Ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Verbindung**: WLAN (2,4 GHz), MQTT-Broker im lokalen Netz

#### Verkabelung

```
ESP32 GPIO 25  →  DIN  Ring 1  (SoC-Anzeige)
ESP32 GPIO 27  →  DIN  Ring 2  (Energie-Anzeige)
5 V            →  +5V  beide Ringe
GND            →  GND  alle
```

> Für mehr als ~6 LEDs bei voller Helligkeit einen externen 5-V-Spannungsregler mit ausreichend Strom verwenden (je Ring max. ~720 mA bei voller Weißhelligkeit). Bei `BRIGHTNESS = 16` reicht USB-Versorgung.

---

### LED-Anzeige im Detail

#### Ring 1 — Batterie SoC (GPIO 25)

| Index | LED | Funktion |
|-------|-----|----------|
| 0–9 | 1–10 | SoC-Gradient, 10 %/LED, Rot (0 %) → Grün (100 %) |
| 10 | 11 | MQTT-Status: **Magenta 50 %** = verbunden · **Aus** = getrennt |
| 11 | 12 | WiFi-Status: **Blau 50 %** = online · **Aus** = offline |

Teillicht-Dimming: z. B. 75 % → LED 1–7 voll + LED 8 bei 50 % Helligkeit.

#### Ring 2 — Energie (GPIO 27)

```
       LED 12 (Solar)
    11         1  (Last)
  10             2
  9               3
    8           4
       7     5
          6
```

| Segment | LEDs | Richtung | Farbe | Skala |
|---------|------|----------|-------|-------|
| AC-Last | 1–6 | Uhrzeigersinn | Rot | 1000 W/LED, max 6000 W |
| Solar | 12–7 | Gegen den UZS | Grün | 1000 W/LED, max 6000 W |

Bei Überlauf (> 6000 W) pulsiert das gesamte Segment (~2 s Atemzyklus).

---

### Software / Abhängigkeiten

| Komponente | Version |
|------------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Teil des MicroPython-Standardarchivs |
| `ntptime` | Teil des MicroPython-Standardarchivs |
| `neopixel` | MicroPython built-in |

---

### Konfiguration

Vor dem ersten Flashen zwei JSON-Dateien im Wurzelverzeichnis des ESP32-Dateisystems anlegen:

**`secrets_wifi.json`**
```json
{
  "MeinHeimnetz": "MeinWLAN-Passwort",
  "Fallback-SSID": "anderesPW"
}
```
Mehrere Netzwerke werden unterstützt — das erste gefundene wird verwendet.

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-passwort"
}
```

Weitere Parameter am Anfang von `main.py`:

```python
BRIGHTNESS       = 16    # LED-Helligkeit (0–255); niedrig lassen für USB-Versorgung
LOOP_MS          = 100   # Haupt-Loop-Takt in Millisekunden (10 Hz)
NTP_INTERVAL_S   = 600   # NTP-Resync alle 10 Minuten
MQTT_BACKOFF_MAX = 6     # Max. MQTT-Reconnect-Delay in Sekunden (WDT-kompatibel)
```

---

### MQTT-Topics

| Topic | Inhalt | Typ |
|-------|--------|-----|
| `Seplos/BatteryPack1/soc` | SoC Batteriepack 1 | float, % |
| `Seplos/BatteryPack2/soc` | SoC Batteriepack 2 | float, % |
| `Seplos/BatteryPack3/soc` | SoC Batteriepack 3 | float, % |
| `solaranlage/pip/totalsolarw` | Gesamte Solarleistung | int, W |
| `solaranlage/pip/acoutw` | AC-Ausgangsleistung (Last) | int, W |

---

### WebREPL (drahtloser Zugriff)

WebREPL ermöglicht Code-Ausführung und Dateiübertragung über WLAN — ohne USB-Kabel.

**Einmalige Einrichtung** (einmalig per USB-REPL):
```python
import webrepl_setup
```
Passwort setzen und neu starten. Danach startet WebREPL bei jedem Boot automatisch.

**Browser-Interface:** http://micropython.org/webrepl/
- Host: `ws://192.168.x.x:8266/` (IP steht im seriellen Boot-Log)

**Dateiübertragung per Kommandozeile:**
```bash
python webrepl_cli.py -p passwort code/main.py 192.168.x.x:/main.py
```

**Thonny:** Run → Configure interpreter → MicroPython (ESP32) → WebREPL → IP + Passwort.

> **Hinweis:** Der Hardware-WDT (8 s) ist nur aktiv, solange `main.py` läuft. Ein `Ctrl+C` stoppt `main.py` und damit auch den WDT — REPL-Sitzungen sind uneingeschränkt nutzbar.

---

### Dateistruktur

#### 2-Ring-Version (`2-Rings/`)

```
2-Rings/
├── main.py                  # Hauptprogramm (2 Ringe: SoC + Last/Solar geteilt)
├── class_color_wheel.py     # NeoPixel-Treiber
├── class_mqtt.py            # MQTT-Wrapper
├── class_wifi_connection.py # WLAN-Manager
├── class_ntp.py             # NTP-Sync
├── class_webserver.py       # HTTP-Statusseite
└── MQTT_Client.py           # Desktop-Testclient (NICHT für ESP32)
```

#### 3-Ring-Version (`3-Rings/`) — neu

```
3-Rings/
├── main.py                  # Hauptprogramm (3 Ringe: Last · Solar · SoC+Status)
├── class_color_wheel.py     # NeoPixel-Treiber + set_ring_watts_full + set_ring3_soc
├── class_mqtt.py            # MQTT-Wrapper (unverändert)
├── class_wifi_connection.py # WLAN-Manager (unverändert)
├── class_ntp.py             # NTP-Sync (unverändert)
└── class_webserver.py       # HTTP-Statusseite + MQTT-Status
```

---

### Flash / Deployment

```bash
# MicroPython flashen (einmalig)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# 3-Ring-Version übertragen (mpremote)
mpremote connect /dev/ttyUSB0 cp 3-Rings/main.py :main.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_color_wheel.py :class_color_wheel.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_mqtt.py :class_mqtt.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_wifi_connection.py :class_wifi_connection.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_ntp.py :class_ntp.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_webserver.py :class_webserver.py
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json

# 2-Ring-Version übertragen (mpremote)
# mpremote connect /dev/ttyUSB0 cp 2-Rings/main.py :main.py  (und restliche Dateien analog)
```

---

### Bekannte Einschränkungen

- `MQTT_Client.py` ist ausschließlich für Desktop-Tests gedacht und darf nicht auf den ESP32 übertragen werden.

---

### Changelog

Siehe [CHANGELOG.md](CHANGELOG.md) für alle Bugfixes und Änderungen.

---

### Lizenz

Siehe [LICENSE](LICENSE).

---
---

## English <a name="english"></a>

### Project Description

This project implements a real-time visual monitor for a solar power system with battery storage, running on an **ESP32** (MicroPython). Two **WS2812B NeoPixel rings** (12 LEDs each, 5 V, RGB) display the current system state at a glance:

| Ring | GPIO | Display |
|------|------|---------|
| Ring 1 | 25 | Average SoC of all 3 battery packs — **10 LEDs**, 10 %/LED, colour gradient **Red** (empty) → **Green** (full), LED 12 = WiFi status (blue = online) |
| Ring 2 | 27 | **Split ring**: LEDs 1–6 = AC load in Watts (red, clockwise) · LEDs 12–7 = solar power (green, counter-clockwise) |

**Ring 2 scale:** 1000 W/LED with proportional partial-LED dimming. Above 6000 W per segment all 6 segment LEDs pulse as an overflow signal (~2 s breathing cycle).

Measurements are received via **MQTT**. WiFi and MQTT broker are automatically restored on failure. A **hardware watchdog (8 s)** resets the ESP32 if the main loop stalls. A built-in **mini web page** (port 80, auto-refresh every 10 s) shows current raw values in the browser.

---

### Hardware

- **Board**: ESP32 (e.g. ESP32 DevKit V1)
- **LEDs**: 2× NeoPixel ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Connectivity**: WiFi (2.4 GHz), MQTT broker on the local network

#### Wiring

```
ESP32 GPIO 25  →  DIN  Ring 1  (SoC display)
ESP32 GPIO 27  →  DIN  Ring 2  (energy display)
5 V            →  +5V  both rings
GND            →  GND  all
```

> For more than ~6 LEDs at full brightness, use an external 5 V regulator with sufficient current capacity (up to ~720 mA per ring at full white brightness). At `BRIGHTNESS = 16` USB power is sufficient.

---

### LED Display Details

#### Ring 1 — Battery SoC (GPIO 25)

| Index | LED | Function |
|-------|-----|----------|
| 0–9 | 1–10 | SoC gradient, 10 %/LED, Red (0 %) → Green (100 %) |
| 10 | 11 | MQTT status: **Magenta 50 %** = connected · **Off** = disconnected |
| 11 | 12 | WiFi status: **Blue 50 %** = online · **Off** = offline |

Partial dimming: e.g. 75 % → LEDs 1–7 full + LED 8 at 50 % brightness.

#### Ring 2 — Energy (GPIO 27)

| Segment | LEDs | Direction | Colour | Scale |
|---------|------|-----------|--------|-------|
| AC Load | 1–6 | Clockwise | Red | 1000 W/LED, max 6000 W |
| Solar | 12–7 | Counter-clockwise | Green | 1000 W/LED, max 6000 W |

Above 6000 W the affected segment pulses (~2 s breathing cycle).

---

### Software / Dependencies

| Component | Version |
|-----------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Part of the MicroPython standard archive |
| `ntptime` | Part of the MicroPython standard archive |
| `neopixel` | MicroPython built-in |

---

### Configuration

Before the first flash, create two JSON files in the root of the ESP32 filesystem:

**`secrets_wifi.json`**
```json
{
  "MyHomeNetwork": "my-wifi-password",
  "Fallback-SSID": "other-password"
}
```
Multiple networks are supported — the first one found during a scan is used.

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-password"
}
```

Additional parameters at the top of `main.py`:

```python
BRIGHTNESS       = 16    # LED brightness (0–255); keep low for USB power supply
LOOP_MS          = 100   # Main loop tick in milliseconds (10 Hz)
NTP_INTERVAL_S   = 600   # NTP re-sync every 10 minutes
MQTT_BACKOFF_MAX = 6     # Max MQTT reconnect delay in seconds (WDT-compatible)
```

---

### MQTT Topics

| Topic | Content | Type |
|-------|---------|------|
| `Seplos/BatteryPack1/soc` | Battery pack 1 SoC | float, % |
| `Seplos/BatteryPack2/soc` | Battery pack 2 SoC | float, % |
| `Seplos/BatteryPack3/soc` | Battery pack 3 SoC | float, % |
| `solaranlage/pip/totalsolarw` | Total solar power | int, W |
| `solaranlage/pip/acoutw` | AC output power (load) | int, W |

---

### WebREPL (wireless access)

WebREPL allows code execution and file transfer over WiFi — without a USB cable.

**One-time setup** (once via USB REPL):
```python
import webrepl_setup
```
Set a password and reboot. After that WebREPL starts automatically on every boot.

**Browser interface:** http://micropython.org/webrepl/
- Host: `ws://192.168.x.x:8266/` (IP is shown in the serial boot log)

**Command-line file transfer:**
```bash
python webrepl_cli.py -p password code/main.py 192.168.x.x:/main.py
```

**Thonny:** Run → Configure interpreter → MicroPython (ESP32) → WebREPL → IP + password.

> **Note:** The hardware WDT (8 s) is only active while `main.py` is running. `Ctrl+C` stops `main.py` and the WDT — REPL sessions are fully usable without time pressure.

---

### File Structure

#### 2-Ring version (`2-Rings/`)

```
2-Rings/
├── main.py                  # Main program (2 rings: SoC + split load/solar)
├── class_color_wheel.py     # NeoPixel driver
├── class_mqtt.py            # MQTT wrapper
├── class_wifi_connection.py # WiFi manager
├── class_ntp.py             # NTP sync
├── class_webserver.py       # HTTP status page
└── MQTT_Client.py           # Desktop test client (NOT for ESP32)
```

#### 3-Ring version (`3-Rings/`) — new

```
3-Rings/
├── main.py                  # Main program (3 rings: load · solar · SoC+status)
├── class_color_wheel.py     # NeoPixel driver + set_ring_watts_full + set_ring3_soc
├── class_mqtt.py            # MQTT wrapper (unchanged)
├── class_wifi_connection.py # WiFi manager (unchanged)
├── class_ntp.py             # NTP sync (unchanged)
└── class_webserver.py       # HTTP status page + MQTT status
```

---

### Flash / Deployment

```bash
# Flash MicroPython (once)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# Upload 3-ring version (mpremote)
mpremote connect /dev/ttyUSB0 cp 3-Rings/main.py :main.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_color_wheel.py :class_color_wheel.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_mqtt.py :class_mqtt.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_wifi_connection.py :class_wifi_connection.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_ntp.py :class_ntp.py
mpremote connect /dev/ttyUSB0 cp 3-Rings/class_webserver.py :class_webserver.py
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json

# Upload 2-ring version (mpremote)
# mpremote connect /dev/ttyUSB0 cp 2-Rings/main.py :main.py  (and remaining files accordingly)
```

---

### Known Limitations

- `MQTT_Client.py` is intended for desktop testing only and must not be deployed to the ESP32.

---

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for all bug fixes and changes.

---

### License

See [LICENSE](LICENSE).


> **DE** | [**EN ↓**](#english)

---

## Deutsch

### Projektbeschreibung

Dieses Projekt implementiert einen visuellen Echtzeit-Monitor für eine Solaranlage mit Batteriespeicher auf einem **ESP32** (MicroPython). Zwei **WS2812B-NeoPixel-Ringe** (je 12 LEDs, 5 V, RGB) zeigen den aktuellen Systemzustand direkt und auf einen Blick:

| Ring | GPIO | Anzeige |
|------|------|---------|
| Ring 1 | 25 | Mittlerer SoC (State of Charge) beider Batteriepacks — Farbverlauf **Rot** (leer) → **Grün** (voll) |
| Ring 2 | 27 | **Grün**: Solarleistung (bis 2500 W = 12 LEDs) · **Rot**: AC-Last (überlagert) |

Messwerte werden per **MQTT** empfangen. Die WLAN-Verbindung und der MQTT-Broker werden bei Ausfall automatisch wiederhergestellt. Eine eingebettete **Mini-Webseite** (Port 80) zeigt die aktuellen Rohwerte im Browser an.

---

### Hardware

- **Board**: ESP32 (z. B. ESP32 DevKit V1)
- **LEDs**: 2× NeoPixel-Ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Verbindung**: WLAN (2,4 GHz), MQTT-Broker im lokalen Netz

#### Verkabelung

```
ESP32 GPIO 25  →  DIN  Ring 1
ESP32 GPIO 27  →  DIN  Ring 2
5 V            →  +5V  beide Ringe
GND            →  GND  alle
```

> Für mehr als ~6 LEDs bei voller Helligkeit einen externen 5-V-Spannungsregler mit ausreichend Strom verwenden (je Ring max. ~720 mA bei voller Weißhelligkeit).

---

### Software / Abhängigkeiten

| Komponente | Version |
|------------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Teil des MicroPython-Standardarchivs |
| `ntptime` | Teil des MicroPython-Standardarchivs |
| `neopixel` | MicroPython built-in |

---

### Konfiguration

Vor dem ersten Flashen zwei JSON-Dateien im Wurzelverzeichnis des ESP32-Dateisystems anlegen:

**`secrets_wifi.json`**
```json
{
  "MeinHeimnetz": "MeinWLAN-Passwort",
  "Fallback-SSID": "anderesPW"
}
```

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-passwort"
}
```

Weitere Parameter am Anfang von `main.py` als Konstanten:

```python
SOLAR_MAX_W    = 2500   # Wechselrichter-Nennleistung in Watt → 100 % = 12 LEDs
BRIGHTNESS     = 16     # LED-Helligkeit (0–255); niedrig lassen für 5-V-USB-Versorgung
LOOP_MS        = 100    # Haupt-Loop-Takt in Millisekunden
NTP_INTERVAL_S = 600    # NTP-Resync alle 10 Minuten
```

---

### MQTT-Topics

| Topic | Inhalt | Einheit |
|-------|--------|---------|
| `mqtt.0.Seplos.BatteryPack1.soc` | SoC Batteriepack 1 | % (0–100) |
| `mqtt.0.Seplos.BatteryPack2.soc` | SoC Batteriepack 2 | % (0–100) |
| `mqtt.0.solaranlage.pip.totalsolarw` | Gesamte Solarleistung | W |
| `mqtt.0.solaranlage.pip.acoutw` | AC-Ausgangsleistung | W |

---

### Dateistruktur

```
code/
├── main.py                  # Hauptprogramm, Main-Loop, MQTT-Callback
├── class_color_wheel.py     # NeoPixel-Treiber (non-blocking, precomputed gradient)
├── class_mqtt.py            # MQTT-Wrapper (umqtt.robust, Keepalive, reconnect)
├── class_wifi_connection.py # WLAN-Manager (Scan, Reconnect, Credentials aus JSON)
├── class_ntp.py             # NTP-Sync mit CET/CEST-Korrektur
├── class_webserver.py       # HTTP-Statusseite (Port 80, _thread)
├── MQTT_Client.py           # Desktop-Testclient (paho-mqtt, Python 3 — NICHT für ESP32)
└── class_solar_values.py    # Ungenutzte Hilfsklasse (TODO: entfernen)
```

---

### Flash / Deployment

```bash
# MicroPython flashen (einmalig)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# Dateien übertragen (mpremote oder ampy)
mpremote connect /dev/ttyUSB0 cp code/main.py :main.py
mpremote connect /dev/ttyUSB0 cp code/class_*.py :
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json
```

---

### Bekannte Einschränkungen / TODOs

- `SOLAR_MAX_W` ggf. an die tatsächliche Wechselrichter-Nennleistung anpassen
- Verhalten bei MQTT/WLAN-Ausfall (einfrieren / ausgehen / Heartbeat-Blink) ist konfigurierbar, aber noch nicht als Konstante exponiert
- `class_solar_values.py` und `MQTT_Client.py` sollten aus dem ESP32-Deployment ausgeschlossen werden (→ `.gitignore` oder separates Verzeichnis)

---

### Changelog

Siehe [CHANGELOG.md](CHANGELOG.md) für alle Bugfixes und Änderungen.

---

### Lizenz

Siehe [LICENSE](LICENSE).

---
---

## English <a name="english"></a>

### Project Description

This project implements a real-time visual monitor for a solar power system with battery storage, running on an **ESP32** (MicroPython). Two **WS2812B NeoPixel rings** (12 LEDs each, 5 V, RGB) display the current system state at a glance:

| Ring | GPIO | Display |
|------|------|---------|
| Ring 1 | 25 | Average SoC (State of Charge) of both battery packs — colour gradient **Red** (empty) → **Green** (full) |
| Ring 2 | 27 | **Green**: solar power (up to 2500 W = 12 LEDs) · **Red**: AC load (overlaid) |

Measurements are received via **MQTT**. The WiFi connection and MQTT broker are automatically restored on failure. A built-in **mini web page** (port 80) shows current raw values in the browser.

---

### Hardware

- **Board**: ESP32 (e.g. ESP32 DevKit V1)
- **LEDs**: 2× NeoPixel ring, 12 × WS2812B, RGB (bpp = 3), 5 V
- **Connectivity**: WiFi (2.4 GHz), MQTT broker on the local network

#### Wiring

```
ESP32 GPIO 25  →  DIN  Ring 1
ESP32 GPIO 27  →  DIN  Ring 2
5 V            →  +5V  both rings
GND            →  GND  all
```

> For more than ~6 LEDs at full brightness, use an external 5 V regulator with sufficient current capacity (up to ~720 mA per ring at full white brightness).

---

### Software / Dependencies

| Component | Version |
|-----------|---------|
| MicroPython | ≥ 1.20 |
| `umqtt.robust` | Part of the MicroPython standard archive |
| `ntptime` | Part of the MicroPython standard archive |
| `neopixel` | MicroPython built-in |

---

### Configuration

Before the first flash, create two JSON files in the root of the ESP32 filesystem:

**`secrets_wifi.json`**
```json
{
  "MyHomeNetwork": "my-wifi-password",
  "Fallback-SSID": "other-password"
}
```

**`secrets_mqtt.json`**
```json
{
  "secretHost": "192.168.1.100",
  "secretPort": "1883",
  "secretUser": "mqtt-user",
  "secretPass": "mqtt-password"
}
```

Additional parameters at the top of `main.py` as constants:

```python
SOLAR_MAX_W    = 2500   # Inverter rated output in Watts → 100 % = 12 LEDs
BRIGHTNESS     = 16     # LED brightness (0–255); keep low for 5 V USB power supply
LOOP_MS        = 100    # Main loop tick in milliseconds
NTP_INTERVAL_S = 600    # NTP re-sync every 10 minutes
```

---

### MQTT Topics

| Topic | Content | Unit |
|-------|---------|------|
| `mqtt.0.Seplos.BatteryPack1.soc` | Battery pack 1 SoC | % (0–100) |
| `mqtt.0.Seplos.BatteryPack2.soc` | Battery pack 2 SoC | % (0–100) |
| `mqtt.0.solaranlage.pip.totalsolarw` | Total solar power | W |
| `mqtt.0.solaranlage.pip.acoutw` | AC output power | W |

---

### File Structure

```
code/
├── main.py                  # Main program, main loop, MQTT callback
├── class_color_wheel.py     # NeoPixel driver (non-blocking, precomputed gradient)
├── class_mqtt.py            # MQTT wrapper (umqtt.robust, keepalive, reconnect)
├── class_wifi_connection.py # WiFi manager (scan, reconnect, credentials from JSON)
├── class_ntp.py             # NTP sync with CET/CEST correction
├── class_webserver.py       # HTTP status page (port 80, _thread)
├── MQTT_Client.py           # Desktop test client (paho-mqtt, Python 3 — NOT for ESP32)
└── class_solar_values.py    # Unused helper class (TODO: remove)
```

---

### Flash / Deployment

```bash
# Flash MicroPython (once)
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin

# Upload files (mpremote or ampy)
mpremote connect /dev/ttyUSB0 cp code/main.py :main.py
mpremote connect /dev/ttyUSB0 cp code/class_*.py :
mpremote connect /dev/ttyUSB0 cp secrets_wifi.json :secrets_wifi.json
mpremote connect /dev/ttyUSB0 cp secrets_mqtt.json :secrets_mqtt.json
```

---

### Known Limitations / TODOs

- Adjust `SOLAR_MAX_W` to match your inverter's actual rated output
- LED behaviour during MQTT/WiFi outage (freeze / turn off / heartbeat blink) is configurable but not yet exposed as a top-level constant
- `class_solar_values.py` and `MQTT_Client.py` should be excluded from the ESP32 deployment (→ `.gitignore` or separate directory)

---

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for all bug fixes and changes.

---

### License

See [LICENSE](LICENSE).
