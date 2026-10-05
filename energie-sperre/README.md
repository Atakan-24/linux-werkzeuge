# Energie und Sperre

Zwei Werkzeuge, die den Rechner sicher in den Energiesparmodus bringen und den Bildschirm schützen.

## claude-power

Schaltet den Rechner in den Energiesparmodus, sobald alle Sitzungen einer Entwicklungsumgebung (Claude Code) fertig sind. Außerdem:

- **Deckel zu:** Nach einer einstellbaren Wartezeit ohne Arbeit geht der Rechner in den Ruhezustand.
- **Leerlauf:** Nach einer Zeit ohne Tastatur- oder Mauseingabe wird der Rechner in Bereitschaft versetzt.
- **Modi:** `suspend` (Bereitschaft), `hibernate` (Ruhezustand), `shutdown` (Herunterfahren).

Befehle:

```text
claude-power status          # Modus und aktive Sitzungen anzeigen
claude-power suspend         # nach Fertigstellung in den Energiesparmodus
claude-power cancel          # laufenden Countdown abbrechen
claude-power lid 30          # Deckel zu + 30 Minuten ohne Arbeit -> Ruhezustand
claude-power idle ac 45      # am Netz: nach 45 Minuten ohne Eingabe in Bereitschaft
```

Die Entwicklungsumgebung ruft das Programm über **Hooks** auf (`busy`, `idle`, `end`). Das ist der Teil, der die Verbindung zwischen Arbeit und Energie herstellt.

## redcode-lock

Sperrt den Bildschirm sofort mit einer Abdeckung, während der Sperrbildschirm noch lädt. Die Tastatur und Maus sind dabei abgefangen.

Ein wichtiger Befund aus dem Betrieb: `dm-tool lock` **nicht** verwenden. Bei LightDM 1.32 hing danach die Anmeldung in einer Schleife und das Passwort wurde nicht mehr angenommen. Stattdessen sperrt `xfce4-screensaver-command --lock` zuverlässig.

## Was man daran sieht

- **systemd und logind:** Der Deckel-Schalter wird über `logind` gesteuert. Eine eigene Konfiguration (`lid-ignore.conf`) verhindert, dass das System beim Zuklappen automatisch reagiert, und das Programm übernimmt die Entscheidung.
- **Hooks:** Ereignisse aus einem anderen Programm werden in Befehle übersetzt.
- **Fehlersuche:** Das Sperr-Problem wurde gefunden, dokumentiert und die sichere Alternative eingetragen.
- **Zeitsteuerung:** Countdown, abbrechbar, mit Status-Datei.

## Vorsicht

Ein Energiesparbefehl beendet laufende Arbeit. Vor dem ersten Einsatz mit `claude-power status` prüfen, welche Sitzungen aktiv sind.
