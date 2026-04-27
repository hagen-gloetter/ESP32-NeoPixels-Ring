"""
class_webserver.py — Minimal HTTP status page for ESP32 (MicroPython).

Serves a single auto-refreshing HTML page on port 80 showing the current
solar/battery state. Runs in a background thread started at construction
time so it never blocks the main loop.

Typical usage::

    from class_webserver import Webserver

    state = {"SOC1": 0.0, "SOC2": 0.0, "SOC3": 0.0,
             "acoutw": 0, "totalsolarw": 0, "mqtt_ok": False}
    server = Webserver(state)   # starts background thread immediately
    # ...
    server.stop_webserver()     # graceful shutdown

The page refreshes every 10 seconds via an HTML meta tag.
"""

import socket
import _thread


class Webserver:
    """Minimal single-page HTTP server running in a background thread.

    Reads a shared ``state`` dict and renders the current values as HTML.
    The background thread is started automatically in ``__init__``.

    Args:
        state (dict): Shared state dictionary with the following keys:

            - ``SOC1`` (float): Battery Pack 1 State of Charge in %.
            - ``SOC2`` (float): Battery Pack 2 State of Charge in %.
            - ``SOC3`` (float): Battery Pack 3 State of Charge in %.
            - ``acoutw`` (int): AC output load in Watts.
            - ``totalsolarw`` (int): Total solar production in Watts.
            - ``mqtt_ok`` (bool): True if MQTT broker is connected.

    Notes:
        The state dict is read from the server thread concurrently with
        writes from the main loop.  MicroPython's GIL protects individual
        dict item reads for int/float/bool values, so no explicit lock is
        needed for this read-only access pattern.
    """

    def __init__(self, state):
        self._state = state
        self._run = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 80))
        sock.listen(3)
        self._sock = sock
        _thread.start_new_thread(self._serve, ())
        print("Webserver started on :80")

    def _serve(self):
        while self._run:
            conn = None
            try:
                conn, addr = self._sock.accept()
                conn.recv(1024)   # consume request headers (not evaluated)
                body = self._html().encode()
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    b"Connection: close\r\n\r\n"
                    + body
                )
            except Exception as e:
                if conn is not None:
                    try:
                        conn.sendall(
                            b"HTTP/1.1 500 Internal Server Error\r\n"
                            b"Connection: close\r\n\r\n"
                            + str(e).encode()
                        )
                    except Exception:
                        pass
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def _html(self):
        """Render the HTML status page from the current state dict."""
        s = self._state
        soc1 = float(s.get("SOC1", 0))
        soc2 = float(s.get("SOC2", 0))
        soc3 = float(s.get("SOC3", 0))
        avg  = (soc1 + soc2 + soc3) / 3.0
        mqtt_status = "connected" if s.get("mqtt_ok", False) else "disconnected"
        return (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='10'>"
            "<title>Solar Monitor</title></head><body>"
            "<h1>Solar Monitor</h1>"
            "<h2>Ring 3 — Battery SoC</h2>"
            "<p>Battery Pack 1 SoC: {:.1f}%</p>"
            "<p>Battery Pack 2 SoC: {:.1f}%</p>"
            "<p>Battery Pack 3 SoC: {:.1f}%</p>"
            "<p><strong>Average SoC: {:.1f}%</strong></p>"
            "<h2>Ring 1 — AC Load</h2>"
            "<p>AC Output: {} W</p>"
            "<h2>Ring 2 — Solar</h2>"
            "<p>Solar Total: {} W</p>"
            "<h2>Status</h2>"
            "<p>MQTT: {}</p>"
            "</body></html>"
        ).format(
            soc1, soc2, soc3, avg,
            int(s.get("acoutw", 0)),
            int(s.get("totalsolarw", 0)),
            mqtt_status,
        )

    def stop_webserver(self):
        """Signal the server thread to stop and close the listen socket.

        The background thread exits after its current ``accept()`` unblocks.
        """
        self._run = False
        try:
            self._sock.close()
        except Exception:
            pass
