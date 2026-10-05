"""Vorschläge aus den Funden: welcher Schritt als Nächstes sinnvoll ist, und warum.

Jede Regel ist einfach und nachlesbar. Es gibt keine Angriffs-Vorschläge: Empfohlen wird nur,
was man zum Prüfen und Schließen von Lücken braucht.
"""

import re

WEB_PORTS = {80, 443, 8080, 8443}
SMB_PORTS = {139, 445}


def _ports(funde: list[dict]) -> set[int]:
    ports = set()
    for f in funde:
        m = re.match(r"Offene Tür (\d+)/", f["titel"])
        if m:
            ports.add(int(m.group(1)))
    return ports


def _webports(funde: list[dict]) -> list[int]:
    """Ports, auf denen ein Webdienst läuft: bekannte Web-Ports oder ein Dienst mit „http“ im Namen."""
    treffer = []
    for f in funde:
        m = re.match(r"Offene Tür (\d+)/\w+ \(([^)]*)\)", f["titel"])
        if m and (int(m.group(1)) in WEB_PORTS or "http" in m.group(2).lower()):
            treffer.append(int(m.group(1)))
    return sorted(set(treffer))


def vorschlaege(funde: list[dict]) -> list[dict]:
    """Gibt Vorschläge zurück: {schritt (oder None für einen Hinweis), weil}."""
    ports = _ports(funde)
    ergebnis: list[dict] = []

    def hinzu(schritt, weil):
        if not any(v["schritt"] == schritt and v["weil"] == weil for v in ergebnis):
            ergebnis.append({"schritt": schritt, "weil": weil})

    webports = _webports(funde)
    if webports:
        hinzu("whatweb", f"Ein Webdienst ist erreichbar (Tür {webports[0]}). Zuerst prüfen, welche Software läuft.")
    if any("WordPress" in f["titel"] for f in funde):
        hinzu("wpscan", "WordPress wurde erkannt. Erweiterungen und Einstellungen prüfen.")
    if ports & SMB_PORTS:
        hinzu("enum4linux", "Windows-Freigaben (SMB) sind erreichbar. Prüfen, welche ohne Anmeldung offen sind.")
    if 3389 in ports:
        hinzu(None, "Der Fernzugriff RDP ist erreichbar. Prüfen, ob das so gewollt ist.")
    if 22 in ports:
        hinzu(None, "SSH ist erreichbar. Prüfen: nur Schlüssel-Anmeldung erlaubt, Sperre nach Fehlversuchen aktiv. "
                    "Kein Passwort-Test gegen SSH, das sperrt schnell den eigenen Zugang.")
    if any(f["schwere"] in ("high", "critical") for f in funde):
        hinzu(None, "Es gibt einen kritischen Fund. Den Verantwortlichen sofort informieren.")
    if not ports and not funde:
        hinzu(None, "Keine offenen Türen gefunden. Webprüfungen bringen hier nichts, wenn kein Webdienst läuft.")
    return ergebnis
