"""Ein Reiter für alle Kürzel: Suche, Konflikte über alle Bereiche, tmux- und Chat-Tasten."""
import json, os, subprocess, tempfile, threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

CACHE = "/usr/local/share/terminal-studio/tmux-tasten.json"
TOOL = "/usr/local/sbin/terminal-studio-tmux"
MODS = {"ctrl": "Ctrl", "control": "Ctrl", "alt": "Alt", "shift": "Shift", "super": "Super", "meta": "Alt",
        "c": "Ctrl", "m": "Alt", "s": "Shift"}


def normal(text, tmux=False):
    """'Ctrl+Shift+C' oder 'M-c' -> 'Alt+C' (gleiche Schreibweise). Folgen (mit Komma) -> None."""
    t = (text or "").strip()
    if not t or ("," in t and len(t) > 1 and not tmux):
        return None
    teile = t.split("-") if tmux and "-" in t and len(t) > 1 else t.split("+")
    if tmux and len(teile) > 1 and teile[-1] == "":
        teile = teile[:-2] + ["-"]
    mods, taste = [], teile[-1]
    for m in teile[:-1]:
        k = MODS.get(m.lower()) if (not tmux or len(m) == 1) else None
        if k is None:
            return None
        mods.append(k)
    return "+".join(sorted(set(mods)) + [taste.upper() if len(taste) == 1 else taste.capitalize()])


def tmux_liste():
    try:
        return json.load(open(CACHE))
    except Exception:
        return []


def sammeln(studio, tmux_zeilen):
    """[(Bereich, Aktion, Taste)]"""
    out = []
    for a, k in studio.c.get("studioShortcuts", {}).items():
        out.append(("Studio", a, k))
    for a, k in studio.c.get("terminalShortcuts", {}).items():
        out.append(("QTerminal", a, k))
    try:
        d = json.load(open(os.path.expanduser("~/.config/kuerzel.json")))
        for e in d.get("eigene", []):
            if e.get("an", True):
                out.append(("Desktop", e.get("name", "?"), e.get("tasten", "")))
        for k, an in d.get("alt_tasten", {}).items():
            if an:
                out.append(("Alt-Tasten", "Alt+" + k.upper(), "Alt+" + k.upper()))
    except Exception:
        pass
    for z in tmux_zeilen:
        out.append(("tmux", "%s (%s)" % (z["name"], z["tabelle"]), z["aktuell"]))
    return out


def baue_seite(studio, hotkeys_widget, kuerzel_widget):
    if not os.environ.get("KUERZEL_ALTE_ANSICHT"):
        try:                                   # neue, einfache Ansicht; bei Fehler weiter mit der alten
            import kuerzel_einfach
            return kuerzel_einfach.baue_seite(studio)
        except Exception as fehler:
            import sys, traceback
            traceback.print_exc()
            print("Einfache Kürzel-Ansicht nicht geladen:", fehler, file=sys.stderr)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
    such = Gtk.SearchEntry(placeholder_text="Suchen: Name oder Taste (z. B. Alt+C)")
    box.pack_start(such, False, False, 0)
    konf = Gtk.Label(xalign=0, wrap=True)
    box.pack_start(konf, False, False, 0)
    treffer = Gtk.Label(xalign=0, wrap=True, selectable=True)
    box.pack_start(treffer, False, False, 0)
    tm = tmux_liste()
    eintraege = []          # (zeile, Entry)

    def neu_pruefen(*_):
        daten = []
        for z, e in eintraege:
            daten.append(dict(z, aktuell=e.get_text().strip() or z["aktuell"]))
        alle = sammeln(studio, daten if eintraege else tm)
        by = {}
        for b, a, k in alle:
            n = normal(k, tmux=(b == "tmux"))
            if n:
                by.setdefault(n, []).append((b, a))
        probleme = ["%s: %s" % (n, " ↔ ".join("%s „%s“" % x for x in v))
                    for n, v in by.items() if len({b for b, _ in v}) > 1 and len(v) > 1]
        konf.set_markup("<b>Doppelte Kürzel zwischen Bereichen:</b>\n" + "\n".join(probleme[:12])
                        if probleme else "Keine Doppelbelegung zwischen den Bereichen gefunden.")
        q = such.get_text().strip().lower()
        if q:
            gef = ["%s – %s: %s" % (b, a, k) for b, a, k in alle if q in a.lower() or q in (k or "").lower()
                   or q == (normal(k, tmux=(b == "tmux")) or "").lower() or q == (normal(q) or "x") and normal(k, tmux=(b == "tmux")) == normal(q)]
            treffer.set_text("\n".join(gef[:40]) if gef else "Nichts gefunden.")
        else:
            treffer.set_text("")

    such.connect("search-changed", neu_pruefen)

    def abschnitt(titel, widget, hoehe, offen=False):
        ex = Gtk.Expander(label=titel); ex.set_expanded(offen)
        widget.set_size_request(-1, hoehe)
        ex.add(widget)
        box.pack_start(ex, False, False, 0)

    abschnitt("Studio & QTerminal (Tasten fürs Terminal-Fenster)", hotkeys_widget, 420)
    abschnitt("Alt-Tasten, eigene Kürzel, Desktop", kuerzel_widget, 420)

    # --- tmux --------------------------------------------------------------
    tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    tb.pack_start(Gtk.Label(label="Tasten im tmux (Chats, Scroll-Modus, Kopieren …). Neue Taste z. B. M-y = Alt+Y, "
                                  "C-a = Strg+A.", xalign=0, wrap=True), False, False, 0)
    gitter = Gtk.Grid(row_spacing=3, column_spacing=10)
    if not tm:
        gitter.attach(Gtk.Label(label="Liste noch nicht erzeugt: unten „Liste aktualisieren“.", xalign=0), 0, 0, 3, 1)
    for i, z in enumerate(tm):
        gitter.attach(Gtk.Label(label=z["name"], xalign=0), 0, i, 1, 1)
        gitter.attach(Gtk.Label(label=z["tabelle"], xalign=0), 1, i, 1, 1)
        e = Gtk.Entry(text=z["aktuell"]); e.set_width_chars(12)
        e.connect("changed", neu_pruefen)
        gitter.attach(e, 2, i, 1, 1)
        eintraege.append((z, e))
    rolle = Gtk.ScrolledWindow(); rolle.set_min_content_height(300); rolle.add(gitter)
    tb.pack_start(rolle, True, True, 0)
    status = Gtk.Label(xalign=0, wrap=True)

    def lauf(befehl, text):
        status.set_text("Einen Moment … Passwort nötig.")
        def arbeit():
            r = subprocess.run(befehl, capture_output=True, text=True)
            GLib.idle_add(status.set_text, text if r.returncode == 0 else
                          "Hat nicht geklappt: " + (r.stderr or r.stdout).strip()[-200:])
        threading.Thread(target=arbeit, daemon=True).start()

    def speichern(_b):
        aend = [{"tabelle": z["tabelle"], "von": z["original"], "nach": e.get_text().strip()}
                for z, e in eintraege if e.get_text().strip() and e.get_text().strip() != z["original"]]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(aend, f); tmp = f.name
        os.chmod(tmp, 0o644)
        lauf(["pkexec", TOOL, "anwenden", "--echt", tmp],
             "Gespeichert. Läuft im tmux sofort; Studio neu öffnen zeigt den Stand.")

    def standard(_b):
        for z, e in eintraege:
            e.set_text(z["original"])

    def aktualisieren(_b):
        lauf(["pkexec", TOOL, "liste", "--echt"], "Liste erneuert. Studio neu öffnen.")
    bx = Gtk.Box(spacing=8)
    for t, f in (("Tmux-Tasten speichern", speichern), ("Alle auf Standard", standard),
                 ("Liste aktualisieren", aktualisieren)):
        b = Gtk.Button(label=t); b.connect("clicked", f); bx.pack_start(b, False, False, 0)
    tb.pack_start(bx, False, False, 0)
    tb.pack_start(status, False, False, 0)
    ex = Gtk.Expander(label="tmux- und Chat-Tasten"); ex.set_expanded(True); ex.add(tb)
    box.pack_start(ex, False, False, 0)
    neu_pruefen()
    scroll = Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(box)
    return scroll
