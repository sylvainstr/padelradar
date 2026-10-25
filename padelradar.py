"""PadelRadar : alerte ntfy dès qu'un nouveau tournoi P25/P50 Hommes sort sur Ten'Up."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

SEEN_FILE = Path(__file__).with_name("seen.json")
BASE = "https://tenup.fft.fr"
# Cépet (31620), rayon 70 km (Toulouse, Montauban, Albi), Double Messieurs Senior, P25 + P50
SEARCH = (
    "/recherche/tournois/resultats?searchType=ville&pratique=PADEL&ville=C%C3%A9pet"
    "&lat=43.742306&lng=1.432835&distance=70&dateDebut={debut}&dateFin={fin}"
    "&utiliserMesDonnees=false&type=P&naturesEpreuves=DM++&typesEpreuves=P25++"
    "&typesEpreuves=P50++&categoriesAge=200&sort=DISTANCE&page={page}"
)
HOUR = re.compile(r"(?<![P\d])(\d{1,2})\s*H")
DAYTIME = re.compile(r"MATIN|APR[EÈ]S[- ]?MIDI|APREM|\bMIDI\b")


def creneau_ok(title, start, end):
    """Week-end : toujours. Semaine : à partir de 18h, ou horaire inconnu (mieux vaut une alerte de trop)."""
    if any((start + timedelta(days=d)).weekday() >= 5 for d in range((end - start).days + 1)):
        return True
    title = title.upper()
    hour = HOUR.search(title)
    if hour:
        return int(hour.group(1)) >= 18
    if "SOIR" in title or "NOCTURNE" in title:
        return True
    return not DAYTIME.search(title)


def fetch_tournaments():
    from playwright.sync_api import sync_playwright

    debut = date.today()
    fin = debut + timedelta(days=180)
    tournaments = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="fr-FR")
        n, read, total = 1, 0, None
        while total is None or read < total:
            page.goto(BASE + SEARCH.format(debut=debut, fin=fin, page=n))
            # Laisse le temps à la file d'attente Queue-it de rediriger vers les résultats
            counter = page.get_by_text(re.compile(r"^\d+ résultats?$")).first
            counter.wait_for(timeout=120_000)
            total = int(counter.inner_text().split()[0])
            rows = page.eval_on_selector_all(
                "article",
                """els => els.map(a => {
                    const link = a.querySelector('a[href^="/tournoi/"]');
                    return {href: link.getAttribute('href'), title: link.innerText.trim(), text: a.innerText};
                })""",
            )
            if not rows:
                break
            for row in rows:
                lines = [l.strip() for l in row["text"].split("\n") if l.strip()]
                start, end = re.search(r"(\d\d/\d\d/\d{4}) - (\d\d/\d\d/\d{4})", row["text"]).groups()
                tournaments[row["href"].rsplit("/", 1)[1]] = {
                    "title": row["title"],
                    "ville": lines[1],
                    "club": lines[2],
                    "distance": next((l for l in lines if l.endswith("km")), ""),
                    "start": datetime.strptime(start, "%d/%m/%Y").date(),
                    "end": datetime.strptime(end, "%d/%m/%Y").date(),
                    "url": BASE + row["href"],
                }
            read += len(rows)
            n += 1
        browser.close()
    return tournaments


def notify(topic, t):
    jours = t["start"].strftime("%d/%m/%Y")
    if t["end"] != t["start"]:
        jours += " → " + t["end"].strftime("%d/%m/%Y")
    params = urllib.parse.urlencode({"title": t["title"], "click": t["url"], "tags": "tennis"})
    message = f"{jours}\n{t['club']} ({t['ville']}, {t['distance']})"
    urllib.request.urlopen(f"https://ntfy.sh/{topic}?{params}", data=message.encode())


def main():
    topic = os.environ["NTFY_TOPIC"]
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else None
    tournaments = fetch_tournaments()
    if not tournaments:
        raise SystemExit("Aucun tournoi récupéré : Ten'Up a peut-être bloqué la requête.")
    if seen is None:
        print(f"Premier passage : {len(tournaments)} tournois enregistrés, sans alerte.")
    else:
        for tid, t in tournaments.items():
            if tid not in seen and creneau_ok(t["title"], t["start"], t["end"]):
                notify(topic, t)
                print(f"Alerte : {t['title']} - {t['club']} ({t['start']})")
    SEEN_FILE.write_text(json.dumps(sorted((seen or set()) | set(tournaments)), indent=0) + "\n")
    print(f"{len(tournaments)} tournois lus.")


if __name__ == "__main__":
    main()
