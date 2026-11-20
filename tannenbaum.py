#!/usr/bin/env python3
"""Tannenbaum mit bunten Kugeln und Adventskerzen im Terminal.

Ab dem 1. Advent brennt die erste Kerze (flackernde Flamme), mit jedem
weiteren Adventstag eine Kerze mehr. Vom 24.12. bis 6.1. brennen alle.

Aufruf:
    python3 tannenbaum.py                      # heutiges Datum
    python3 tannenbaum.py --datum 2026-12-10   # beliebiges Datum testen
    python3 tannenbaum.py --modus sonntage     # nur 4 Kerzen (je Adventssonntag)

Tasten:  d = Datum simulieren (Eingabe TT.MM.JJJJ, leer = heute)
         q = Beenden (oder Strg+C)
"""

import argparse
import curses
import datetime as dt
import random

HOEHE = 18          # Anzahl Zeilen der Baumkrone
KUGEL_ANTEIL = 0.13  # Anteil der Nadelfelder, die eine Kugel tragen
FRAME_MS = 120      # Zeit zwischen zwei Bildern (Flackern)

# Kerzenkörper: linke Baumhälfte U+258D (Linker Drei-Achtel-Block),
# rechte Baumhälfte U+1FB88 (Rechter Drei-Achtel-Block).
# Falls die Schrift U+1FB88 nicht kennt: "▐" (Rechte Hälfte) verwenden.
KERZE_LINKS = "▍"
KERZE_RECHTS = "\U0001fb88"
KERZEN_BREITE = 1
KERZEN_ABSTAND = 6   # Mindestabstand zwischen zwei Kerzen einer Zeile
FLAMMEN = "^*'\"()^"  # Flammenformen (flackern zufällig)

# Farbpaar-Nummern
GRUEN, ROT, BLAU, MAGENTA, CYAN, GELB, WEISS, STAMM = range(1, 9)
KUGELFARBEN = [ROT, BLAU, MAGENTA, CYAN, GELB, WEISS]


# --------------------------------------------------------------------------
# Datumslogik
# --------------------------------------------------------------------------
def erster_advent(jahr: int) -> dt.date:
    """1. Advent = 3 Wochen vor dem 4. Advent (letzter Sonntag bis 24.12.)."""
    heiligabend = dt.date(jahr, 12, 24)
    tage_seit_sonntag = (heiligabend.weekday() + 1) % 7  # Mo=0 ... So=6
    vierter_advent = heiligabend - dt.timedelta(days=tage_seit_sonntag)
    return vierter_advent - dt.timedelta(weeks=3)


def kerzen_status(heute: dt.date, modus: str):
    """Liefert (Kerzen gesamt, davon brennend, Datum 1. Advent)."""
    # Anfang Januar gehört noch zur Weihnachtszeit des Vorjahres
    jahr = heute.year if heute.month >= 7 else heute.year - 1
    start = erster_advent(jahr)
    heiligabend = dt.date(jahr, 12, 24)

    gesamt = (heiligabend - start).days + 1 if modus == "tage" else 4

    if heute < start:
        brennend = 0
    elif heute <= heiligabend:
        tag = (heute - start).days
        brennend = tag + 1 if modus == "tage" else tag // 7 + 1
    elif heute <= dt.date(jahr + 1, 1, 6):
        brennend = gesamt
    else:
        brennend = 0
    return gesamt, brennend, start


# --------------------------------------------------------------------------
# Baum aufbauen (statischer Teil)
# --------------------------------------------------------------------------
def baue_baum(gesamt_kerzen: int):
    """Erzeugt Nadeln, Kugeln und Kerzenpositionen (relativ zur Mitte)."""
    rng = random.Random(2412)  # fester Seed -> Baum sieht immer gleich aus
    zellen = {}  # (y, dx) -> (zeichen, farbpaar, fett)

    # Baumkrone: Zeile k reicht von -k bis +k
    for k in range(HOEHE):
        y = k + 1
        for dx in range(-k, k + 1):
            if dx == -k:
                zeichen = "/"
            elif dx == k:
                zeichen = "\\"
            else:
                zeichen = "^"
            zellen[(y, dx)] = (zeichen, GRUEN, False)

    # Kerzenplätze: jede zweite Zeile, gleichmäßig über die Breite verteilt
    # (außen an den Astspitzen und dazwischen auf den Zweigen).
    # Eine Kerze ist KERZEN_BREITE Zeichen breit, die Flamme sitzt darüber.
    plaetze = []
    for k in range(3, HOEHE, 2):
        links, rechts = -k - KERZEN_BREITE, k + 1  # Startspalten außen
        anzahl = (rechts - links) // KERZEN_ABSTAND + 1
        schritt = (rechts - links) / (anzahl - 1)
        for i in range(anzahl):
            plaetze.append((k + 1, round(links + i * schritt)))
    if gesamt_kerzen > len(plaetze):
        raise ValueError("Zu viele Kerzen für die Baumhöhe")
    if gesamt_kerzen == 1:
        auswahl = [plaetze[len(plaetze) // 2]]
    else:
        schritt = (len(plaetze) - 1) / (gesamt_kerzen - 1)
        auswahl = [plaetze[round(i * schritt)] for i in range(gesamt_kerzen)]
    rng.shuffle(auswahl)  # Reihenfolge des Anzündens über den Baum verteilen

    # Felder von Kerzen und Flammen bleiben frei von Kugeln
    belegt = set()
    for y, dx in auswahl:
        for i in range(KERZEN_BREITE):
            belegt.add((y, dx + i))
            belegt.add((y - 1, dx + i))

    # Kugeln im Inneren der Krone
    for k in range(1, HOEHE):
        for dx in range(-k + 1, k):
            if (k + 1, dx) in belegt:
                continue
            if rng.random() < KUGEL_ANTEIL:
                zellen[(k + 1, dx)] = ("o", rng.choice(KUGELFARBEN), True)

    return zellen, auswahl


# --------------------------------------------------------------------------
# Zeichnen
# --------------------------------------------------------------------------
def init_farben():
    curses.start_color()
    try:
        curses.use_default_colors()
        hg = -1
    except curses.error:
        hg = curses.COLOR_BLACK
    curses.init_pair(GRUEN, curses.COLOR_GREEN, hg)
    curses.init_pair(ROT, curses.COLOR_RED, hg)
    curses.init_pair(BLAU, curses.COLOR_BLUE, hg)
    curses.init_pair(MAGENTA, curses.COLOR_MAGENTA, hg)
    curses.init_pair(CYAN, curses.COLOR_CYAN, hg)
    curses.init_pair(GELB, curses.COLOR_YELLOW, hg)
    curses.init_pair(WEISS, curses.COLOR_WHITE, hg)
    curses.init_pair(STAMM, curses.COLOR_RED, hg)


def schreibe(scr, y, x, text, paar, fett=False):
    attr = curses.color_pair(paar) | (curses.A_BOLD if fett else 0)
    try:
        scr.addstr(y, x, text, attr)
    except curses.error:
        pass  # Rand des Fensters – ignorieren


def zeichne(scr, zellen, kerzen, brennend, info):
    scr.erase()
    max_y, max_x = scr.getmaxyx()
    noetig_y, noetig_x = HOEHE + 7, 2 * HOEHE + 6
    if max_y < noetig_y or max_x < noetig_x:
        schreibe(scr, 0, 0, f"Fenster zu klein ({max_x}x{max_y}), "
                            f"benötigt {noetig_x}x{noetig_y}", WEISS, True)
        scr.refresh()
        return

    oben = max(0, (max_y - noetig_y) // 2)
    mitte = max_x // 2

    # Stern an der Spitze (funkelt leicht)
    stern = random.choice("*+*X*")
    schreibe(scr, oben, mitte, stern, GELB, True)

    for (y, dx), (z, paar, fett) in zellen.items():
        schreibe(scr, oben + y, mitte + dx, z, paar, fett)

    # Stamm
    for i in range(2):
        schreibe(scr, oben + HOEHE + 1 + i, mitte - 1, "###", STAMM)

    # Kerzen
    for i, (y, dx) in enumerate(kerzen):
        an = i < brennend
        kerze = KERZE_LINKS if dx < 0 else KERZE_RECHTS
        schreibe(scr, oben + y, mitte + dx, kerze, ROT, an)
        if an:
            flamme = random.choice(FLAMMEN)
            farbe = random.choice([GELB, GELB, GELB, WEISS])
            schreibe(scr, oben + y - 1, mitte + dx, flamme, farbe,
                     random.random() < 0.8)

    for i, zeile in enumerate(info):
        schreibe(scr, oben + HOEHE + 4 + i,
                 max(0, mitte - len(zeile) // 2), zeile, WEISS)
    scr.refresh()


def parse_datum(text: str):
    """Akzeptiert TT.MM.JJJJ, TT.MM. (aktuelles Jahr) oder JJJJ-MM-TT."""
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        tag_monat = dt.datetime.strptime(text.rstrip(".") + ".", "%d.%m.")
        return tag_monat.date().replace(year=dt.date.today().year)
    except ValueError:
        return None


def frage_datum(scr):
    """Fragt am unteren Fensterrand ein Datum ab. Leer = heute."""
    max_y, max_x = scr.getmaxyx()
    meldung = ""
    while True:
        frage = "Datum (TT.MM.JJJJ, leer = heute): "
        scr.move(max_y - 1, 0)
        scr.clrtoeol()
        if meldung:
            schreibe(scr, max_y - 2, 0, meldung, ROT, True)
        schreibe(scr, max_y - 1, 0, frage, WEISS, True)
        scr.refresh()

        scr.timeout(-1)
        curses.echo()
        curses.curs_set(1)
        try:
            eingabe = scr.getstr(max_y - 1, len(frage), 20)
            eingabe = eingabe.decode("utf-8", "ignore")
        except curses.error:
            eingabe = ""
        finally:
            curses.noecho()
            curses.curs_set(0)
            scr.timeout(FRAME_MS)

        if not eingabe.strip():
            return dt.date.today()
        datum = parse_datum(eingabe)
        if datum:
            return datum
        meldung = f"Ungültiges Datum: '{eingabe}'"


def hauptschleife(scr, heute, modus):
    curses.curs_set(0)
    init_farben()
    scr.timeout(FRAME_MS)
    info = ["d = Datum simulieren   q = Beenden"]

    while True:
        gesamt, brennend, _ = kerzen_status(heute, modus)
        zellen, kerzen = baue_baum(gesamt)

        while True:
            zeichne(scr, zellen, kerzen, brennend, info)
            taste = scr.getch()
            if taste in (ord("q"), ord("Q"), 27):
                return
            if taste in (ord("d"), ord("D")):
                heute = frage_datum(scr)
                break


def main():
    parser = argparse.ArgumentParser(description="Adventlicher Tannenbaum")
    parser.add_argument("--datum", type=dt.date.fromisoformat,
                        default=dt.date.today(),
                        help="Datum im Format JJJJ-MM-TT (Standard: heute)")
    parser.add_argument("--modus", choices=["tage", "sonntage"], default="tage",
                        help="'tage': jeden Adventstag eine Kerze mehr; "
                             "'sonntage': 4 Kerzen, je Adventssonntag eine")
    args = parser.parse_args()
    try:
        curses.wrapper(hauptschleife, args.datum, args.modus)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
