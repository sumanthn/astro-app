from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .enums import Planet, Sign, Nakshatra, Dignity


class BirthData(BaseModel):
    datetime_utc: datetime
    latitude: float
    longitude: float
    timezone: str
    place: str


class PlanetState(BaseModel):
    planet: Planet
    longitude: float
    sign: Sign
    degree_in_sign: float
    house: int
    nakshatra: Nakshatra
    pada: int
    retrograde: bool
    combust: bool
    dignity: Dignity
    speed: float
    vargottama: bool = False  # set later when D9 is computed


class House(BaseModel):
    number: int
    sign: Sign
    lord: Planet
    occupants: list[Planet] = []
    aspected_by: list[Planet] = []


class Chart(BaseModel):
    variant: str  # "D1", "D9", "D10"
    birth: BirthData
    ascendant_sign: Sign
    ascendant_degree: float
    planets: dict[Planet, PlanetState]
    houses: dict[int, House]

    def lord_of(self, house: int) -> Planet:
        return self.houses[house].lord

    def planets_in_house(self, house: int) -> list[Planet]:
        return self.houses[house].occupants

    def planets_in_sign(self, sign: Sign) -> list[Planet]:
        return [ps.planet for ps in self.planets.values() if ps.sign == sign]
