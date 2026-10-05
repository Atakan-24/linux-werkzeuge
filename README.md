# Linux-Werkzeuge und Konfigurationen

Eigene Werkzeuge und Einstellungen für einen Linux-Arbeitsplatz (Kali Linux mit XFCE).
Alles in Bash und Python, mit Tests und Dokumentation. Jeder Teil ist für sich verständlich.

## Inhalt

| Ordner | Was drin steckt | Linux-Themen |
|---|---|---|
| [`desktop-setup/`](desktop-setup/) | Desktop anpassen: Farben, Tastenkürzel, Screenshots, Terminal-Oberfläche | GTK, XFCE-Einstellungen (xfconf), Python mit GObject, Konfigurations-Backups mit Rückweg |
| [`energie-sperre/`](energie-sperre/) | Automatisch in Energiesparmodus, sicheres Sperren, Deckel-Verhalten | systemd, logind, Energieverwaltung, Shell-Hooks |
| [`kontrollzentrum-architektur/`](kontrollzentrum-architektur/) | Beschreibung eines Werkzeugs für Sicherheitsprüfungen, mit Bildern ([English](kontrollzentrum-architektur/README.en.md)) | Python/Tkinter, Threads und Warteschlangen, Tests mit virtuellem Bildschirm, Freigabe-Logik |
| [`kontrollzentrum/`](kontrollzentrum/) | Logik eines Kontrollzentrums für Sicherheitsprüfungen: Umfang, Zeitfenster, Freigabe-Stapel, Beweisprüfung, Berichte (SARIF) | Python, Datenstrukturen, Prüfsummen, Tests ohne Oberfläche |
| [`dienst-absicherung/`](dienst-absicherung/) | Wie ein lokaler Dienst gegen Befehlseinschleusung abgesichert wurde | Token-Anmeldung, Eingabeprüfung, Shell-Befehle und ihre Gefahren, Tests mit Angriffsversuchen |
| [`bilder/`](bilder/) | Screenshots der Oberflächen | |

## Prüfung

Bei jeder Änderung prüft GitHub Actions die Skripte: `shellcheck` für die Bash-Dateien, Syntaxprüfung für die Python-Dateien
und die Tests der Kontrollzentrum-Logik laufen durch (Datei [`.github/workflows/pruefen.yml`](.github/workflows/pruefen.yml)).

## Hinweis

- Die Skripte sind auf einen bestimmten Rechner zugeschnitten (Benutzername, Pfade, XFCE). Sie sind **Beispiele und Nachweis meiner Arbeit**. Auf einem anderen Rechner sind sie eine Vorlage, kein fertiges Paket.
- Benutzername und Pfade stehen als `DEIN_BENUTZER` und `/home/DEIN_BENUTZER` im Code. Vor der Benutzung ersetzen.
- Werkzeuge für Sicherheitsprüfungen nur auf eigenen Systemen oder mit schriftlicher Erlaubnis einsetzen.
- Die Angriffs-Werkzeuge selbst sind nicht Teil dieses Repositorys. Beschrieben ist nur, wie das Kontrollzentrum aufgebaut ist.
