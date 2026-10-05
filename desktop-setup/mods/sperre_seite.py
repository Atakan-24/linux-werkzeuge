"""Reiter „Sperre & Energie“: Bildschirm-Sperre (mit/ohne Passwort), Deckel zu und Leerlauf-Schlaf.

Sperre an/aus:  xfce4-power-manager /xfce4-power-manager/lock-screen-suspend-hibernate
                (+ xfce4-screensaver /lock/sleep-activation). claude-power liest den Wert, bevor es sperrt.
Alles andere:   /var/lib/claude-power-ui/ui.json  (gehört DEIN_BENUTZER). claude-power liest die Datei bei jedem
                Durchlauf und übernimmt nur bekannte Schlüssel mit passendem Typ (siehe UI_KEYS dort).
Alle Schalter gelten sofort. Von Hand sperren geht immer noch mit Super+L.
"""
import json, os, pwd, subprocess
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

UI_CONF = "/var/lib/claude-power-ui/ui.json"
KEYS = [
    ("xfce4-power-manager", "/xfce4-power-manager/lock-screen-suspend-hibernate"),
    ("xfce4-screensaver", "/lock/sleep-activation"),
]
# Standardwerte wie in claude-power conf()
DEFAULTS = {"lid_lock": True, "lid_minutes": 30, "lid_action": "hibernate",
            "idle_enabled": True, "idle_ac_min": 45, "idle_bat_min": 20,
            "idle_action": "suspend-then-hibernate", "idle_warn_s": 60, "idle_lock": True}
ACTIONS = [("suspend", "Bereitschaft (Energiesparmodus)"), ("hibernate", "Ruhezustand"),
           ("suspend-then-hibernate", "Bereitschaft, danach Ruhezustand"), ("shutdown", "Herunterfahren")]


def _xfconf(args):
    cmd = ["xfconf-query"] + args
    if os.geteuid() == 0:
        user = "DEIN_BENUTZER"
        uid = pwd.getpwnam(user).pw_uid
        cmd = ["runuser", "-u", user, "--", "env", f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def sperre_an():
    """True = automatische Sperre an (Standard, wenn der Wert fehlt)."""
    return _xfconf(["-c", KEYS[0][0], "-p", KEYS[0][1]]) != "false"


def setze_sperre(an):
    ok = True
    for kanal, prop in KEYS:
        wert = "true" if an else "false"
        if _xfconf(["-c", kanal, "-p", prop, "-n", "-t", "bool", "-s", wert]) is None:
            ok = _xfconf(["-c", kanal, "-p", prop, "-s", wert]) is not None and ok
    return ok and sperre_an() == an


def lade_ui():
    try:
        with open(UI_CONF) as f:
            ui = json.load(f)
    except Exception:
        ui = {}
    return {k: ui.get(k, v) for k, v in DEFAULTS.items()}


def speichere_ui(werte):
    tmp = UI_CONF + ".tmp"
    with open(tmp, "w") as f:
        json.dump(werte, f)
    os.replace(tmp, UI_CONF)


def baue_seite(studio=None):
    g = Gtk.Grid(column_spacing=14, row_spacing=10, margin=14)
    ui = lade_ui()
    status = Gtk.Label(xalign=0, wrap=True)
    zeile = [0]

    def kopf(text):
        l = Gtk.Label(xalign=0, margin_top=10)
        l.set_markup(f"<b>{GLib_escape(text)}</b>")
        g.attach(l, 0, zeile[0], 2, 1); zeile[0] += 1

    def reihe(label, widget, hint=None):
        if studio is not None and hasattr(studio, "mit_standard"):
            widget = studio.mit_standard(widget)
        g.attach(Gtk.Label(label=label, xalign=0), 0, zeile[0], 1, 1)
        widget.set_hexpand(True); g.attach(widget, 1, zeile[0], 1, 1); zeile[0] += 1
        if hint:
            h = Gtk.Label(label=hint, xalign=0, wrap=True); h.get_style_context().add_class("hint")
            g.attach(h, 1, zeile[0], 1, 1); zeile[0] += 1

    def ui_setzen(key, wert):
        ui[key] = wert
        try:
            speichere_ui(ui)
        except OSError as e:
            status.set_text(f"Nicht gespeichert: {e}")

    widgets = {}

    def schalter(key):
        sw = Gtk.Switch(active=ui[key], halign=Gtk.Align.START)
        sw.connect("notify::active", lambda w, _p: ui_setzen(key, w.get_active()))
        widgets[key] = sw
        return sw

    def zahl(key, lo, hi, step):
        sp = Gtk.SpinButton.new_with_range(lo, hi, step)
        sp.set_value(ui[key]); sp.set_halign(Gtk.Align.START)
        sp._standard = DEFAULTS[key]
        sp.connect("value-changed", lambda w: ui_setzen(key, int(w.get_value())))
        widgets[key] = sp
        return sp

    def auswahl(key):
        cb = Gtk.ComboBoxText(halign=Gtk.Align.START)
        for wert, text in ACTIONS:
            cb.append(wert, text)
        cb.set_active_id(ui[key])
        cb.connect("changed", lambda w: w.get_active_id() and ui_setzen(key, w.get_active_id()))
        widgets[key] = cb
        return cb

    # ---- Bildschirm-Sperre ----
    kopf("Bildschirm-Sperre")
    master = Gtk.Switch(active=sperre_an(), halign=Gtk.Align.START)

    def text():
        return ("Mit Passwort: Aufwachen aus Bereitschaft/Ruhezustand verlangt das Passwort."
                if master.get_active() else
                "Ohne Passwort: der Laptop sperrt nie von selbst, du kommst direkt zurück auf den Desktop.")

    def master_geaendert(sw, _p):
        an = sw.get_active()
        if not setze_sperre(an):
            sw.handler_block_by_func(master_geaendert)
            sw.set_active(sperre_an())
            sw.handler_unblock_by_func(master_geaendert)
            status.set_text("Hat nicht geklappt – Einstellung konnte nicht geändert werden.")
            return
        status.set_text(text())

    master.connect("notify::active", master_geaendert)
    status.set_text(text())
    reihe("Mit Passwort sperren", master, "Hauptschalter. Aus = nirgends automatisch sperren, egal was unten steht.")
    reihe("", status)
    reihe("Beim Deckel-Zuklappen sperren", schalter("lid_lock"))
    reihe("Vor dem Leerlauf-Schlaf sperren", schalter("idle_lock"))

    # ---- Deckel zu ----
    kopf("Deckel zugeklappt")
    reihe("Nach … Minuten schlafen", zahl("lid_minutes", 0, 480, 5),
          "0 = nie. Zählt nur, solange keine Claude-/Codex-Sitzung arbeitet. Bis dahin läuft der Laptop weiter.")
    reihe("Dann", auswahl("lid_action"))

    # ---- Leerlauf ----
    kopf("Leerlauf (Deckel offen, keine Maus/Tastatur)")
    dienst = subprocess.run(["systemctl", "is-active", "claude-power-idle"], capture_output=True, text=True).stdout.strip()
    reihe("Leerlauf-Schlaf einschalten", schalter("idle_enabled"),
          "Es wird nie geschlafen, solange Claude oder Codex arbeitet." if dienst == "active" else
          "ACHTUNG: Der Leerlauf-Dienst ist ausgeschaltet, deshalb schläft der Laptop im Leerlauf nicht von selbst. "
          "Einschalten (einmal im Terminal): sudo systemctl enable --now claude-power-idle")
    reihe("Am Ladekabel nach … Minuten", zahl("idle_ac_min", 1, 480, 5))
    reihe("Mit Akku nach … Minuten", zahl("idle_bat_min", 1, 480, 5))
    reihe("Dann", auswahl("idle_action"))
    reihe("Vorwarnung (Sekunden)", zahl("idle_warn_s", 10, 600, 10), "So lange kannst du mit einer Taste abbrechen.")

    h = Gtk.Label(xalign=0, wrap=True,
                  label="Alles gilt sofort, kein Speichern nötig. Von Hand sperren geht immer noch mit Super+L.")
    h.get_style_context().add_class("hint")
    g.attach(h, 0, zeile[0], 2, 1)
    def standard():
        """Alles auf Ausgangswerte (Sperre AN, Deckel 30 Min Ruhezustand, Leerlauf 45/20 Min ...)."""
        for key, wert in DEFAULTS.items():
            w = widgets[key]
            if isinstance(w, Gtk.Switch):
                w.set_active(wert)
            elif isinstance(w, Gtk.SpinButton):
                w.set_value(wert)
            else:
                w.set_active_id(wert)
        ui.update(DEFAULTS)
        speichere_ui(ui)
        master.set_active(True)

    if studio is not None:
        studio.sperre_standard = standard
    sc = Gtk.ScrolledWindow(); sc.add(g)
    return sc


def GLib_escape(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
