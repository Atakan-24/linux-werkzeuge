# Kontrollzentrum für Sicherheitsprüfungen: Aufbau und Entscheidungen

Ein lokales Programm mit grafischer Oberfläche (Python, Tkinter), das Sicherheitsprüfungen
für Einsteiger strukturiert: vom Ziel über die Freigabe bis zum Bericht.

**Dieser Ordner enthält nur die Beschreibung, keinen Code der Werkzeug-Aufrufe.**

## Die Idee

Viele Einsteiger wissen nicht, was sie zuerst tun sollen. Das Programm führt deshalb über **Wege**
(„Ist meine Webseite sicher?“), und jeder Weg sagt vorher:

- was man **braucht** (z. B. eine Webadresse),
- was **passiert**,
- was man **danach bekommt** (Wissen oder Zugang).

![Startseite mit den Wegen](../bilder/kontrollzentrum/01-startseite.png)

## Wichtigster Grundsatz: Freigabe vor jeder Prüfung

Vor dem ersten Start bei einem Ziel fragt das Programm nach einer **schriftlichen Freigabe**:
Wer hat freigegeben, und bestätigt der Benutzer das ausdrücklich?
Ohne diese Angaben startet kein Werkzeug. Die Freigabe wird mit Datum gespeichert und landet im Bericht.

Die Freigabe ist eine Entscheidung der Oberfläche, nicht des Werkzeugs. Deshalb steht sie an der
Stelle, die jeden Start prüft.

![Vorschau eines Weges mit Ziel](../bilder/kontrollzentrum/04-weg-mit-ziel.png)

## Aufbau

| Teil | Aufgabe |
|---|---|
| **Oberfläche** | Fenster, Reiter, Vorschau je Weg, Erklärungen. Keine Logik zur Ausführung. |
| **Ausführung** | Startet Werkzeuge im Hintergrund und liefert die Ausgabe über eine **Warteschlange** an das Fenster zurück. Tkinter ist nicht thread-sicher, deshalb darf nur das Hauptfenster Bildschirmelemente ändern. |
| **Daten** | Ziele, Freigaben, Fortschritt und Berichte liegen in einfachen JSON-Dateien neben dem Programm. Keine Datenbank nötig. |
| **Wissen** | Erklärungen je Werkzeug als Text mit festen Feldern: Was ist das, was brauche ich, Beispiel, was bekommst du, Vorsicht. |
| **Übersetzung** | Die Rohausgabe einiger Werkzeuge wird in einfache Sätze umgewandelt. Das ist eine reine Textfunktion ohne Oberfläche und damit leicht prüfbar. |

## Fortschritt und Level

Jeder abgeschlossene Schritt zählt als Punkt. Die Stufen (Lehrling, Späher, Prüfer, Experte) zeigen den Lernfortschritt.
Der Fortschritt wird nach jedem Schritt gespeichert und bleibt nach einem Neustart erhalten.

## Bericht

Jede Prüfung kann als Markdown-Bericht gespeichert werden: Ziel, Freigabe mit Datum, abgeschlossene Schritte und das Ergebnis.
Fehlt die Freigabe, steht das im Bericht ausdrücklich.

![Werkzeugkiste](../bilder/kontrollzentrum/05-werkzeugkiste.png)

## Tests

- **Ablauf-Tests:** Die Oberfläche wird auf einem virtuellen Bildschirm (Xvfb) gestartet. Tests klicken Wege an, prüfen die Freigabe-Sperre und den Fortschritt, und vergleichen die Ergebnisse.
- **Datenschutz der Tests:** Jeder Test legt seine Dateien in einen eigenen Ordner. Die echten Daten werden nie verändert.
- **Logik-Tests:** Die Empfehlung des Assistenten und die Übersetzung der Ausgabe sind reine Funktionen und haben eigene Prüfungen.
- **Fehler, die die Tests fanden:** Oberflächenzugriffe aus Hintergrund-Threads (führten zu Abstürzen), doppelt belegte Zeilen in Dialogen, und ein Testlauf, der versehentlich echte Dateien veränderte. Die Ursachen sind behoben, und die Tests isolieren seitdem alles.

## Was bewusst nicht drin ist

- Keine Zusammenstellung von Angriffsbefehlen für fremde Ziele.
- Keine Werkzeugauswahl, die ohne Freigabe startet.
- Keine Speicherung von Zugangsdaten.

## Was man daraus lernt

Sicherheit beginnt bei der Organisation: Wer prüft, braucht eine Erlaubnis, muss wissen, was er tut, und sollte es dokumentieren.
Das Programm macht diese Schritte zur Pflicht, bevor etwas gestartet wird.
