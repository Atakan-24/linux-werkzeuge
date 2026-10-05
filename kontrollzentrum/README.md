# Kontrollzentrum: Logik-Teil

Dieser Ordner enthält die **Logik** eines Kontrollzentrums für Sicherheitsprüfungen: die Regeln, die
bestimmen, was geprüft werden darf, und wie Ergebnisse festgehalten und ausgegeben werden.

Die Beschreibung des ganzen Programms steht in [`kontrollzentrum-architektur/`](../kontrollzentrum-architektur/README.md).

## Was drin ist

| Datei | Was sie tut |
|---|---|
| `code/umfang.py` | Prüft, ob ein Ziel im erlaubten Umfang liegt (IP, Netz, Domain), ob die Freigabe noch gilt und ob die Uhrzeit passt (Zeitfenster). |
| `code/stapel.py` | Plant eine Prüfung für mehrere Ziele. Nur Ziele mit gültiger Freigabe kommen in die Reihe. |
| `code/beweise.py` | Prüft, ob die gespeicherte Rohausgabe eines Laufs noch mit ihrer SHA-256-Prüfsumme übereinstimmt. |
| `code/befunde.py` | Wandelt die Ausgabe von Prüfwerkzeugen in Funde um, führt gleiche Funde zusammen und speichert den Verlauf. |
| `code/berichte.py` | Schreibt Berichte als Markdown, JSON, CSV, HTML und SARIF 2.1.0 (das Austauschformat für Sicherheitsbefunde). |
| `code/regeln.py` | Schlägt aus den Funden die nächsten Prüfschritte vor, jeweils mit Begründung. |
| `tests/test_logik.py` | 38 Prüfungen dieser Logik. Ohne Oberfläche, ohne Werkzeuge, ohne echte Daten. |

## Die Grundregeln im Code

- **Freigabe vor jeder Prüfung.** Ohne eingetragene Freigabe wird nichts geprüft. Das gilt vor jedem einzelnen Schritt.
- **Umfang.** Ein Ziel außerhalb der Freigabe wird abgelehnt, auch wenn es in einer Liste steht.
- **Zeitfenster.** Eine Freigabe kann Uhrzeiten festlegen, z. B. `Mo-Fr 08:00-18:00`. Außerhalb davon startet nichts. Das Ende ist ausgeschlossen.
- **Ablauf.** Eine Freigabe kann ein Ablaufdatum haben. Danach gilt sie nicht mehr.
- **Nachweis.** Jeder Lauf bekommt eine Prüfsumme. Nachträgliche Änderungen fallen auf.

## Was bewusst nicht drin ist

Die Teile, die Werkzeuge tatsächlich starten, sind nicht Teil dieses Ordners. Dazu gehören die Oberfläche,
die Lauf-Steuerung und die Anbindung an die einzelnen Werkzeuge. Auch Angriffswerkzeuge wie Passwort-Knacker
oder Exploit-Starter fehlen hier vollständig. Die Logik oben ist, was man zum sicheren Planen und Festhalten braucht.

## Ausführen

```bash
python3 kontrollzentrum/tests/test_logik.py
```

Die Prüfung braucht nur Python 3. Sie legt ihre Daten in einen eigenen Ordner und verändert nichts anderes.

## Hinweis

Die Freigabe ist eine Entscheidung des Programms, nicht des Ziels. Wer den Code ändert, kann die Prüfung umgehen.
Deshalb gehört die schriftliche Erlaubnis immer auch außerhalb des Programms festgehalten.
