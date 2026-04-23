from enum import Enum


class Planet(str, Enum):
    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"


class Sign(int, Enum):
    ARIES = 1
    TAURUS = 2
    GEMINI = 3
    CANCER = 4
    LEO = 5
    VIRGO = 6
    LIBRA = 7
    SCORPIO = 8
    SAGITTARIUS = 9
    CAPRICORN = 10
    AQUARIUS = 11
    PISCES = 12


class Nakshatra(int, Enum):
    ASHWINI = 1
    BHARANI = 2
    KRITTIKA = 3
    ROHINI = 4
    MRIGASHIRA = 5
    ARDRA = 6
    PUNARVASU = 7
    PUSHYA = 8
    ASHLESHA = 9
    MAGHA = 10
    PURVA_PHALGUNI = 11
    UTTARA_PHALGUNI = 12
    HASTA = 13
    CHITRA = 14
    SWATI = 15
    VISHAKHA = 16
    ANURADHA = 17
    JYESHTHA = 18
    MULA = 19
    PURVASHADHA = 20
    UTTARASHADHA = 21
    SHRAVANA = 22
    DHANISHTA = 23
    SHATABHISHA = 24
    PURVA_BHADRAPADA = 25
    UTTARA_BHADRAPADA = 26
    REVATI = 27

    @property
    def lord(self) -> Planet:
        _lords = {
            # Ketu lords
            Nakshatra.ASHWINI: Planet.KETU,
            Nakshatra.MAGHA: Planet.KETU,
            Nakshatra.MULA: Planet.KETU,
            # Venus lords
            Nakshatra.BHARANI: Planet.VENUS,
            Nakshatra.PURVA_PHALGUNI: Planet.VENUS,
            Nakshatra.PURVASHADHA: Planet.VENUS,
            # Sun lords
            Nakshatra.KRITTIKA: Planet.SUN,
            Nakshatra.UTTARA_PHALGUNI: Planet.SUN,
            Nakshatra.UTTARASHADHA: Planet.SUN,
            # Moon lords
            Nakshatra.ROHINI: Planet.MOON,
            Nakshatra.HASTA: Planet.MOON,
            Nakshatra.SHRAVANA: Planet.MOON,
            # Mars lords
            Nakshatra.MRIGASHIRA: Planet.MARS,
            Nakshatra.CHITRA: Planet.MARS,
            Nakshatra.DHANISHTA: Planet.MARS,
            # Rahu lords
            Nakshatra.ARDRA: Planet.RAHU,
            Nakshatra.SWATI: Planet.RAHU,
            Nakshatra.SHATABHISHA: Planet.RAHU,
            # Jupiter lords
            Nakshatra.PUNARVASU: Planet.JUPITER,
            Nakshatra.VISHAKHA: Planet.JUPITER,
            Nakshatra.PURVA_BHADRAPADA: Planet.JUPITER,
            # Saturn lords
            Nakshatra.PUSHYA: Planet.SATURN,
            Nakshatra.ANURADHA: Planet.SATURN,
            Nakshatra.UTTARA_BHADRAPADA: Planet.SATURN,
            # Mercury lords
            Nakshatra.ASHLESHA: Planet.MERCURY,
            Nakshatra.JYESHTHA: Planet.MERCURY,
            Nakshatra.REVATI: Planet.MERCURY,
        }
        return _lords[self]


class Dignity(str, Enum):
    EXALTED = "Exalted"
    MOOLATRIKONA = "Moolatrikona"
    OWN = "Own"
    GREAT_FRIEND = "Great Friend"
    FRIEND = "Friend"
    NEUTRAL = "Neutral"
    ENEMY = "Enemy"
    GREAT_ENEMY = "Great Enemy"
    DEBILITATED = "Debilitated"


class HouseType(str, Enum):
    KENDRA = "Kendra"
    TRIKONA = "Trikona"
    DUSTHANA = "Dusthana"
    UPACHAYA = "Upachaya"
    MARAKA = "Maraka"
    NEUTRAL = "Neutral"
