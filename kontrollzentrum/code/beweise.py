"""Beweise prüfen: stimmt noch, was das Beweisprotokoll über jeden Lauf sagt?

Jeder Lauf hat einen Eintrag mit SHA-256-Prüfsumme seiner Rohausgabe (beweise.jsonl).
Diese Datei vergleicht die Prüfsummen mit den Protokollen auf der Platte. Ergebnis je Eintrag:
ok, verändert, fehlt oder ohne_prüfsumme. Die Funktion ändert nichts.
"""

import hashlib
import json
from pathlib import Path


def _sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def pruefe(beweis_datei: Path, runs_dir: Path) -> list[dict]:
    """Gibt für jeden Eintrag {lauf, befehl, status} zurück. Fehlerhafte Zeilen werden als Fehler gemeldet."""
    try:
        zeilen = Path(beweis_datei).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    ergebnis = []
    for zeile in zeilen:
        if not zeile.strip():
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            ergebnis.append({"lauf": "?", "befehl": zeile[:80], "status": "fehlerhaft"})
            continue
        ergebnis.append({"lauf": eintrag.get("lauf", "?"), "befehl": eintrag.get("befehl", ""),
                         "status": _status(eintrag, Path(runs_dir))})
    return ergebnis


def _status(eintrag: dict, runs_dir: Path) -> str:
    gespeichert = eintrag.get("sha256")
    if not gespeichert:
        return "ohne_prüfsumme"
    protokoll = runs_dir / str(eintrag.get("protokoll", ""))
    if not protokoll.is_file():
        return "fehlt"
    try:
        return "ok" if _sha256(protokoll) == gespeichert else "verändert"
    except OSError:
        return "fehlt"


def zusammenfassung(ergebnis: list[dict]) -> dict[str, int]:
    """Zählt die Stati, z. B. {'ok': 5, 'verändert': 1}."""
    zaehler: dict[str, int] = {}
    for e in ergebnis:
        zaehler[e["status"]] = zaehler.get(e["status"], 0) + 1
    return zaehler
