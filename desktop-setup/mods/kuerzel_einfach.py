"""Tastenkürzel – einfache Ansicht für das Terminal-Studio.

Bedienung: Auf das Tastenfeld klicken, neue Kombination drücken, fertig (Esc bricht ab).
Alles wirkt sofort. Gespeichert wird in denselben Dateien wie bisher:
  ~/.config/kuerzel.json (eigene Kürzel, Alt-Tasten, Fenster schließen), ~/.config/pfeil-auswahl.json,
  xfconf (System-Kürzel), studio.c (Terminal-Studio/QTerminal, wird mit „Speichern“ unten übernommen).
"""
import json, os, re, subprocess, tempfile, threading
from urllib.parse import unquote
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

import kuerzel_seite as ks
import kuerzel_zentral as kz

CSS = b"""
button.taste { background: #2a0a0a; color: #ffd8d8; border: 1px solid #6a2020; border-radius: 6px;
               padding: 4px 10px; font-family: monospace; font-weight: bold; min-width: 120px; }
button.taste:hover { border-color: #ff5050; background: #3a0e0e; }
button.taste.leer { color: #8a6060; font-weight: normal; }
button.taste.aufnahme { background: #a00010; color: white; border-color: #ff7070; }
button.taste.konflikt { border: 2px solid #ff3030; }
button.klein { padding: 2px 8px; min-width: 0; }
frame.karte { border: 1px solid #4a1818; border-radius: 8px; background: #1a0606; }
.kopf { font-size: 14px; font-weight: bold; color: #ff6060; }
.schritte { background: #240a0a; border-radius: 8px; padding: 8px; color: #f0d0d0; }
.ok { color: #7ee08a; } .warn { color: #ffb36b; font-weight: bold; }
"""

XF_NAMEN = {"close_window_key": "Fenster schließen", "maximize_window_key": "Fenster maximieren",
            "hide_window_key": "Fenster minimieren", "fullscreen_key": "Vollbild", "above_key": "Fenster immer oben",
            "stick_window_key": "Fenster auf allen Arbeitsflächen", "move_window_key": "Fenster verschieben",
            "resize_window_key": "Fenstergröße ändern", "add_workspace_key": "Arbeitsfläche hinzufügen",
            "del_workspace_key": "Arbeitsfläche löschen", "lower_window_key": "Fenster nach hinten",
            "raise_window_key": "Fenster nach vorn", "cycle_windows_key": "Fenster wechseln",
            "show_desktop_key": "Desktop zeigen", "tile_left_key": "Fenster links", "tile_right_key": "Fenster rechts",
            "left_workspace_key": "Arbeitsfläche links", "right_workspace_key": "Arbeitsfläche rechts",
            "up_workspace_key": "Arbeitsfläche hoch", "down_workspace_key": "Arbeitsfläche runter",
            "xfce4-popup-whiskermenu --pointer": "Startmenü", "xfrun4": "Programm ausführen",
            "xfce4-appfinder": "Programmsuche", "xflock4": "Bildschirm sperren", "xkill": "Programm abschießen",
            "xfce4-session-logout": "Abmelden", "exo-open --launch FileManager": "Dateimanager",
            "exo-open --launch TerminalEmulator": "Terminal"}
XF_BEFEHLE = {"/home/DEIN_BENUTZER/.local/bin/desktop-wechseln next": "Nächste Arbeitsfläche",
              "/home/DEIN_BENUTZER/.local/bin/desktop-wechseln prev": "Vorherige Arbeitsfläche",
              "/home/DEIN_BENUTZER/.local/bin/helligkeit-voll.sh": "Helligkeit auf voll",
              "/home/DEIN_BENUTZER/.local/bin/panel-reparieren.sh": "Leiste reparieren",
              "/home/DEIN_BENUTZER/.local/bin/panel-sichern.sh": "Leiste sichern",
              "/home/DEIN_BENUTZER/.local/bin/pfeil-auswahl": "Pfeil-Auswahl (Bedienung ohne Maus)",
              "exo-open --launch WebBrowser": "Webbrowser", "exo-open --launch MailReader": "E-Mail-Programm",
              "mate-calc": "Taschenrechner", "pkexec x-terminal-emulator": "Terminal als Administrator",
              "/usr/local/bin/kuerzel": "Kürzel-Übersicht", "/usr/local/bin/mac-screenshot bar": "Screenshot (Auswahlleiste)",
              "/usr/local/bin/mac-screenshot full": "Screenshot: ganzer Bildschirm",
              "/usr/local/bin/mac-screenshot region": "Screenshot: Bereich",
              "/usr/share/kali-themes/xfce4-screenshooter": "Screenshot-Programm",
              "/usr/share/kali-themes/xfce4-screenshooter --fullscreen --clipboard": "Screenshot ganzer Bildschirm → Zwischenablage",
              "/usr/share/kali-themes/xfce4-screenshooter --region": "Screenshot: Bereich",
              "/usr/share/kali-themes/xfce4-screenshooter --region --clipboard": "Screenshot Bereich → Zwischenablage",
              "/usr/share/kali-themes/xfce4-screenshooter --window": "Screenshot: aktives Fenster",
              "/usr/share/kali-themes/xfce4-screenshooter --window --clipboard": "Screenshot Fenster → Zwischenablage",
              "cycle_reverse_windows_key": "Fenster wechseln (rückwärts)", "switch_window_key": "Fenster wechseln (gleiche Art)",
              "cancel_key": "Abbrechen", "popup_menu_key": "Fenstermenü", "left_key": "Links", "right_key": "Rechts",
              "up_key": "Hoch", "down_key": "Runter", "prev_workspace_key": "Vorherige Arbeitsfläche",
              "next_workspace_key": "Nächste Arbeitsfläche"}
RICHTUNG = {"left": "links", "right": "rechts", "up": "oben", "down": "unten", "prev": "vorherige", "next": "nächste"}


def schoener_name(wert):
    """Technischen Kürzel-Befehl in lesbaren deutschen Text übersetzen."""
    if wert in XF_NAMEN:
        return XF_NAMEN[wert]
    if wert in XF_BEFEHLE:
        return XF_BEFEHLE[wert]
    m = re.fullmatch(r"move_window_workspace_(\d+)_key", wert)
    if m: return f"Fenster auf Arbeitsfläche {m.group(1)} schieben"
    m = re.fullmatch(r"workspace_(\d+)_key", wert)
    if m: return f"Arbeitsfläche {m.group(1)}"
    m = re.fullmatch(r"move_window_(left|right|up|down|prev|next)_workspace_key", wert)
    if m: return f"Fenster auf Arbeitsfläche {RICHTUNG[m.group(1)]} schieben"
    m = re.fullmatch(r"move_window_to_monitor_(left|right|up|down)_key", wert)
    if m: return f"Fenster auf Monitor {RICHTUNG[m.group(1)]}"
    m = re.fullmatch(r"tile_(up|down)?_?(left|right)?_?key", wert)
    if m and wert.startswith("tile_"):
        teile = [RICHTUNG[x] for x in wert[5:-4].split("_") if x in RICHTUNG]
        return "Fenster kacheln: " + " ".join(teile)
    return None


NAME_ZU_XF = {"PgUp": "Prior", "PgDown": "Next", "Space": "space", "Ins": "Insert", "Del": "Delete",
              "Comma": "comma", "+": "plus", "-": "minus", "^": "asciicircum"}
XF_ZU_NAME = {v: k for k, v in NAME_ZU_XF.items()}
XF_ZU_NAME.update({"Page_Down": "PgDown", "Page_Up": "PgUp"})
FENSTER_NAMEN = {"schliessen": "schließen", "minimieren": "minimieren", "maximieren": "maximieren",
                 "vollbild": "Vollbild", "links": "linke Hälfte", "rechts": "rechte Hälfte", "nach_vorn": "nach vorn",
                 "arbeitsflaeche_1": "auf Arbeitsfläche 1", "arbeitsflaeche_2": "auf Arbeitsfläche 2",
                 "arbeitsflaeche_3": "auf Arbeitsfläche 3", "arbeitsflaeche_4": "auf Arbeitsfläche 4"}
FLAECHE_NAMEN = {"naechste": "nächste", "vorherige": "vorherige", "1": "Nummer 1", "2": "Nummer 2",
                 "3": "Nummer 3", "4": "Nummer 4"}
VORGABEN = {"fenster": FENSTER_NAMEN, "arbeitsflaeche": FLAECHE_NAMEN}
AKTION_NAMEN = {"programm": "Programm starten", "befehl": "Befehl ausführen", "tasten": "Tasten senden",
                "text": "Text tippen", "fenster": "Fenster-Aktion", "arbeitsflaeche": "Arbeitsfläche wechseln",
                "pfeil": "Pfeil-Auswahl öffnen", "hintergrund": "Hintergrund ändern"}


class Tastenfeld(Gtk.Box):
    """Ein Knopf, der die Taste zeigt. Klick = aufnehmen, ↺ = Standard, ✕ = Taste entfernen."""

    def __init__(self, studio, text, aenderung, standard=None, einzeln=True, entfernbar=False):
        super().__init__(spacing=4)
        self.studio, self.text, self.cb, self.einzeln, self.standard = studio, text or "", aenderung, einzeln, standard
        self.btn = Gtk.Button()
        self.btn.get_style_context().add_class("taste")
        self.btn.set_tooltip_text("Klicken, dann die neue Tasten-Kombination drücken (Esc = abbrechen)")
        self.btn.connect("clicked", self.aufnehmen)
        self.pack_start(self.btn, True, True, 0)
        self.reset = self.weg = None
        if standard is not None:
            self.reset = Gtk.Button(label="↺")
            self.reset.get_style_context().add_class("klein")
            self.reset.set_tooltip_text("Zurück auf Standard: " + (standard or "keine Taste"))
            self.reset.connect("clicked", lambda _b: self.setze(standard))
            self.pack_start(self.reset, False, False, 0)
        if entfernbar:
            self.weg = Gtk.Button(label="✕")
            self.weg.get_style_context().add_class("klein")
            self.weg.set_tooltip_text("Taste entfernen (Kürzel ist dann aus)")
            self.weg.connect("clicked", lambda _b: self.setze(""))
            self.pack_start(self.weg, False, False, 0)
        self.zeige()

    def zeige(self, aufnahme=False):
        ctx = self.btn.get_style_context()
        if aufnahme:
            self.btn.set_label("⌨  Jetzt Taste drücken …")
            ctx.add_class("aufnahme")
            return
        ctx.remove_class("aufnahme")
        self.btn.set_label(self.text or "– keine Taste –")
        (ctx.add_class if not self.text else ctx.remove_class)("leer")
        if self.reset:
            self.reset.set_sensitive(self.text != (self.standard or ""))
        if self.weg:
            self.weg.set_sensitive(bool(self.text))

    def setze(self, text, melden=True):
        self.text = text or ""
        self.zeige()
        if melden and self.cb:
            self.cb(self.text)

    def markiere(self, tipp):
        ctx = self.btn.get_style_context()
        (ctx.add_class if tipp else ctx.remove_class)("konflikt")
        self.btn.set_tooltip_text(tipp or "Klicken, dann die neue Tasten-Kombination drücken (Esc = abbrechen)")

    def aufnehmen(self, _b):
        feld = self

        class Knopf:                    # Stellvertreter für studio.record_hotkey()
            def set_label(self, text):
                if text == "Aufnehmen":
                    feld.zeige()
                elif text.startswith("Taste drücken"):
                    feld.zeige(True)
                else:
                    feld.btn.set_label(text)        # „X … weitere Taste?“

            def grab_focus(self):
                feld.btn.grab_focus()

        class Eintrag:
            def set_text(self, t):
                if t != "Escape":                    # Esc bricht ab
                    feld.setze(t)

        self.zeige(True)
        self.studio.record_hotkey(Knopf(), Eintrag(), "studioShortcuts", "copy" if self.einzeln else "x")


def norm(text):
    t = re.sub(r"\b(Meta|Super)\b", "Super", (text or "").strip())      # kz.normal() liest Meta als Alt (tmux)
    return (kz.normal(t) or t).lower() if t else ""


def baue_seite(studio, _hotkeys_alt=None, _kuerzel_alt=None):
    css = Gtk.CssProvider(); css.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

    daten = ks.laden()
    pfeil = ks.pfeil_laden()
    timer = {}
    registry = []                    # {"name","kontext","get","feld"}
    suchzeilen = []                  # (widget, suchtext-Funktion, bereich)
    bereiche = {}                    # titel -> {"karte": widget, "zeilen": [...]}

    seite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=12)

    # ---- Kopf -------------------------------------------------------------------
    schritte = Gtk.Label(xalign=0, wrap=True)
    schritte.set_markup("<b>So geht's:</b>  ① Auf das Tastenfeld klicken   ② Neue Kombination drücken   "
                        "③ Fertig – wirkt sofort.\nEsc = abbrechen · ↺ = Standard · ✕ = Taste entfernen")
    schritte.get_style_context().add_class("schritte")
    seite.pack_start(schritte, False, False, 0)

    such = Gtk.SearchEntry(placeholder_text="Suchen: Name oder Taste (z. B. Kopieren oder Alt+C)")
    seite.pack_start(such, False, False, 0)
    status = Gtk.Label(xalign=0, wrap=True)
    seite.pack_start(status, False, False, 0)

    testg = studio.grid()
    studio.build_key_test(testg)
    testbox = Gtk.Frame(); testbox.get_style_context().add_class("karte")
    testbox.add(testg)
    seite.pack_start(testbox, False, False, 0)

    # ---- Hilfen -----------------------------------------------------------------
    def speichern_spaeter(art="kuerzel"):
        if timer.get(art):
            GLib.source_remove(timer[art])

        def tun():
            timer[art] = None
            if art == "kuerzel":
                ks.speichern(daten)
            else:
                ks.pfeil_speichern(pfeil)
            status_text("✔ Gespeichert – wirkt sofort.", "ok")
            return False
        timer[art] = GLib.timeout_add(350, tun)

    def status_text(text, klasse=None):
        status.set_text(text)
        ctx = status.get_style_context()
        for k in ("ok", "warn"):
            ctx.remove_class(k)
        if klasse:
            ctx.add_class(klasse)

    def pruefen(*_a):
        gruppen = {}
        for r in registry:
            n = norm(r["get"]())
            if n:
                gruppen.setdefault((r["kontext"], n), []).append(r)
        doppelt = 0
        if os.environ.get("KUERZEL_DEBUG"):
            for k, v in gruppen.items():
                if len(v) > 1:
                    print("DOPPELT", k, [x["name"] for x in v], flush=True)
        for r in registry:
            if not r["feld"]:
                continue
            n = norm(r["get"]())
            andere = [x["name"] for x in gruppen.get((r["kontext"], n), []) if x is not r] if n else []
            r["feld"].markiere(("Schon belegt von: " + ", ".join(andere)) if andere else None)
            doppelt += bool(andere)
        if doppelt:
            status_text(f"⚠ {doppelt} Tasten sind doppelt belegt (rot markiert) – fahr mit der Maus drüber.", "warn")
        elif status.get_text().startswith("⚠"):
            status_text("✔ Keine Doppelbelegung.", "ok")

    def neuer_bereich(titel, beschreibung=None, einklappbar=False, offen=True):
        karte = Gtk.Frame(); karte.get_style_context().add_class("karte")
        inhalt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=10)
        kopf = Gtk.Label(label=titel, xalign=0); kopf.get_style_context().add_class("kopf")
        if einklappbar:
            ex = Gtk.Expander(); ex.set_label_widget(kopf); ex.set_expanded(offen)
            ex.add(inhalt); karte.add(ex)
        else:
            ex = None
            inhalt.pack_start(kopf, False, False, 0)
            karte.add(inhalt)
        if beschreibung:
            b = Gtk.Label(label=beschreibung, xalign=0, wrap=True)
            b.get_style_context().add_class("hint")
            inhalt.pack_start(b, False, False, 0)
        seite.pack_start(karte, False, False, 0)
        bereiche[titel] = {"karte": karte, "ex": ex, "zeilen": []}
        return titel, inhalt

    def zeile(bereich, inhalt, name, feld, zusatz=None, tipp=None):
        row = Gtk.Box(spacing=8)
        l = Gtk.Label(label=name, xalign=0, hexpand=True)
        l.set_line_wrap(True); l.set_max_width_chars(34)
        if tipp:
            l.set_tooltip_text(tipp)
        row.pack_start(l, True, True, 0)
        if zusatz is not None:
            row.pack_start(zusatz, False, False, 0)
        row.pack_start(feld, False, False, 0)
        inhalt.pack_start(row, False, False, 0)
        bereiche[bereich]["zeilen"].append((row, lambda n=name, f=feld: (n + " " + (f.text if hasattr(f, "text") else "")).lower()))
        return row

    def eintragen(name, kontext, feld, get=None):
        registry.append({"name": name, "kontext": kontext, "feld": feld, "get": get or (lambda f=feld: f.text)})

    # ---- 1. Eigene Kürzel ---------------------------------------------------------
    b1, inh1 = neuer_bereich("Eigene Kürzel", "Eine Taste startet ein Programm, tippt Text, schiebt Fenster …")
    karten_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    inh1.pack_start(karten_box, False, False, 0)

    def wert_lesen(combo):
        return combo.get_active_id() or combo.get_child().get_text()

    def programm_waehlen(wert_combo):
        dlg = Gtk.AppChooserDialog.new_for_content_type(studio, 0, "text/plain")
        dlg.set_heading("Programm wählen")
        dlg.get_widget().set_show_all(True)          # alle installierten Programme, nicht nur „Textdateien“
        dlg.get_widget().set_show_other(True)
        if dlg.run() == Gtk.ResponseType.OK:
            app = dlg.get_app_info()
            if app:
                befehl = re.sub(r"\s*%[a-zA-Z]", "", app.get_commandline() or "").strip()
                wert_combo.get_child().set_text(befehl)
        dlg.destroy()

    def eigenes_bauen(e, aufnehmen=False):
        karte = Gtk.Frame(); karte.get_style_context().add_class("karte")
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=8); karte.add(v)
        kopf = Gtk.Box(spacing=6); v.pack_start(kopf, False, False, 0)
        an = Gtk.CheckButton(); an.set_active(e.get("an", True)); an.set_tooltip_text("Kürzel an/aus")
        name = Gtk.Entry(text=e.get("name", ""), placeholder_text="Name, z. B. Browser öffnen", hexpand=True)
        weg = Gtk.Button(label="🗑"); weg.get_style_context().add_class("klein"); weg.set_tooltip_text("Dieses Kürzel löschen")
        z2 = Gtk.Box(spacing=6); v.pack_start(z2, False, False, 0)
        typ = Gtk.ComboBoxText()
        for k, _t in ks.TYPEN:
            typ.append(k, AKTION_NAMEN.get(k, _t))
        typ.set_active_id(e.get("typ", "programm") if e.get("typ") in AKTION_NAMEN else "programm")
        wert = Gtk.ComboBoxText.new_with_entry(); wert.set_hexpand(True)
        wahl = Gtk.Button(label="Programm wählen …"); wahl.get_style_context().add_class("klein")
        wahl.set_no_show_all(True); wert.set_no_show_all(True)
        wahl.connect("clicked", lambda _b: programm_waehlen(wert))
        z2.pack_start(typ, False, False, 0); z2.pack_start(wert, True, True, 0); z2.pack_start(wahl, False, False, 0)
        z3 = Gtk.Box(spacing=6); v.pack_start(z3, False, False, 0)
        z3.pack_start(Gtk.Label(label="Gilt:"), False, False, 0)
        umfang = Gtk.ComboBoxText()
        for k, t in ks.UMFAENGE:
            umfang.append(k, t)
        umfang.set_active_id(e.get("umfang", "ueberall") if e.get("umfang") in dict(ks.UMFAENGE) else "ueberall")
        z3.pack_start(umfang, False, False, 0)

        def taste_geaendert(t):
            e["tasten"] = t
            speichern_spaeter(); pruefen()
        feld = Tastenfeld(studio, e.get("tasten", ""), taste_geaendert, standard=None, einzeln=True, entfernbar=True)
        kopf.pack_start(an, False, False, 0); kopf.pack_start(name, True, True, 0)
        kopf.pack_start(feld, False, False, 0); kopf.pack_start(weg, False, False, 0)
        reg = {"name": "eigenes Kürzel „%s“" % (e.get("name") or "?"), "kontext": "desktop", "feld": feld,
               "get": lambda: feld.text if an.get_active() else ""}
        registry.append(reg)

        def typ_gewechselt(*_a):
            t = typ.get_active_id() or "programm"
            wert.remove_all()
            for k, text in VORGABEN.get(t, {}).items():
                wert.append(k, text)
            wert.get_child().set_placeholder_text({"programm": "z. B. firefox oder thunar /home",
                                                   "befehl": "Shell-Befehl", "tasten": "z. B. ctrl+shift+t",
                                                   "text": "Text, der getippt wird"}.get(t, "Aktion wählen"))
            wert.set_visible(t not in ("pfeil", "hintergrund"))
            wahl.set_visible(t == "programm")
            alt = e.get("wert", "")
            if alt in VORGABEN.get(t, {}):
                wert.set_active_id(alt)
            elif wert.get_active_id() is None and not wert.get_child().get_text():
                wert.get_child().set_text(alt if e.get("typ", t) == t else "")

        def uebernehmen(*_a):
            e["an"] = an.get_active(); e["name"] = name.get_text()
            e["typ"] = typ.get_active_id(); e["wert"] = wert_lesen(wert); e["umfang"] = umfang.get_active_id()
            reg["name"] = "eigenes Kürzel „%s“" % (e["name"] or "?")
            speichern_spaeter(); pruefen()

        typ_gewechselt()
        typ.connect("changed", lambda *_a: (typ_gewechselt(), uebernehmen()))
        for w, sig in ((an, "toggled"), (name, "changed"), (wert, "changed"), (umfang, "changed")):
            w.connect(sig, uebernehmen)

        def loeschen(_b):
            daten["eigene"].remove(e); registry.remove(reg); karten_box.remove(karte)
            speichern_spaeter(); pruefen()
        weg.connect("clicked", loeschen)
        karten_box.pack_start(karte, False, False, 0)
        karte.show_all()
        wahl.set_visible((typ.get_active_id() or "") == "programm")
        wert.set_visible((typ.get_active_id() or "") not in ("pfeil", "hintergrund"))
        if aufnehmen:
            name.grab_focus()
            GLib.idle_add(lambda: feld.aufnehmen(None) or False)
        bereiche[b1]["zeilen"].append((karte, lambda: ((e.get("name") or "") + " " + (e.get("tasten") or "")
                                                          + " " + (e.get("wert") or "")).lower()))

    for e in daten["eigene"]:
        eigenes_bauen(e)
    neu = Gtk.Button(label="＋  Neues Kürzel anlegen")
    neu.get_style_context().add_class("save")

    def neu_klick(_b):
        e = {"name": "", "tasten": "", "typ": "programm", "wert": "", "umfang": "ueberall", "an": True}
        daten["eigene"].append(e); eigenes_bauen(e, aufnehmen=True); speichern_spaeter()
    neu.connect("clicked", neu_klick)
    inh1.pack_start(neu, False, False, 0)

    # ---- 2. Fenster schließen + Alt-Tasten ------------------------------------------
    b2, inh2 = neuer_bereich("Fenster & Mac-Tasten",
                             "Alt-Tasten arbeiten wie die Befehlstaste am Mac. In Terminals bleiben sie für tmux frei.")

    def schliessen_geaendert(t):
        if t and t != "^,1":
            daten["fenster_schliessen"] = t
        else:
            daten.pop("fenster_schliessen", None)
        speichern_spaeter(); pruefen()
    fs = Tastenfeld(studio, daten.get("fenster_schliessen", "^,1"), schliessen_geaendert, standard="^,1", einzeln=False)
    zeile(b2, inh2, "Aktives Fenster schließen (Tastenfolge, z. B. ^ dann 1)", fs)
    eintragen("Fenster schließen", "desktop", fs)
    for taste, text in ks.ALT_TASTEN:
        sw = Gtk.Switch(active=daten["alt_tasten"].get(taste, True), halign=Gtk.Align.END, valign=Gtk.Align.CENTER)

        def geschaltet(w, _p, t=taste):
            daten["alt_tasten"][t] = w.get_active(); speichern_spaeter(); pruefen()
        sw.connect("notify::active", geschaltet)
        kurz = text.split("  ", 1)
        zeile(b2, inh2, kurz[1] if len(kurz) > 1 else text, sw, zusatz=Gtk.Label(label=kurz[0]))
        registry.append({"name": "Alt-Taste " + kurz[0], "kontext": "desktop", "feld": None,
                         "get": lambda s=sw, t=taste: ("Alt+" + t.upper()) if s.get_active() else ""})

    # ---- 3. System-Kürzel (XFCE) -------------------------------------------------------
    b3, inh3 = neuer_bereich("System (Arbeitsflächen, Programme, Fenster)",
                             "Die Kürzel deines Desktops. Änderungen gelten sofort.", einklappbar=True, offen=False)
    for pfad, wert in sorted(ks.xfconf_zeilen(), key=lambda p: schoener_name(p[1]) or p[1]):
        prefix, taste = pfad.rsplit("/", 1)
        st = {"pfad": pfad, "prefix": prefix + "/", "wert": wert}
        teile0 = ks.xf_zu_text(taste).split("+")
        teile0[-1] = XF_ZU_NAME.get(teile0[-1], teile0[-1].upper() if len(teile0[-1]) == 1 else teile0[-1])
        text0 = "+".join(teile0)

        def xf_neu(t, st=st):
            teile = t.split("+") if t else []
            if not teile:
                subprocess.run(["xfconf-query", "-c", ks.KANAL, "-p", st["pfad"], "-r"])
                status_text("✔ System-Kürzel entfernt.", "ok"); return
            teile[-1] = NAME_ZU_XF.get(teile[-1], teile[-1].lower() if len(teile[-1]) == 1 else teile[-1])
            neu_pfad = st["prefix"] + ks.text_zu_xf("+".join(teile))
            if neu_pfad == st["pfad"]:
                return
            subprocess.run(["xfconf-query", "-c", ks.KANAL, "-p", neu_pfad, "-n", "-t", "string", "-s", st["wert"]])
            subprocess.run(["xfconf-query", "-c", ks.KANAL, "-p", st["pfad"], "-r"])
            st["pfad"] = neu_pfad
            status_text("✔ System-Kürzel gesetzt.", "ok"); pruefen()
        feld = Tastenfeld(studio, text0, xf_neu, standard=None, einzeln=True, entfernbar=True)
        name = schoener_name(wert) or wert.replace("_key", "").replace("_", " ")
        if name.startswith("/"):
            t = name.split(" ", 1); name = os.path.basename(t[0]) + (" " + t[1] if len(t) > 1 else "")
        zeile(b3, inh3, name, feld, tipp=wert)
        eintragen("System: " + name, "desktop", feld)

    # ---- 4. Terminal-Studio -------------------------------------------------------------
    b4, inh4 = neuer_bereich("Terminal-Studio", "Tasten im Studio-Fenster selbst. Gelten nach „Speichern“ unten.")
    import __main__ as hauptprogramm
    labels = getattr(hauptprogramm, "STUDIO_HOTKEY_LABELS", {})

    def c_feld(gruppe, action, name, einzeln, bereich, inhalt, kontext="studio"):
        def geaendert(t, g=gruppe, a=action):
            studio.c[g][a] = t
            pruefen()
        feld = Tastenfeld(studio, studio.c[gruppe].get(action, ""), geaendert,
                          standard=studio.hotkey_default(gruppe, action), einzeln=einzeln)
        zeile(bereich, inhalt, name, feld)
        eintragen(name, kontext, feld)

    for action, label in labels.items():
        c_feld("studioShortcuts", action, label, action != "close", b4, inh4)

    # ---- 5. QTerminal -------------------------------------------------------------------
    qt = studio.c.get("terminalShortcuts", {})
    b5, inh5 = neuer_bereich(f"QTerminal – alle Aktionen ({len(qt)})",
                             "Tasten im Terminal-Fenster (Tabs, Teilen, Kopieren …).", einklappbar=True, offen=False)
    for key in sorted(qt, key=lambda x: unquote(x).lower()):
        c_feld("terminalShortcuts", key, unquote(key), True, b5, inh5, "qterminal")

    # ---- 6. Für Fortgeschrittene: Pfeil-Modus ---------------------------------------------
    b6, inh6 = neuer_bereich("Pfeil-Modus (Bedienung ohne Maus)",
                             "Tab springt zwischen den Zeilen, Pfeile zum nächsten Element, Enter klickt. "
                             "Gilt beim nächsten Start des Pfeil-Modus.", einklappbar=True, offen=False)
    tasten_cfg = pfeil.setdefault("tasten", {})
    for aktion, text, standard in ks.PFEIL_TASTEN:
        def pfeil_neu(t, a=aktion, s=standard):
            if t and t != s:
                tasten_cfg[a] = t
            else:
                tasten_cfg.pop(a, None)
            speichern_spaeter("pfeil")
        feld = Tastenfeld(studio, tasten_cfg.get(aktion, standard), pfeil_neu, standard=standard, einzeln=True)
        zeile(b6, inh6, text, feld)

    # ---- 7. Für Fortgeschrittene: tmux/Chat -------------------------------------------------
    b7, inh7 = neuer_bereich("Chat & tmux (Fortgeschrittene)",
                             "Tasten im tmux (Chats, Scroll-Modus, Kopieren). Schreibweise: M-y = Alt+Y, C-a = Strg+A. "
                             "Speichern verlangt dein Passwort.", einklappbar=True, offen=False)
    tm = kz.tmux_liste()
    tm_felder = []
    if not tm:
        inh7.pack_start(Gtk.Label(label="Liste noch nicht erzeugt – unten „Liste aktualisieren“.", xalign=0),
                        False, False, 0)
    for z in tm:
        e = Gtk.Entry(text=z["aktuell"]); e.set_width_chars(12)
        row = zeile(b7, inh7, f'{z["name"]}  ({z["tabelle"]})', e)
        tm_felder.append((z, e))
    tm_status = Gtk.Label(xalign=0, wrap=True)

    def tm_lauf(befehl, ok_text):
        tm_status.set_text("Einen Moment … Passwort nötig.")

        def arbeit():
            r = subprocess.run(befehl, capture_output=True, text=True)
            GLib.idle_add(tm_status.set_text, ok_text if r.returncode == 0 else
                          "Hat nicht geklappt: " + (r.stderr or r.stdout).strip()[-200:])
        threading.Thread(target=arbeit, daemon=True).start()

    def tm_speichern(_b):
        aend = [{"tabelle": z["tabelle"], "von": z["original"], "nach": e.get_text().strip()}
                for z, e in tm_felder if e.get_text().strip() and e.get_text().strip() != z["original"]]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(aend, f); tmp = f.name
        os.chmod(tmp, 0o644)
        tm_lauf(["pkexec", kz.TOOL, "anwenden", "--echt", tmp], "Gespeichert. Läuft im tmux sofort.")

    def tm_standard(_b):
        for z, e in tm_felder:
            e.set_text(z["original"])
    bx = Gtk.Box(spacing=8)
    for t, f in (("tmux-Tasten speichern", tm_speichern), ("Alle auf Standard", tm_standard),
                 ("Liste aktualisieren", lambda _b: tm_lauf(["pkexec", kz.TOOL, "liste", "--echt"],
                                                           "Liste erneuert. Studio neu öffnen."))):
        b = Gtk.Button(label=t); b.connect("clicked", f); bx.pack_start(b, False, False, 0)
    inh7.pack_start(bx, False, False, 0)
    inh7.pack_start(tm_status, False, False, 0)

    # ---- Suche ----------------------------------------------------------------------
    def suchen(_w):
        q = such.get_text().strip().lower()
        for titel, b in bereiche.items():
            sichtbar = 0
            for widget, text in b["zeilen"]:
                treffer = not q or q in text()
                widget.set_visible(treffer)
                sichtbar += treffer
            b["karte"].set_visible(not q or sichtbar > 0)
            if b["ex"] is not None and q and sichtbar:
                b["ex"].set_expanded(True)
    such.connect("search-changed", suchen)

    pruefen()
    if not status.get_text():
        status_text("✔ Keine Doppelbelegung.", "ok")
    scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(seite)
    return scroll
