# Einen lokalen Dienst absichern

Ein lokaler API-Server (HTTP, Port 8888, nur auf `127.0.0.1` erreichbar) führte Werkzeuge aus, bekam Befehle als Text und
hatte **keine Anmeldung**. Dieser Ordner beschreibt, wie ich ihn abgesichert habe. Der Code des fremden Servers ist nicht enthalten.

## Das Problem

1. **Keine Anmeldung.** Jeder Prozess auf dem Rechner konnte die Schnittstelle nutzen.
2. **Ein Befehlszugang für alles.** Ein Endpunkt führte jeden übergebenen Text als Shell-Befehl aus.
3. **Eingaben in Befehlstexte.** Ziel und Zusatzargumente wurden direkt in einen Befehlstext gesetzt, der dann von der Shell ausgeführt wurde.

Punkt 3 ist eine typische **Befehlseinschleusung**: Ein Eingabewert enthält Zeichen wie `;` oder `|`, und die Shell führt danach
einen zweiten, ungewollten Befehl aus.

## Die Lösung

| Maßnahme | Umsetzung |
|---|---|
| **Token-Anmeldung** | Beim ersten Start wird ein zufälliger Schlüssel erzeugt und mit Rechten `600` nur für den Benutzer gespeichert. Jede Anfrage braucht den Schlüssel im Kopf `Authorization`. |
| **Vergleich in fester Zeit** | Der Schlüssel wird mit `hmac.compare_digest` verglichen, damit die Antwortzeit nichts über den Schlüssel verrät. |
| **Befehlszugang gesperrt** | Der offene Endpunkt für beliebige Befehle antwortet mit `403`. |
| **Eingabeprüfung** | Vor jeder Anfrage: Zeichen wie `; \| & \` $ ( ) < > " '` und Zeilenumbrüche werden abgelehnt (`400`). Ziele müssen wie eine Adresse aussehen. |
| **Nur der Gesundheitscheck ist offen** | `/health` braucht keinen Schlüssel, alles andere schon. |

## Tests und Ergebnisse

| Prüfung | Erwartet | Ergebnis |
|---|---|---|
| Werkzeug-Aufruf ohne Schlüssel | 401 | 401 |
| Befehlszugang mit Schlüssel | 403 | 403 |
| Ziel mit `; touch …` | 400, keine Datei entsteht | 400, keine Datei |
| Zusatzargument mit `$(…)` | 400, keine Datei entsteht | 400, keine Datei |
| Normaler Lauf mit Schlüssel | Ergebnis | Ergebnis mit Rückgabewert 0 |

## Was man daraus lernt

- **Eingaben nie als Text in Befehle setzen.** Richtig ist, Argumente als Liste zu übergeben (in Python `subprocess` ohne `shell=True`).
- **Sperrlisten sind nur eine Notlösung.** Sie blockieren bekannte Zeichen, aber nicht alles. Die saubere Lösung ist die Übergabe als Liste.
- **Lokal heißt nicht sicher.** Jeder Prozess des Benutzers und jedes Programm mit Zugriff auf den Port konnte den Befehlszugang nutzen.
- **Tests mit Angriffsversuchen** zeigen, ob die Absicherung wirkt. Ein blockierter Versuch, bei dem keine Datei entsteht, ist der Beweis.

## Offen

- Die Eingabeprüfung ist eine Sperrliste. Der nächste Schritt wäre, alle Werte mit `shlex.quote` oder als Liste zu übergeben.
- Die Freigabe-Prüfung liegt im Kontrollzentrum, nicht im Server. Wer den Schlüssel hat, kann den Server direkt nutzen. Der Schlüssel ist deshalb geheim zu halten.
