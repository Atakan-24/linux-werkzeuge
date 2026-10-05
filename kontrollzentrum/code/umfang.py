"""Umfang einer Freigabe: welche Ziele darf man prüfen, und bis wann.

Ein Umfang ist eine Liste aus IP-Adressen, Netzen (z. B. 192.168.1.0/24) und Domains.
Eine Domain „firma.de“ erfasst auch alle Unterdomains wie „shop.firma.de“.
Ziele außerhalb des Umfangs werden vor jedem Start abgelehnt.
"""

import ipaddress
import re
from datetime import date, datetime
from urllib.parse import urlsplit

_DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9-]+\.)+[a-z]{2,}$")


def ziel_host(ziel: str) -> str:
    """Nur der Rechnername oder die IP: „https://shop.firma.de/x“ wird zu „shop.firma.de“."""
    text = (ziel or "").strip()
    if "://" in text:
        host = urlsplit(text).hostname or ""
    else:
        host = text.split("/")[0].split(":")[0]
    return host.lower().rstrip(".")


def umfang_fuer_ziel(ziel: str) -> list[str]:
    """Der Standard-Umfang, wenn man nichts extra einträgt: nur das Ziel selbst."""
    host = ziel_host(ziel)
    return [host] if host else []


def ist_gueltiger_eintrag(eintrag: str) -> bool:
    e = eintrag.strip().lower()
    if not e:
        return False
    try:
        ipaddress.ip_network(e, strict=False)
        return True
    except ValueError:
        pass
    return bool(_DOMAIN.match(e.removeprefix("*.")))


def in_umfang(ziel: str, umfang: list[str]) -> bool:
    host = ziel_host(ziel)
    if not host or not umfang:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    for eintrag in umfang:
        e = eintrag.strip().lower()
        if not e:
            continue
        try:
            netz = ipaddress.ip_network(e, strict=False)
            if ip is not None and ip in netz:
                return True
            continue
        except ValueError:
            pass
        if ip is None:  # Domain: die Domain selbst und alle Unterdomains
            basis = e.removeprefix("*.")
            if host == basis or host.endswith("." + basis):
                return True
    return False


def gueltig_bis_ok(gueltig_bis: str | None, heute: date | None = None) -> bool:
    """Leer heißt unbegrenzt. Sonst muss das Datum im Format JJJJ-MM-TT heute oder später sein."""
    if not gueltig_bis:
        return True
    try:
        ende = date.fromisoformat(gueltig_bis)
    except ValueError:
        return False
    return (heute or date.today()) <= ende


def datum_lesbar(text: str) -> bool:
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False


# ------------------------------------------------------------ Zeitfenster
# Erlaubte Uhrzeiten einer Prüfung, z. B. „Mo-Fr 08:00-18:00“. Nur das Programm selbst achtet darauf, nicht
# die Sicherheit des Ziels: Es verhindert Prüfungen außerhalb der vereinbarten Zeit (Versehen, Schichtplanung).
_ZEITFENSTER = re.compile(r"(?:(Mo-Fr|Mo-So)\s+)?([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)")


def parse_zeitfenster(text: str | None) -> dict | None:
    """Leer heißt jederzeit. Sonst {'tage', 'von', 'bis'}. Wirft ValueError mit Klartext, wenn es nicht passt."""
    roh = (text or "").strip()
    if not roh:
        return None
    m = _ZEITFENSTER.fullmatch(roh)
    if not m:
        raise ValueError("Bitte so eingeben: 08:00-18:00 oder Mo-Fr 08:00-18:00.")
    von, bis = f"{m.group(2)}:{m.group(3)}", f"{m.group(4)}:{m.group(5)}"
    if von >= bis:
        raise ValueError("Die Startzeit muss vor der Endzeit liegen. Über Mitternacht geht es nicht.")
    return {"tage": m.group(1) or "Mo-So", "von": von, "bis": bis}


def zeitfenster_text(zeitfenster: dict | None) -> str:
    if not zeitfenster:
        return "jederzeit"
    tage = "Mo–Fr" if zeitfenster.get("tage") == "Mo-Fr" else "täglich"
    return f"{tage} {zeitfenster['von']}–{zeitfenster['bis']} Uhr"


def zeitfenster_ok(zeitfenster: dict | None, jetzt: datetime | None = None) -> bool:
    """Ende ist ausgeschlossen: „bis 18:00“ heißt, um 18:00 ist es schon zu spät."""
    if not zeitfenster:
        return True
    jetzt = jetzt or datetime.now()
    if zeitfenster.get("tage") == "Mo-Fr" and jetzt.weekday() >= 5:
        return False
    return zeitfenster["von"] <= jetzt.strftime("%H:%M") < zeitfenster["bis"]


def darf_jetzt(ziel: str, freigabe: dict | None, jetzt: datetime | None = None) -> tuple[bool, str]:
    """Die Gesamtprüfung vor jedem Start: Erlaubnis da, gültig, Ziel im Umfang, Zeitfenster. Gibt (ok, Grund)."""
    if not freigabe:
        return False, "Keine Erlaubnis eingetragen"
    if not gueltig_bis_ok(freigabe.get("gueltig_bis")):
        return False, "Erlaubnis ist abgelaufen"
    if not in_umfang(ziel, freigabe.get("umfang") or umfang_fuer_ziel(ziel)):
        return False, "Liegt nicht im erlaubten Umfang"
    if not zeitfenster_ok(freigabe.get("zeitfenster"), jetzt):
        return False, f"Außerhalb des erlaubten Zeitfensters ({zeitfenster_text(freigabe.get('zeitfenster'))})"
    return True, "erlaubt"
