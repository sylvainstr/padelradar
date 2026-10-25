import unittest
from datetime import date

from padelradar import creneau_ok

LUNDI = date(2026, 11, 2)
VENDREDI = date(2026, 10, 30)
SAMEDI = date(2026, 11, 14)


class CreneauTest(unittest.TestCase):
    # Titres réels relevés sur Ten'Up
    def test_semaine_18h_ou_plus(self):
        self.assertTrue(creneau_ok("TOURNOI HOMMES P50 18 H", VENDREDI, VENDREDI))
        self.assertTrue(creneau_ok("P100 MIXTE à 18H00", VENDREDI, VENDREDI))

    def test_semaine_avant_18h(self):
        self.assertFalse(creneau_ok("TOURNOI HOMMES P25 12H00", LUNDI, LUNDI))
        self.assertFalse(creneau_ok("P50 LUNDI MATIN", LUNDI, LUNDI))
        self.assertFalse(creneau_ok("P50H VENDREDI APRÈS-MIDI", VENDREDI, VENDREDI))
        self.assertFalse(creneau_ok("P25 APREM", LUNDI, LUNDI))
        self.assertFalse(creneau_ok("P100 MIXTE MERCREDI MATIN + P50 APRÈS-MIDI", LUNDI, LUNDI))

    def test_semaine_soir(self):
        self.assertTrue(creneau_ok("P25 SOIR", LUNDI, LUNDI))

    def test_semaine_horaire_inconnu(self):
        self.assertTrue(creneau_ok("P50", LUNDI, LUNDI))
        self.assertTrue(creneau_ok("P50H", LUNDI, LUNDI))

    def test_week_end_toujours(self):
        self.assertTrue(creneau_ok("P50H SAMEDI MATIN", SAMEDI, SAMEDI))
        self.assertTrue(creneau_ok("P25 MATIN", VENDREDI, date(2026, 10, 31)))


if __name__ == "__main__":
    unittest.main()
