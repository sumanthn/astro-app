"""Pydantic v2 models for LLM-ready fact dossiers.

These models structure all computed Vedic astrology data into flat,
serialisable forms that are easy for an LLM to consume and reason about.
"""

from pydantic import BaseModel
from typing import Optional


class PlanetFacts(BaseModel):
    planet: str
    sign: str
    degree: str  # formatted "18°42'"
    house: int
    nakshatra: str
    pada: int
    dignity: str
    retrograde: bool
    combust: bool
    vargottama: bool
    aspects_cast_on_houses: list[int]
    conjunctions: list[str]  # other planets in same house
    rules_houses: list[int]  # houses this planet lords
    functional_nature: str  # "yogakaraka", "benefic", "malefic", "neutral"
    d9_sign: str
    d9_dignity: str
    d9_house_from_d9_lagna: int
    d10_sign: str
    d10_house: int


class HouseFacts(BaseModel):
    number: int
    sign: str
    lord: str
    lord_sign: str
    lord_house: int
    lord_dignity: str
    lord_is_combust: bool
    lord_is_retrograde: bool
    occupants: list[str]
    aspected_by: list[str]
    is_hemmed_by_malefics: bool
    is_hemmed_by_benefics: bool
    karaka: str  # natural significator of the house
    karaka_state: str  # "strong"/"afflicted"/"neutral"


class NatalDossier(BaseModel):
    birth: dict
    ascendant: dict
    planets: dict[str, PlanetFacts]
    houses: dict[int, HouseFacts]
    yogas: list[dict]
    afflictions: list[dict]
    vargottama_planets: list[str]
    atmakaraka: str
    amatyakaraka: str
    functional_benefics: list[str]
    functional_malefics: list[str]
    d9_summary: dict


class DashaDossier(BaseModel):
    current_md: dict
    current_ad: dict
    current_pd: dict
    md_ad_relationship: str
    ad_pd_relationship: str
    doubly_activated_houses: list[int]
    upcoming_transitions: list[dict]


class TransitDossier(BaseModel):
    timestamp: str
    transit_positions: dict[str, dict]
    transit_overlays: list[dict]
    sade_sati: dict
    jupiter_from_moon: int
    active_natal_houses: list[int]
