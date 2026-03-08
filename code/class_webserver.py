# class_webserver.py
# Simple HTTP status page for ESP32 (MicroPython), runs in background thread.
# FIX: conn referenced before assignment in except (NameError),
#      html_code used str+float/int (TypeError),
#      now receives shared state dict instead of reading stale module globals,
#      proper bytes HTTP headers, SO_REUSEADDR, finally block for socket cleanup.

import socket
import _thread


class Webserver:
    """
    Minimal HTTP server. Accepts a shared state dict and serves a status page.

    state keys: SOC1 (float), SOC2 (float), acoutw (int), totalsolarw (int)

    NOTE: state dict is read from a second thread. In MicroPython the GIL
    protects individual dict lookups, so explicit locking is not required for
    simple integer/float reads, but be aware of this if the structure grows.
    """

    def __init__(self, state):
        self._state = state
        self._run = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # FIX: allow immediate rebind after restart (avoid TIME_WAIT errors)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 80))
        sock.listen(3)
        self._sock = sock
        _thread.start_new_thread(self._serve, ())
        print("Webserver started on :80")

    def _serve(self):
        while self._run:
            conn = None   # FIX: always defined before except block
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
                # FIX: always close connection socket to avoid resource leak
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def _html(self):
        """Render status page. FIX: use .format() instead of str+float/int."""
        s = self._state
        return (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='10'>"
            "<title>Solar Monitor</title></head><body>"
            "<h1>Solar Monitor</h1>"
            "<p>Battery Pack 1 SoC: {:.1f}%</p>"
            "<p>Battery Pack 2 SoC: {:.1f}%</p>"
            "<p>AC Output: {} W</p>"
            "<p>Solar Total: {} W</p>"
            "</body></html>"
        ).format(
            float(s.get("SOC1", 0)),
            float(s.get("SOC2", 0)),
            int(s.get("acoutw", 0)),
            int(s.get("totalsolarw", 0)),
        )

    def stop_webserver(self):
        self._run = False
        try:
            self._sock.close()
        except Exception:
            pass

