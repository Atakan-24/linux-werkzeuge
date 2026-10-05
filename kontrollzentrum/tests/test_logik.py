"""Tests für die Logik des Kontrollzentrums: Umfang, Zeitfenster, Beweise, Berichte, Befunde, Stapel, Vorschläge.

Ohne Oberfläche und ohne Werkzeuge. Jeder Test schreibt in einen eigenen Ordner, echte Daten werden nie berührt.
Start: python3 kontrollzentrum/tests/test_logik.py
"""
import hashlib
import json
import os
import pathlib
import sys
import tempfile
from datetime import datetime

ORDNER = pathlib.Path(tempfile.mkdtemp(prefix="kz-test-"))
os.environ["KONTROLLZENTRUM_DATEN"] = str(ORDNER)  # befunde.py legt seine Daten hier ab
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "code"))

import beweise, berichte, befunde, regeln, stapel, umfang  # noqa: E402

ergebnisse = []


def check(name, bedingung):
    ergebnisse.append((name, bool(bedingung)))
    print(("OK   " if bedingung else "FEHL ") + name)


def wirft(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# ---------------------------------------------------------- Umfang
check("Ziel: Rechnername aus Adresse", umfang.ziel_host("https://Shop.Firma.de/x") == "shop.firma.de")
check("Umfang: Standard ist das Ziel selbst", umfang.umfang_fuer_ziel("firma.de") == ["firma.de"])
check("Eintrag: IP, Netz und Domain gültig", all(umfang.ist_gueltiger_eintrag(e) for e in ["10.0.0.1", "192.168.1.0/24", "firma.de"]))
check("Eintrag: Unsinn abgelehnt", not umfang.ist_gueltiger_eintrag("hallo welt"))
check("Umfang: IP im Netz erlaubt", umfang.in_umfang("192.168.1.7", ["192.168.1.0/24"]))
check("Umfang: IP außerhalb gesperrt", not umfang.in_umfang("10.0.0.1", ["192.168.1.0/24"]))
check("Umfang: Domain und Unterdomain erlaubt", umfang.in_umfang("shop.firma.de", ["firma.de"]))
check("Umfang: fremde Domain gesperrt", not umfang.in_umfang("fremd.de", ["firma.de"]))
check("Umfang: Domain bleibt außerhalb eines IP-Netzes", not umfang.in_umfang("firma.de", ["192.168.1.0/24"]))
check("Ablauf: leer heißt unbegrenzt", umfang.gueltig_bis_ok(None))
check("Ablauf: Datum in der Zukunft gilt", umfang.gueltig_bis_ok("2099-01-01"))
check("Ablauf: Datum in der Vergangenheit gilt nicht", not umfang.gueltig_bis_ok("2020-01-01"))

# ---------------------------------------------------------- Zeitfenster
werktage = {"tage": "Mo-Fr", "von": "08:00", "bis": "18:00"}
mo_1000, mo_1800, sa_1000 = datetime(2026, 10, 5, 10, 0), datetime(2026, 10, 5, 18, 0), datetime(2026, 10, 3, 10, 0)
check("Zeitfenster: Eingabe mit Tagen", umfang.parse_zeitfenster("Mo-Fr 08:00-18:00") == werktage)
check("Zeitfenster: leer heißt jederzeit", umfang.parse_zeitfenster("") is None)
check("Zeitfenster: Ende über Mitternacht abgelehnt", wirft(lambda: umfang.parse_zeitfenster("18:00-08:00")))
check("Zeitfenster: Zeichen wie Semikolon abgelehnt", wirft(lambda: umfang.parse_zeitfenster("08:00-18:00; ls")))
check("Zeitfenster: Montag 10:00 erlaubt", umfang.zeitfenster_ok(werktage, mo_1000))
check("Zeitfenster: 18:00 gesperrt (Ende ist ausgeschlossen)", not umfang.zeitfenster_ok(werktage, mo_1800))
check("Zeitfenster: Samstag gesperrt bei Mo-Fr", not umfang.zeitfenster_ok(werktage, sa_1000))
check("Gesamtprüfung: alles passt", umfang.darf_jetzt("firma.de", {"umfang": ["firma.de"], "zeitfenster": werktage}, mo_1000) == (True, "erlaubt"))
check("Gesamtprüfung: keine Erlaubnis sperrt", umfang.darf_jetzt("firma.de", None)[0] is False)
check("Gesamtprüfung: Zeitfenster sperrt mit Grund",
      "Zeitfenster" in umfang.darf_jetzt("firma.de", {"zeitfenster": werktage}, sa_1000)[1])

# ---------------------------------------------------------- Stapel
freigaben = {"firma.de": {"wer": "Test", "umfang": ["firma.de"], "gueltig_bis": None, "zeitfenster": None}}
plan = stapel.plan(["firma.de", "fremd.de"], freigaben, jetzt=mo_1000)
check("Stapel: Ziel mit Erlaubnis ist ok", plan[0]["ok"] is True)
check("Stapel: Ziel ohne Erlaubnis ist gesperrt", plan[1]["ok"] is False and "Keine Erlaubnis" in plan[1]["grund"])
check("Stapel: nur freigegebene Ziele kommen in die Reihe", stapel.freigegebene(plan) == ["firma.de"])

# ---------------------------------------------------------- Beweise
log = ORDNER / "lauf-1.log"
log.write_text("Ausgabe eins\n", encoding="utf-8")
beweis_datei = ORDNER / "beweise.jsonl"
beweis_datei.write_text(json.dumps({"lauf": "lauf-1", "befehl": "beispiel", "rueckgabe": 0, "protokoll": "lauf-1.log",
                                    "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}) + "\n", encoding="utf-8")
check("Beweise: unveränderter Lauf ist ok", beweise.pruefe(beweis_datei, ORDNER)[0]["status"] == "ok")
log.write_text("Ausgabe zwei, nachträglich geändert\n", encoding="utf-8")
check("Beweise: nachträgliche Änderung wird erkannt", beweise.pruefe(beweis_datei, ORDNER)[0]["status"] == "verändert")
log.unlink()
check("Beweise: fehlendes Protokoll wird gemeldet", beweise.pruefe(beweis_datei, ORDNER)[0]["status"] == "fehlt")

# ---------------------------------------------------------- Befunde und Verlauf
datei = ORDNER / "befunde.json"
ordner = ORDNER / "staende"
befunde.verarbeite("nikto", "firma.de", "+ Der Server ist veraltet (outdated)\n+ Normale Zeile\n",
                   zeit="2026-10-01 10:00", datei=datei)
befunde.stand_speichern("firma.de", zeit="20261001-100000", ordner=ordner, datei=datei)
befunde.verarbeite("nikto", "firma.de", "+ Normale Zeile\n", zeit="2026-10-02 10:00", datei=datei)
befunde.stand_speichern("firma.de", zeit="20261002-100000", ordner=ordner, datei=datei)
reihe = befunde.verlauf("firma.de", ordner)
check("Verlauf: zwei Stände in Reihenfolge", [z["stand"] for z in reihe] == ["20261001-100000", "20261002-100000"])
check("Verlauf: Zähler je Schwere", reihe[0]["zaehler"]["low"] == 1 and reihe[1]["gesamt"] == 1)
check("Befunde: behobener Fund wird nicht mehr als offen gezählt",
      len(befunde.fuer_ziel("firma.de", datei=datei, nur_offen=True)) == 1)

# ---------------------------------------------------------- Berichte
funde = [{"fp": "aaa111", "ziel": "firma.de", "werkzeug": "nikto", "titel": "Header fehlt <b>",
          "schwere": "critical", "detail": "x", "erstmals": "2026-10-01 10:00", "zuletzt": "2026-10-01 10:00"},
         {"fp": "bbb222", "ziel": "firma.de", "werkzeug": "sslscan", "titel": "Alt", "schwere": "low", "detail": "",
          "erstmals": "2026-10-01 10:00", "zuletzt": "2026-10-01 10:00"}]
sarif = json.loads(berichte.als_sarif("firma.de", funde, "2026-10-05 10:00"))
check("SARIF: Version 2.1.0", sarif["version"] == "2.1.0")
check("SARIF: critical wird error, low wird note",
      [r["level"] for r in sarif["runs"][0]["results"]] == ["error", "note"])
freigabe_md = {"wer": "Test", "datum": "2026-10-01", "umfang": ["firma.de"], "gueltig_bis": None, "zeitfenster": werktage}
check("Bericht: erlaubte Zeit steht drin",
      "Erlaubte Zeit: Mo–Fr 08:00–18:00 Uhr" in berichte.als_markdown("firma.de", [], [], "2026-10-05", freigabe_md))
check("Bericht: HTML maskiert Eingaben",
      "<b>" not in berichte.als_html("firma.de", funde, [], "2026-10-05").split("<table>")[1])
check("CSV: Kopfzeile vorhanden", berichte.als_csv(funde).startswith("schwere,titel"))

# ---------------------------------------------------------- Vorschläge
webfunde = [{"titel": "Offene Tür 443/tcp (https)", "schwere": "info", "detail": ""}]
vorschl = regeln.vorschlaege(webfunde)
check("Vorschlag: Webdienst führt zu whatweb", any(v["schritt"] == "whatweb" for v in vorschl))
verboten = {"hydra", "crack", "metasploit", "hashcat", "john", "msfvenom"}
check("Vorschläge: keine Angriffswerkzeuge", not any(v["schritt"] in verboten for v in vorschl))

gut = sum(1 for _, o in ergebnisse if o)
print(f"\n{gut} von {len(ergebnisse)} Prüfungen bestanden")
if gut != len(ergebnisse):
    print("FEHLER:", [n for n, o in ergebnisse if not o])
    sys.exit(1)
print("LOGIK_OK")
