"""Reiter "Tastenkürzel" des Terminal-Studios: Alt-Tasten, eigene Kürzel, XFCE-Kürzel.

Alles wirkt sofort und ohne Claude: Die Datei ~/.config/kuerzel.json wird von kuerzel-waechter
und mac-keys.py laufend nachgeladen; XFCE-Kürzel werden per xfconf geschrieben.
"""
import json, os, re, subprocess, tempfile
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

DATEI = os.environ.get("KUERZEL_DATEI") or (os.path.expanduser("~/.config/kuerzel.json") if os.geteuid() != 0 else "/home/DEIN_BENUTZER/.config/kuerzel.json")
KANAL = "xfce4-keyboard-shortcuts"
PFEIL_DATEI = os.environ.get("PFEIL_DATEI") or (os.path.expanduser("~/.config/pfeil-auswahl.json") if os.geteuid() != 0 else "/home/DEIN_BENUTZER/.config/pfeil-auswahl.json")
PFEIL_TASTEN = [("schliessen", "Schließen", "^"), ("zeile_vor", "Nächste Zeile (Programm/Dock/Oben/Fenster)", "Tab"),
                ("zeile_zurueck", "Vorherige Zeile", "Shift+Tab"), ("links", "Links", "Left"), ("rechts", "Rechts", "Right"),
                ("hoch", "Hoch", "Up"), ("runter", "Runter", "Down"), ("klick", "Öffnen / Klick", "Return"),
                ("rechtsklick", "Rechtsklick", "Shift+Return"), ("doppelklick", "Doppelklick", "Ctrl+Return"),
                ("raster", "Raster (Maus-Ersatz)", "G"), ("verschieben", "Fenster verschieben", "M"),
                ("groesse", "Fenster-Größe", "R"), ("fenster_schliessen", "Fenster schließen", "W"),
                ("halb_links", "Fenster linke Hälfte", "Ctrl+Left"), ("halb_rechts", "Fenster rechte Hälfte", "Ctrl+Right")]

ALT_TASTEN = [("c", "Alt+C  Kopieren"), ("v", "Alt+V  Einfügen"), ("x", "Alt+X  Ausschneiden"),
              ("a", "Alt+A  Alles auswählen"), ("z", "Alt+Z  Rückgängig"), ("w", "Alt+W  Tab/Wort schließen"),
              ("q", "Alt+Q  Programm beenden (nicht im Terminal)"), ("d", "Alt+D  Wort markieren"),
              ("l", "Alt+L  Zeile markieren")]
TYPEN = [("programm", "Programm starten"), ("befehl", "Befehl ausführen"), ("tasten", "Tasten senden"),
         ("text", "Text tippen"), ("fenster", "Fenster-Aktion"), ("arbeitsflaeche", "Arbeitsfläche"),
         ("pfeil", "Pfeil-Auswahl öffnen"), ("hintergrund", "Hintergrund ändern")]
FENSTER_WERTE = ["schliessen", "minimieren", "maximieren", "vollbild", "links", "rechts", "nach_vorn",
                 "arbeitsflaeche_1", "arbeitsflaeche_2", "arbeitsflaeche_3", "arbeitsflaeche_4"]
UMFAENGE = [("ueberall", "überall"), ("terminal", "nur in Terminals"), ("nicht-terminal", "nicht in Terminals")]
HINTS = {"programm": "z. B. firefox oder thunar /home", "befehl": "Shell-Befehl", "tasten": "z. B. ctrl+shift+t (xdotool-Schreibweise)",
         "text": "wird getippt", "fenster": "schliessen, links, rechts, maximieren …", "arbeitsflaeche": "naechste, vorherige oder Nummer",
         "pfeil": "", "hintergrund": ""}
XF_MOD = {"Primary": "Ctrl", "Control": "Ctrl", "Alt": "Alt", "Shift": "Shift", "Super": "Meta", "Mod4": "Meta"}


def laden():
    try:
        with open(DATEI, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("version", 1)
    d.setdefault("eigene", [])
    d.setdefault("alt_tasten", {})
    return d


def speichern(daten):
    os.makedirs(os.path.dirname(DATEI), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(DATEI), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)                       # die Waechter laufen als Nutzer und muessen mitlesen
    os.replace(tmp, DATEI)


def pfeil_laden():
    try:
        with open(PFEIL_DATEI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def pfeil_speichern(daten):
    os.makedirs(os.path.dirname(PFEIL_DATEI), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(PFEIL_DATEI), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, PFEIL_DATEI)


def xf_zu_text(pfad_taste):
    """'<Primary><Alt>Left' -> 'Ctrl+Alt+Left'"""
    teile = re.findall(r"<([^>]+)>", pfad_taste)
    taste = re.sub(r"<[^>]+>", "", pfad_taste)
    return "+".join([XF_MOD.get(t, t) for t in teile] + [taste])


def text_zu_xf(text):
    """'Ctrl+Alt+Left' -> '<Primary><Alt>Left'"""
    teile = [t for t in text.replace(" ", "").split("+") if t]
    if not teile:
        return ""
    rueck = {"ctrl": "Primary", "strg": "Primary", "alt": "Alt", "shift": "Shift", "meta": "Super", "super": "Super"}
    mods = "".join(f"<{rueck.get(t.lower(), t)}>" for t in teile[:-1])
    return mods + teile[-1]


def xfconf_zeilen():
    """[(pfad, wert)] fuer /commands/custom und /xfwm4/custom."""
    try:
        aus = subprocess.run(["xfconf-query", "-c", KANAL, "-lv"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    zeilen = []
    for z in aus.splitlines():
        m = re.match(r"^(/(?:commands|xfwm4)/custom/\S+)\s+(.*)$", z)
        if m and m.group(2) and m.group(2) != "empty" and m.group(2) != "true":
            zeilen.append((m.group(1), m.group(2)))
    return zeilen


def baue_seite(studio):
    daten = laden()
    grid = studio.grid()
    zustand = {"timer": None}

    def titel(text):
        l = Gtk.Label(label=text, xalign=0)
        l.get_style_context().add_class("title")
        grid.attach(l, 0, grid.row, 2, 1); grid.row += 1

    def hinweis(text):
        l = Gtk.Label(label=text, xalign=0); l.set_line_wrap(True)
        l.get_style_context().add_class("hint")
        grid.attach(l, 0, grid.row, 2, 1); grid.row += 1

    def spaeter_speichern():
        if zustand["timer"]:
            GLib.source_remove(zustand["timer"])
        def tun():
            zustand["timer"] = None
            speichern(daten)
            status.set_text("Gespeichert – wirkt sofort.")
            return False
        zustand["timer"] = GLib.timeout_add(400, tun)

    status = Gtk.Label(label="", xalign=0)
    hinweis("Alles hier wirkt sofort, ohne Neustart und ohne dass du es Claude sagen musst. "
            "Taste anklicken → „Aufnehmen“ → gewünschte Kombination drücken.")
    grid.attach(status, 0, grid.row, 2, 1); grid.row += 1
    hg = Gtk.Button(label="🖼  Desktop-Hintergrund ändern …")
    hg.connect("clicked", lambda _b: subprocess.Popen([os.path.expanduser("~/.local/bin/hintergrund-aendern")
                                                        if os.geteuid() != 0 else "/home/DEIN_BENUTZER/.local/bin/hintergrund-aendern"],
                                                       start_new_session=True))
    hg.set_tooltip_text("Geht auch per Rechtsklick auf den Desktop")
    grid.attach(hg, 0, grid.row, 1, 1); grid.row += 1

    # --- Fenster schließen ---
    titel("Fenster schließen")
    hinweis("Tastenfolge, die das aktive Fenster schließt (auch Terminals). Standard: ^ dann 1 – beim ersten Tastendruck "
            "erscheint ein lila Rahmen, danach die nächste Taste. Mehrere Tasten mit Komma trennen, z. B. ^,1 oder F9,F10. "
            "Leer = Standard.")
    fe = Gtk.Entry(text=daten.get("fenster_schliessen", "^,1")); fe.set_width_chars(14)
    fa = Gtk.Button(label="Aufnehmen"); fr = Gtk.Button(label="↺"); fr.set_tooltip_text("Standard: ^,1")
    fb = Gtk.Box(spacing=6)
    fb.pack_start(fe, True, True, 0); fb.pack_start(fa, False, False, 0); fb.pack_start(fr, False, False, 0)
    def fenster_geaendert(w):
        wert = w.get_text().strip()
        if wert and wert != "^,1":
            daten["fenster_schliessen"] = wert
        else:
            daten.pop("fenster_schliessen", None)
        spaeter_speichern()
    fe.connect("changed", fenster_geaendert)
    fa.connect("clicked", lambda b: studio.record_hotkey(b, fe, "studioShortcuts", "close"))
    fr.connect("clicked", lambda _b: fe.set_text("^,1"))
    studio.row(grid, "Aktives Fenster schließen", fb)

    # --- Alt-Kürzel ---
    titel("Alt-Kürzel (wie am Mac)")
    for taste, text in ALT_TASTEN:
        sw = Gtk.Switch(active=daten["alt_tasten"].get(taste, True), halign=Gtk.Align.START)
        def geschaltet(w, _p, t=taste):
            daten["alt_tasten"][t] = w.get_active(); spaeter_speichern()
        sw.connect("notify::active", geschaltet)
        studio.row(grid, text, sw)

    # --- Eigene Kürzel ---
    titel("Eigene Kürzel")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    grid.attach(box, 0, grid.row, 2, 1); grid.row += 1
    zeilen = []

    def konflikte_markieren():
        gesehen = {}
        for z in zeilen:
            t = z["taste"].get_text().strip().lower()
            if t:
                gesehen.setdefault(t, []).append(z)
        for z in zeilen:
            t = z["taste"].get_text().strip().lower()
            anderswo = [x for x in gesehen.get(t, []) if x is not z] if t else []
            ctx = z["taste"].get_style_context()
            (ctx.add_class if anderswo else ctx.remove_class)("konflikt")
            z["taste"].set_tooltip_text("Doppelt belegt bei den eigenen Kürzeln" if anderswo else None)

    def zeile_bauen(e):
        row = Gtk.Box(spacing=6)
        an = Gtk.CheckButton(); an.set_active(e.get("an", True)); an.set_tooltip_text("an/aus")
        name = Gtk.Entry(text=e.get("name", "")); name.set_placeholder_text("Name"); name.set_width_chars(9)
        taste = Gtk.Entry(text=e.get("tasten", "")); taste.set_placeholder_text("Taste"); taste.set_width_chars(11)
        aufnehmen = Gtk.Button(label="Aufnehmen")
        typ = Gtk.ComboBoxText()
        for k, t in TYPEN:
            typ.append(k, t)
        typ.set_active_id(e.get("typ", "programm"))
        wert = Gtk.Entry(text=e.get("wert", "")); wert.set_hexpand(True); wert.set_width_chars(8)
        umfang = Gtk.ComboBoxText()
        for k, t in UMFAENGE:
            umfang.append(k, t)
        umfang.set_active_id(e.get("umfang", "ueberall") if e.get("umfang", "ueberall") in dict(UMFAENGE) else "ueberall")
        weg = Gtk.Button(label="🗑"); weg.set_tooltip_text("Löschen")
        for w in (an, name, taste, aufnehmen, typ, wert, umfang, weg):
            row.pack_start(w, w is wert, w is wert, 0)
        z = {"e": e, "row": row, "taste": taste}
        zeilen.append(z)

        def uebernehmen(*_a):
            e["an"] = an.get_active(); e["name"] = name.get_text(); e["tasten"] = taste.get_text().strip()
            e["typ"] = typ.get_active_id(); e["wert"] = wert.get_text(); e["umfang"] = umfang.get_active_id()
            wert.set_placeholder_text(HINTS.get(e["typ"], ""))
            wert.set_sensitive(e["typ"] not in ("pfeil", "hintergrund"))
            konflikte_markieren(); spaeter_speichern()
        for w, sig in ((an, "toggled"), (name, "changed"), (taste, "changed"), (typ, "changed"),
                       (wert, "changed"), (umfang, "changed")):
            w.connect(sig, uebernehmen)
        aufnehmen.connect("clicked", lambda b: studio.record_hotkey(b, taste, "studioShortcuts", "copy"))

        def loeschen(_b):
            daten["eigene"].remove(e); zeilen.remove(z); box.remove(row); spaeter_speichern(); konflikte_markieren()
        weg.connect("clicked", loeschen)
        typ.emit("changed")
        box.pack_start(row, False, False, 0)
        row.show_all()

    for e in daten["eigene"]:
        zeile_bauen(e)
    neu = Gtk.Button(label="+ Neues Kürzel")
    def neu_klick(_b):
        e = {"name": "Neu", "tasten": "", "typ": "programm", "wert": "", "umfang": "ueberall", "an": True}
        daten["eigene"].append(e); zeile_bauen(e); spaeter_speichern()
    neu.connect("clicked", neu_klick)
    grid.attach(neu, 0, grid.row, 1, 1); grid.row += 1
    konflikte_markieren()

    # --- Pfeil-Modus ---
    titel("Pfeil-Modus (Bedienung ohne Maus)")
    hinweis("Wirkt beim nächsten Start des Pfeil-Modus. Standard: Tab-Taste zwischen den Zeilen, Pfeile springen zum nächsten "
            "Element, Enter klickt. Geöffnet wird er über das System-Kürzel unten („pfeil-auswahl“).")
    pfeil = pfeil_laden()
    tasten_cfg = pfeil.setdefault("tasten", {})
    pfeil_timer = {"t": None}
    for aktion, text, standard in PFEIL_TASTEN:
        e = Gtk.Entry(text=tasten_cfg.get(aktion, standard)); e.set_width_chars(14)
        aufn = Gtk.Button(label="Aufnehmen"); reset = Gtk.Button(label="↺"); reset.set_tooltip_text("Standard: " + standard)
        rb = Gtk.Box(spacing=6)
        rb.pack_start(e, True, True, 0); rb.pack_start(aufn, False, False, 0); rb.pack_start(reset, False, False, 0)
        def geaendert(w, aktion=aktion, standard=standard):
            wert = w.get_text().strip()
            if wert and wert != standard:
                tasten_cfg[aktion] = wert
            else:
                tasten_cfg.pop(aktion, None)
            if pfeil_timer["t"]:
                GLib.source_remove(pfeil_timer["t"])
            def tun():
                pfeil_timer["t"] = None; pfeil_speichern(pfeil); status.set_text("Pfeil-Modus-Tasten gespeichert."); return False
            pfeil_timer["t"] = GLib.timeout_add(500, tun)
        e.connect("changed", geaendert)
        aufn.connect("clicked", lambda b, e=e: studio.record_hotkey(b, e, "studioShortcuts", "copy"))
        reset.connect("clicked", lambda _b, e=e, standard=standard: e.set_text(standard))
        studio.row(grid, text, rb)

    # --- XFCE-Kürzel ---
    titel("System-Kürzel (XFCE)")
    hinweis("Arbeitsflächen, Programme starten, Fenster verwalten. Änderung wird sofort übernommen (Enter oder Aufnehmen).")
    for pfad, wert in sorted(xfconf_zeilen(), key=lambda p: p[1]):
        prefix, taste = pfad.rsplit("/", 1)
        prefix += "/"
        e = Gtk.Entry(text=xf_zu_text(taste)); e.set_width_chars(14)
        aufn = Gtk.Button(label="Aufnehmen"); weg = Gtk.Button(label="🗑")
        rowbox = Gtk.Box(spacing=6)
        rowbox.pack_start(e, True, True, 0); rowbox.pack_start(aufn, False, False, 0); rowbox.pack_start(weg, False, False, 0)
        st = {"pfad": pfad, "wert": wert, "prefix": prefix}
        def xf_setzen(_w, st=st, e=e):
            teile = [t for t in e.get_text().replace(" ", "").split("+") if t]
            if not teile or teile[-1].lower() in ("ctrl", "strg", "alt", "shift", "meta", "super"):
                return                      # unvollstaendig (noch am Tippen)
            neu_taste = text_zu_xf(e.get_text())
            if not neu_taste:
                return
            neuer_pfad = st["prefix"] + neu_taste
            if neuer_pfad == st["pfad"]:
                return
            subprocess.run(["xfconf-query", "-c", KANAL, "-p", neuer_pfad, "-n", "-t", "string", "-s", st["wert"]])
            subprocess.run(["xfconf-query", "-c", KANAL, "-p", st["pfad"], "-r"])
            st["pfad"] = neuer_pfad
            status.set_text(f"System-Kürzel gesetzt: {e.get_text()}")
        e.connect("activate", xf_setzen)
        e.connect("focus-out-event", lambda w, ev, f=xf_setzen: f(w) or False)
        def verzoegert(_w, st=st, f=xf_setzen, e=e):
            if st.get("t"):
                GLib.source_remove(st["t"])
            st["t"] = GLib.timeout_add(1200, lambda: (st.update(t=None), f(e), False)[2])
        e.connect("changed", verzoegert)
        aufn.connect("clicked", lambda b, e=e: studio.record_hotkey(b, e, "studioShortcuts", "copy"))
        def xf_loeschen(_b, st=st, rowbox=rowbox):
            subprocess.run(["xfconf-query", "-c", KANAL, "-p", st["pfad"], "-r"])
            rowbox.hide(); status.set_text("System-Kürzel gelöscht.")
        weg.connect("clicked", xf_loeschen)
        anzeige = wert.replace("_key", "").replace("_", " ")
        if anzeige.startswith("/"):
            teile = anzeige.split(" ", 1)
            anzeige = os.path.basename(teile[0]) + (" " + teile[1] if len(teile) > 1 else "")
        beschr = Gtk.Label(label=anzeige, xalign=0); beschr.set_tooltip_text(wert)
        beschr.set_line_wrap(False); beschr.set_max_width_chars(30); beschr.set_ellipsize(3)
        grid.attach(beschr, 0, grid.row, 1, 1); grid.attach(rowbox, 1, grid.row, 1, 1); grid.row += 1

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(grid)
    return scroll
