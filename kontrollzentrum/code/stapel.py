"""Stapel: eine Prüfung nacheinander für mehrere Ziele, jedes Ziel mit eigener Erlaubnis.

Vorab wird jedes Ziel geprüft (Erlaubnis vorhanden, im Umfang, nicht abgelaufen). Nur freigegebene Ziele
kommen in die Reihe. Während des Laufs prüft die Prüfung Umfang und Erlaubnis ohnehin vor jedem Schritt.
"""

import umfang


def plan(ziele: list[str], freigaben: dict, jetzt=None) -> list[dict]:
    """Je Ziel {ziel, ok, grund}. ok=True heißt: Erlaubnis gültig, Ziel im Umfang, Zeitfenster passt jetzt."""
    ergebnis = []
    for ziel in ziele:
        f = freigaben.get(ziel)
        ok, grund = umfang.darf_jetzt(ziel, f, jetzt)
        ergebnis.append({"ziel": ziel, "ok": ok,
                         "grund": f"erlaubt von {f.get('wer', '–')}" if ok else grund})
    return ergebnis


def freigegebene(vorplan: list[dict]) -> list[str]:
    """Nur die Ziele, die vorab bestanden haben, in der Reihenfolge der Auswahl."""
    return [e["ziel"] for e in vorplan if e["ok"]]
