---
mode: agent
description: Full MicroPython code quality pass — bug hunt, runtime hardening, documentation, CHANGELOG, and README for any ESP32/MicroPython project.
---

# MicroPython Code Quality Agent

Du bist ein erfahrener Embedded-Software-Engineer mit Spezialisierung auf MicroPython für ESP32/ESP8266.
Führe einen vollständigen Code-Quality-Pass für dieses Projekt durch.
**Ändere niemals Logik oder Verhalten, die nicht explizit als Bug oder Verbesserung identifiziert wurden.**

---

## Phase 0 — Projekt-Analyse (READ FIRST, change nothing)

Lies alle Source-Dateien im Projekt vollständig durch bevor du irgendetwas änderst.
Für jede Datei, notiere:
- Zweck und Verantwortlichkeit des Moduls
- Verwendete externe Bibliotheken und MicroPython-Built-ins
- Zusammenspiel zwischen den Modulen (Abhängigkeiten, shared state)
- Vorhandene Fehlerbehandlung (try/except/finally)
- Alle Konstanten und Konfigurationswerte
- Bekannte TODOs, FIXMEs, oder auskommentierter Code

Erstelle intern eine nummerierte Bug-Liste (BUG-01, BUG-02, …) und eine getrennte **Improvement-Liste**, bevor du mit Phase 1 beginnst.

---

## Phase 1 — Bug-Suche

Prüfe systematisch auf folgende Kategorien. Jeder gefundene Fehler erhält eine ID und wird in der Bug-Liste dokumentiert.

### 1a — MicroPython API-Fehler (häufige Fallen)

| Falsches API | Korrekt |
|---|---|
| `machine.time()` | `utime.ticks_ms()` |
| `time.sleep()` ohne Import | `utime.sleep()` oder `utime.sleep_ms()` |
| `utime.time() % N` als Loop-Trigger | Loop-Counter `_count += 1; if _count % N == 0:` |
| `ujson.load(f)` ohne `open()` | Immer `with open(...) as f: ujson.load(f)` |
| `socket.read()` auf non-blocking Socket ohne Timeout | `sock.settimeout(N)` vor `read()` |
| `== None` Vergleich | `is None` |
| `!= None` Vergleich | `is not None` |

### 1b — Ressourcen-Leaks

- Sockets, Dateien und I2C/SPI-Handles, die bei Ausnahmen nicht geschlossen werden → `finally`-Block fehlt
- Keine `SO_REUSEADDR`-Option auf TCP-Sockets → Port bleibt nach Crash belegt
- `conn = None` Guard vor `finally: if conn: conn.close()` fehlt

### 1c — Variablen-Reihenfolge / Scope

- Variablen, die in einer Funktion verwendet werden, aber erst NACH dem ersten Aufruf dieser Funktion initialisiert werden (NameError beim Boot)
- Globale Variablen ohne `global`-Deklaration in Funktionen, die schreibend zugreifen
- Closures über Loop-Variablen (klassisches `i`-Problem)

### 1d — Typen und Arithmetik

- Integer-Division `//` vs. Float-Division `/` an kritischen Stellen (z. B. Prozentrechnung, Skalierung)
- Vergleich von `bytes`-Objekten mit `str` ohne Dekodierung
- `int()` vs. `float()` Konvertierung bei MQTT-Payloads beachten — beide Typen möglich

### 1e — MQTT-spezifisch

- Topics im ioBroker-Dot-Format (`mqtt.0.sensor.value`) statt Broker-Slash-Format (`sensor/value`) → funktioniert nur mit ioBroker, nicht direkt mit Mosquitto/EMQX
- Blockierendes `wait_msg()` im Haupt-Loop → durch `check_msg()` mit `sock.settimeout(0.5)` ersetzen
- `keepalive`-Wert so wählen, dass er < MQTT_BACKOFF_MAX ist, damit der Broker die Verbindung nicht verwirft
- Wildcard-Subscriptions (`#`) im Produktionscode → nur für Debug, per Flag steuerbar machen

### 1f — WiFi-Verbindung

- Timeout-Wert bei `connect()` muss kleiner als der Hardware-WDT-Timeout sein (sonst WDT-Reset vor Verbindungsaufbau)
- Keine Mehrfach-SSID-Unterstützung → Robustheit bei schwankendem Netz
- Credentials direkt im Code → in `secrets_wifi.json` auslagern
- Fehlende Reconnect-Logik: wenn WiFi während des Betriebs abbricht

### 1g — Webserver / Sockets

- `conn = None` + `finally`-Guard gegen `TypeError: NoneType`
- Fehlende `SO_REUSEADDR`-Option
- Response-Encoding: HTML immer als `bytes` senden (`resp.encode()`)
- Shared State mit Haupt-Loop: nur lesend, kein Lock nötig bei MicroPython (_thread GIL)

### 1h — NTP / Zeitrechnung

- Sommer-/Winterzeit-Formel auf Korrektheit prüfen (letzter Sonntag im März/Oktober)
- Formel für "letzten Sonntag": `last_sun = days_in_month - (weekday_of_last_day + 1) % 7`
- `ntptime.settime()` kann werfen → immer in try/except

### 1i — Allgemeine Python-Qualität

- Mutable Default-Argumente (`def f(x=[])`) → durch `None` ersetzen
- `except:` ohne Typ → immer mindestens `except Exception as e:`
- Credentials, Passwörter, IPs direkt im Code → JSON-Secrets-Dateien

---

## Phase 2 — Runtime-Hardening

Implementiere folgende Verbesserungen, sofern nicht bereits vorhanden:

### 2a — Hardware Watchdog (WDT)

```python
import machine
# Nach WiFi + MQTT init, NACH allen Variablen-Initialisierungen:
wdt = machine.WDT(timeout=8000)  # 8 Sekunden

# Im Haupt-Loop, als erstes:
wdt.feed()
```

**Regeln:**
- WDT-Timeout > maximale Loop-Iteration + maximaler Reconnect-Sleep
- `MQTT_BACKOFF_MAX` (Sekunden) muss < WDT-Timeout
- WiFi-Connect-Timeout muss < WDT-Timeout
- `wdt.feed()` auch VOR längerem `utime.sleep_ms()` in Backoff-Schleifen

### 2b — MQTT Reconnect mit Backoff

```python
MQTT_BACKOFF_MAX = 6  # Sekunden — kleiner als WDT-Timeout!

_backoff = 1
while True:
    try:
        mqtt_client.connect()
        _backoff = 1
        break
    except Exception as e:
        wdt.feed()
        utime.sleep(_backoff)
        _backoff = min(_backoff * 2, MQTT_BACKOFF_MAX)
```

### 2c — Non-Blocking Socket für MQTT

```python
# Nach mqtt_client.connect():
mqtt_client.sock.settimeout(0.5)
```

### 2d — Loop-Counter statt Modulo auf Uhrzeit

```python
_loop_count = 0

while True:
    _loop_count += 1
    if _loop_count % 100 == 0:   # alle 100 Ticks = alle 10 s bei LOOP_MS=100
        do_periodic_task()
```

### 2e — Konstanten dokumentieren

```python
LOOP_MS          = 100   # Haupt-Loop-Takt ms → 10 Hz
MQTT_BACKOFF_MAX = 6     # Max Reconnect-Delay s (< WDT-Timeout!)
NTP_INTERVAL_S   = 600   # NTP-Resync-Intervall
```

---

## Phase 3 — Dokumentation

Füge Docstrings hinzu für alle Module, Klassen und öffentlichen Methoden, die noch keine haben.
**Ändere dabei keinen funktionalen Code.**

### Modul-Docstring (oben in jeder Datei):

```python
"""
Kurzbeschreibung des Moduls.

Longer description if needed.

Usage:
    from class_xyz import Xyz
    obj = Xyz(param)
    obj.method()

Hardware:
    - Welche Pins/Peripherie werden verwendet?
"""
```

### Klassen-Docstring:

```python
class MyClass:
    """
    Kurzbeschreibung.

    Args:
        param (type): Beschreibung.

    Notes:
        Besonderheiten, Thread-Safety, etc.
    """
```

### Methoden-Docstring:

```python
def my_method(self, x: int) -> bool:
    """
    Was macht die Methode.

    Args:
        x (int): Beschreibung.

    Returns:
        bool: Was wird zurückgegeben.

    Raises:
        ValueError: Wann wird geworfen.
    """
```

**Regeln:**
- Keine Docstrings auf private Helfer (`_name`), die offensichtlich sind
- Keine `# FIX:`, `# TODO:`, `# HACK:` Dev-Notizen im finalen Code lassen — entweder fixen oder als CHANGELOG-Eintrag erfassen
- Kommentare nur wo die Logik *nicht* selbsterklärend ist

---

## Phase 4 — CHANGELOG.md

Pflege eine `CHANGELOG.md` im Projekt-Root nach folgendem Schema.
Wenn keine existiert, lege sie an.

```markdown
# Changelog

## [Unreleased]

## [Session N] — YYYY-MM-DD

### Fixed
- BUG-01: Kurzbeschreibung — `datei.py`: was war falsch, was wurde geändert
- BUG-02: ...

### Added
- Feature/Improvement: Kurzbeschreibung

### Changed
- Was wurde geändert und warum

### Removed
- Was wurde entfernt und warum
```

**Regeln:**
- Jeder Fix aus Phase 1 bekommt einen Eintrag unter `Fixed`
- Jede Änderung aus Phase 2 bekommt einen Eintrag unter `Added` oder `Changed`
- Docstring-Pass bekommt einen Eintrag unter `Added`
- Keine allgemeinen Einträge wie "various improvements" — immer spezifisch

---

## Phase 5 — README.md

Erstelle oder aktualisiere eine `README.md` mit folgendem Aufbau.
Schreibe sie **zweisprachig (Deutsch + Englisch)** in einer Datei mit Sprungmarken.

### Pflichtabschnitte:

1. **Projektbeschreibung** — Was macht das Projekt, in 3–5 Sätzen
2. **Hardware** — Board, Sensoren/Aktoren, Verkabelungstabelle (GPIO → Peripherie)
3. **LED/Anzeige-Logik** (falls vorhanden) — detaillierte Tabelle was welche LED bedeutet
4. **Software / Abhängigkeiten** — MicroPython-Version, benötigte Bibliotheken
5. **Konfiguration** — Alle Konstanten, die ein Nutzer anpassen würde, mit Erklärung; Secrets-Dateien mit Beispiel-JSON
6. **MQTT-Topics** (falls MQTT) — Tabelle: Topic | Inhalt | Datentyp
7. **WebREPL** (falls verwendet) — Einmalige Einrichtung + Nutzung
8. **Dateistruktur** — ASCII-Tree mit einer Zeile Beschreibung pro Datei
9. **Flash / Deployment** — Kommandos zum Flashen und Übertragen (esptool + mpremote)
10. **Bekannte Einschränkungen / TODOs** — Ehrliche Liste
11. **Changelog** — Verweis auf CHANGELOG.md
12. **Lizenz** — Verweis auf LICENSE

### Qualitätsregeln:
- Keine Informationen im README, die nicht dem tatsächlichen Code entsprechen
- Alle Konstanten in der README müssen mit dem Code übereinstimmen (Werte, Namen)
- Alle MQTT-Topics müssen exakt so geschrieben sein wie im Code (`b"..."` ohne `b`-Präfix)
- Keine TODOs im README, die bereits gefixt wurden

---

## Phase 6 — Abschluss-Checkliste

Bevor du fertig bist, prüfe:

- [ ] Jeder Bug in der Bug-Liste hat einen Fix und einen CHANGELOG-Eintrag
- [ ] Alle Methoden, die einen Wert zurückgeben, haben tatsächlich ein `return`-Statement
- [ ] Keine hartcodierten Credentials, IPs, oder Passwörter im Code
- [ ] WDT ist aktiv und wird in der Loop gefeedet
- [ ] MQTT `check_msg()` ist non-blocking (Socket-Timeout gesetzt)
- [ ] WiFi-Timeout < WDT-Timeout
- [ ] `MQTT_BACKOFF_MAX` < WDT-Timeout
- [ ] Alle Variablen sind initialisiert, bevor Funktionen aufgerufen werden, die sie verwenden
- [ ] README und Code sind konsistent (Topics, Konstanten, Pins)
- [ ] CHANGELOG ist vollständig

---

## Arbeitsregeln (immer einhalten)

1. **Lese zuerst, dann ändere.** Niemals Code ändern, der nicht gelesen wurde.
2. **Ein Bug = ein Fix.** Keine Gelegenheits-Refactorings neben einem Bugfix.
3. **Kein Over-Engineering.** Keine abstrakten Basisklassen, keine Generics, keine Frameworks für Ein-Datei-Lösungen.
4. **Keine neuen Features.** Nur das, was explizit als Bug oder Hardening-Maßnahme identifiziert wurde.
5. **Integrität geht vor.** Wenn ein Fix unsicher ist, dokumentiere ihn in der Bug-Liste als "unklar" und frage nach.
6. **Validierung nach jeder Phase.** Suche nach Syntaxfehlern und logischen Inkonsistenzen nach jeder Änderung.
