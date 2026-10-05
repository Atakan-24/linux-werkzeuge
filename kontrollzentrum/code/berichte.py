"""Berichte in mehreren Formaten: Markdown, JSON, CSV und HTML."""

import csv
import html
import io
import json

from umfang import zeitfenster_text

FORMATE = ["markdown", "json", "csv", "html", "sarif"]
ENDUNG = {"markdown": "md", "json": "json", "csv": "csv", "html": "html", "sarif": "sarif"}

# SARIF 2.1.0: der Standard, mit dem Sicherheitsbefunde zwischen Werkzeugen ausgetauscht werden
# (z. B. von GitHub, VS Code oder Auswertungsprogrammen gelesen).
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}
# Zahl 0–10 nach CVSS-Art, damit Auswertungen nach Dringlichkeit sortieren können
SARIF_SICHERHEIT = {"critical": "9.5", "high": "7.5", "medium": "5.0", "low": "3.0", "info": "0.0"}


def als_markdown(ziel: str, funde: list[dict], vorschl: list[dict], erstellt: str, freigabe: dict | None) -> str:
    zeilen = [f"# Prüfbericht: {ziel}", "", f"Erstellt: {erstellt}", "", "## Freigabe"]
    if freigabe:
        zeilen += [f"- Freigegeben von: {freigabe.get('wer', '–')}",
                   f"- Datum: {freigabe.get('datum', '–')}",
                   f"- Umfang: {', '.join(freigabe.get('umfang') or [ziel])}",
                   f"- Gültig bis: {freigabe.get('gueltig_bis') or 'unbegrenzt'}",
                   f"- Erlaubte Zeit: {zeitfenster_text(freigabe.get('zeitfenster'))}"]
    else:
        zeilen += ["- **Keine Freigabe eingetragen.** Dieser Bericht ist nicht belegt."]
    zeilen += ["", "## Funde", ""]
    if not funde:
        zeilen += ["Keine Funde."]
    for f in funde:
        zeilen += [f"- **[{f['schwere']}]** {f['titel']} (von {f['werkzeug']}, zuerst {f['erstmals']})"]
        if f.get("detail"):
            zeilen += [f"  - {f['detail']}"]
    zeilen += ["", "## Empfehlungen", ""]
    zeilen += [f"- {v['weil']}" for v in vorschl] or ["Keine Empfehlungen."]
    return "\n".join(zeilen) + "\n"


def als_json(ziel: str, funde: list[dict], vorschl: list[dict], erstellt: str) -> str:
    return json.dumps({"ziel": ziel, "erstellt": erstellt, "funde": funde, "empfehlungen": vorschl},
                      ensure_ascii=False, indent=2)


def als_csv(funde: list[dict]) -> str:
    puffer = io.StringIO()
    schreiber = csv.writer(puffer)
    schreiber.writerow(["schwere", "titel", "werkzeug", "ziel", "erstmals", "zuletzt", "detail"])
    for f in funde:
        schreiber.writerow([f["schwere"], f["titel"], f["werkzeug"], f["ziel"], f["erstmals"], f["zuletzt"], f.get("detail", "")])
    return puffer.getvalue()


def als_sarif(ziel: str, funde: list[dict], erstellt: str, version: str = "1.0") -> str:
    """Jeder Fund ist ein Ergebnis mit Regel, Dringlichkeit und einem stabilen Fingerabdruck."""
    regeln, ergebnisse = [], []
    for f in funde:
        regel_id = f"KZ-{f['fp']}"
        regeln.append({
            "id": regel_id,
            "name": f["titel"][:80],
            "shortDescription": {"text": f["titel"]},
            "properties": {"tags": ["sicherheit", f["werkzeug"]], "security-severity": SARIF_SICHERHEIT[f["schwere"]]},
        })
        meldung = f["titel"] + (f" – {f['detail']}" if f.get("detail") else "")
        ergebnisse.append({
            "ruleId": regel_id,
            "level": SARIF_LEVEL[f["schwere"]],
            "message": {"text": meldung},
            "locations": [{"logicalLocations": [{"name": ziel, "kind": "namespace"}]}],
            "partialFingerprints": {"kontrollzentrum/v1": f["fp"]},
            "properties": {"schwere": f["schwere"], "werkzeug": f["werkzeug"], "erstmals": f["erstmals"],
                           "zuletzt": f["zuletzt"], "status": f.get("status", "offen")},
        })
    bericht = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "Kontrollzentrum", "version": version, "rules": regeln}},
            "results": ergebnisse,
            "properties": {"ziel": ziel, "erstellt": erstellt},
        }],
    }
    return json.dumps(bericht, ensure_ascii=False, indent=2) + "\n"


def als_html(ziel: str, funde: list[dict], vorschl: list[dict], erstellt: str) -> str:
    e = html.escape
    zeilen = "".join(
        f"<tr><td>{e(f['schwere'])}</td><td>{e(f['titel'])}</td><td>{e(f['werkzeug'])}</td>"
        f"<td>{e(f.get('detail', ''))}</td></tr>" for f in funde) or "<tr><td colspan=4>Keine Funde.</td></tr>"
    empf = "".join(f"<li>{e(v['weil'])}</li>" for v in vorschl) or "<li>Keine Empfehlungen.</li>"
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><title>Prüfbericht {e(ziel)}</title>
<style>body{{font-family:sans-serif;margin:2em;color:#222}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee}}</style></head>
<body><h1>Prüfbericht: {e(ziel)}</h1><p>Erstellt: {e(erstellt)}</p>
<h2>Funde</h2><table><tr><th>Schwere</th><th>Titel</th><th>Werkzeug</th><th>Detail</th></tr>{zeilen}</table>
<h2>Empfehlungen</h2><ul>{empf}</ul></body></html>
"""
