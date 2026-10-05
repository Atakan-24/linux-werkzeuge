"""Befunde: die Ausgabe der Werkzeuge in strukturierte Funde umwandeln und speichern.

Ein Fund hat: Ziel, Werkzeug, Titel, Schweregrad (info, low, medium, high, critical), Detail und Zeitpunkte.
Gleiche Funde aus mehreren Läufen werden zusammengeführt (über einen Fingerabdruck aus Ziel, Werkzeug und Titel).
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path

DATEN_DIR = Path(os.environ.get("KONTROLLZENTRUM_DATEN") or Path(__file__).resolve().parent)
BEFUNDE_DATEI = DATEN_DIR / "befunde.json"

SCHWEREN = ["info", "low", "medium", "high", "critical"]


def fingerabdruck(ziel: str, werkzeug: str, titel: str) -> str:
    return hashlib.sha1(f"{ziel}|{werkzeug}|{titel}".encode("utf-8")).hexdigest()[:12]


def _nmap(text: str) -> list[dict]:
    funde = []
    for port, proto, dienst in re.findall(r"^(\d+)/(tcp|udp)\s+open\s+(\S+)", text, re.MULTILINE):
        funde.append({"titel": f"Offene Tür {port}/{proto} ({dienst})", "schwere": "info",
                      "detail": "Der Dienst antwortet aus dem Netz."})
    return funde


def _nikto(text: str) -> list[dict]:
    funde = []
    for zeile in text.splitlines():
        if zeile.startswith("+ "):
            titel = zeile[2:].strip()[:160]
            schwere = "low" if re.search(r"outdated|veraltet|vulnerab|header", titel, re.I) else "info"
            funde.append({"titel": titel, "schwere": schwere, "detail": ""})
    return funde


def _nuclei(text: str) -> list[dict]:
    funde = []
    for zeile in text.splitlines():
        m = re.match(r"^\[([^\]]+)\]\s+\[[^\]]+\]\s+\[(\w+)\]\s+(\S+)", zeile.strip())
        if m and m.group(2) in SCHWEREN:
            funde.append({"titel": f"Bekannte Lücke: {m.group(1)}", "schwere": m.group(2), "detail": m.group(3)})
    return funde


def _whatweb(text: str) -> list[dict]:
    funde = []
    for name, version in re.findall(r"([A-Za-z][\w-]+)\[([^\]]*)\]", text):
        if name in ("IP", "Country", "Title", "MetaGenerator", "HTML5"):
            continue
        titel = f"Software erkannt: {name}"
        funde.append({"titel": titel, "schwere": "info", "detail": f"Version {version}" if version else ""})
    return funde


def _sslscan(text: str) -> list[dict]:
    """Veraltete Verschlüsselungsprotokolle, die der Server noch annimmt."""
    gefunden = set()
    for m in re.finditer(r"(SSLv2|SSLv3|TLSv1\.0|TLSv1\.1)\s+(enabled|disabled)", text):
        if m.group(2) == "enabled":
            gefunden.add(m.group(1))
    for m in re.finditer(r"Accepted\s+(SSLv2|SSLv3|TLSv1\.0|TLSv1\.1)\b", text):
        gefunden.add(m.group(1))
    funde = []
    for protokoll in sorted(gefunden):
        schwere = "high" if protokoll in ("SSLv2", "SSLv3") else "medium"
        funde.append({"titel": f"Veraltetes Protokoll aktiv: {protokoll}", "schwere": schwere,
                      "detail": "Der Server nimmt eine veraltete Verschlüsselung an. Abschalten."})
    return funde


PARSER = {"nmap": _nmap, "nikto": _nikto, "nuclei": _nuclei, "whatweb": _whatweb, "sslscan": _sslscan}


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")  # Farbcodes, die manche Werkzeuge in die Ausgabe schreiben


def befunde_aus_text(werkzeug: str, text: str) -> list[dict]:
    parser = PARSER.get(werkzeug)
    if not parser:
        return []
    return parser(ANSI.sub("", text))


# ------------------------------------------------------------ Speicher
def laden(datei: Path | None = None) -> dict:
    """Alle Befunde: {ziel: {fingerabdruck: fund}}."""
    try:
        return json.loads(Path(datei or BEFUNDE_DATEI).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _speichern(daten: dict, datei: Path | None = None) -> None:
    try:
        Path(datei or BEFUNDE_DATEI).write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def verarbeite(werkzeug: str, ziel: str, text: str, zeit: str | None = None, datei: Path | None = None) -> dict:
    """Nimmt die Ausgabe eines Laufs auf.

    Ein Fund, den das Werkzeug in diesem Lauf nicht mehr meldet, wird „nicht mehr gesehen“ (z. B. nach einer Reparatur).
    Gibt {'neu': n, 'bekannt': m, 'nicht_mehr_gesehen': k} zurück.
    """
    zeit = zeit or time.strftime("%Y-%m-%d %H:%M")
    daten = laden(datei)
    bestand = daten.setdefault(ziel, {})
    neu = bekannt = 0
    gesehen = set()
    for fund in befunde_aus_text(werkzeug, text):
        fp = fingerabdruck(ziel, werkzeug, fund["titel"])
        gesehen.add(fp)
        if fp in bestand:
            bestand[fp]["zuletzt"] = zeit
            bestand[fp]["status"] = "offen"
            bekannt += 1
        else:
            bestand[fp] = {"fp": fp, "ziel": ziel, "werkzeug": werkzeug, "titel": fund["titel"],
                           "schwere": fund["schwere"], "detail": fund["detail"],
                           "erstmals": zeit, "zuletzt": zeit, "status": "offen"}
            neu += 1
    weg = 0
    for fp, f in bestand.items():
        if f["werkzeug"] == werkzeug and fp not in gesehen and f.get("status", "offen") == "offen":
            f["status"] = "nicht_mehr_gesehen"
            f["nicht_mehr_seit"] = zeit
            weg += 1
    _speichern(daten, datei)
    return {"neu": neu, "bekannt": bekannt, "nicht_mehr_gesehen": weg}


def fuer_ziel(ziel: str, datei: Path | None = None, nur_offen: bool = False) -> list[dict]:
    """Funde eines Ziels, nach Schwere sortiert (kritisch zuerst). Mit nur_offen nur die aktuell vorhandenen."""
    funde = list(laden(datei).get(ziel, {}).values())
    if nur_offen:
        funde = [f for f in funde if f.get("status", "offen") == "offen"]
    return sorted(funde, key=lambda f: (-SCHWEREN.index(f["schwere"]), f["titel"]))


def vergleich(alt: list[dict], neu: list[dict]) -> dict:
    """Vergleicht zwei Stände: was ist neu, was wurde behoben, was bleibt."""
    a = {f["fp"]: f for f in alt}
    n = {f["fp"]: f for f in neu}
    return {
        "neu": [n[k] for k in n if k not in a],
        "behoben": [a[k] for k in a if k not in n],
        "bleibt": [n[k] for k in n if k in a],
    }


# ------------------------------------------------------------ Momentaufnahmen
STAENDE_DIR = DATEN_DIR / "staende"


def stand_speichern(ziel: str, zeit: str | None = None, ordner: Path | None = None,
                    datei: Path | None = None) -> Path:
    """Speichert den aktuellen Befundstand eines Ziels, damit man später vergleichen kann."""
    zeit = zeit or time.strftime("%Y%m%d-%H%M%S")
    ziel_ordner = (ordner or STAENDE_DIR) / "".join(c if c.isalnum() or c in "-." else "_" for c in ziel)
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    pfad = ziel_ordner / f"{zeit}.json"
    pfad.write_text(json.dumps(fuer_ziel(ziel, datei, nur_offen=True), ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad


def staende(ziel: str, ordner: Path | None = None) -> list[Path]:
    """Alle gespeicherten Stände eines Ziels, älteste zuerst."""
    ziel_ordner = (ordner or STAENDE_DIR) / "".join(c if c.isalnum() or c in "-." else "_" for c in ziel)
    return sorted(ziel_ordner.glob("*.json")) if ziel_ordner.is_dir() else []


def stand_laden(pfad: Path) -> list[dict]:
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def verlauf(ziel: str, ordner: Path | None = None) -> list[dict]:
    """Zeitreihe: je gespeichertem Stand die Anzahl offener Funde je Schwere, älteste zuerst.

    Gibt [{'stand': 'YYYYmmdd-HHMMSS', 'zaehler': {'critical': 0, ..., 'info': 2}, 'gesamt': n}, ...].
    """
    reihe = []
    for pfad in staende(ziel, ordner):
        funde = stand_laden(pfad)
        zaehler = {s: 0 for s in reversed(SCHWEREN)}
        for f in funde:
            if f.get("schwere") in zaehler:
                zaehler[f["schwere"]] += 1
        reihe.append({"stand": pfad.stem, "zaehler": zaehler, "gesamt": len(funde)})
    return reihe
