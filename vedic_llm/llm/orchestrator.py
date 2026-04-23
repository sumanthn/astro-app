"""Analysis orchestrator — chains the 4-stage analysis pipeline."""
from datetime import datetime, timezone
from typing import Optional
from vedic_llm.models.chart import BirthData
from vedic_llm.compute.chart import build_d1_chart, build_d9_chart, build_d10_chart
from vedic_llm.compute.aspects import populate_house_aspects
from vedic_llm.extract.natal_facts import extract_natal_dossier
from vedic_llm.extract.dasha_facts import extract_dasha_dossier
from vedic_llm.extract.transit_facts import extract_transit_dossier
from vedic_llm.prompts.natal import build_natal_prompt
from vedic_llm.prompts.dasha import build_dasha_prompt
from vedic_llm.prompts.transit import build_transit_prompt
from vedic_llm.prompts.synthesis import build_synthesis_prompt
from vedic_llm.llm.client import ClaudeClient
import json


class AnalysisOrchestrator:
    def __init__(self, client: ClaudeClient):
        self.client = client

    def run_full_analysis(
        self,
        birth: BirthData,
        at: Optional[datetime] = None,
        topics: Optional[list[str]] = None,
    ) -> dict:
        at = at or datetime.now(timezone.utc)

        # Compute layer
        d1 = build_d1_chart(birth)
        populate_house_aspects(d1)
        d9 = build_d9_chart(d1)
        d10 = build_d10_chart(d1)

        # Mark vargottama
        for planet in d1.planets:
            if planet in d9.planets:
                if d1.planets[planet].sign == d9.planets[planet].sign:
                    d1.planets[planet].vargottama = True

        # Extract dossiers
        natal_dossier = extract_natal_dossier(d1, d9, d10)
        dasha_dossier = extract_dasha_dossier(birth, d1, at)
        transit_dossier = extract_transit_dossier(d1, at)

        # Stage 1: Natal
        natal_sys, natal_user = build_natal_prompt(natal_dossier)
        natal_result = self.client.analyze_json(natal_sys, natal_user)

        # Stage 2: Dasha
        dasha_sys, dasha_user = build_dasha_prompt(natal_result, dasha_dossier)
        dasha_result = self.client.analyze_json(dasha_sys, dasha_user)

        # Stage 3: Transit
        transit_sys, transit_user = build_transit_prompt(natal_result, dasha_result, transit_dossier)
        transit_result = self.client.analyze_json(transit_sys, transit_user)

        # Stage 4: Synthesis
        synth_sys, synth_user = build_synthesis_prompt(natal_result, dasha_result, transit_result)
        synthesis = self.client.analyze_json(synth_sys, synth_user)

        return {
            "layers": {
                "natal": natal_result,
                "dasha": dasha_result,
                "transits": transit_result,
            },
            "synthesis": synthesis,
            "dossiers": {
                "natal": natal_dossier.model_dump(),
                "dasha": dasha_dossier.model_dump(),
                "transits": transit_dossier.model_dump(),
            },
            "token_usage": self.client.token_usage(),
        }

    def run_dossier_only(self, birth: BirthData, at: Optional[datetime] = None) -> dict:
        """Just compute dossiers without LLM calls — for debugging."""
        at = at or datetime.now(timezone.utc)
        d1 = build_d1_chart(birth)
        populate_house_aspects(d1)
        d9 = build_d9_chart(d1)
        d10 = build_d10_chart(d1)

        for planet in d1.planets:
            if planet in d9.planets:
                if d1.planets[planet].sign == d9.planets[planet].sign:
                    d1.planets[planet].vargottama = True

        natal_dossier = extract_natal_dossier(d1, d9, d10)
        dasha_dossier = extract_dasha_dossier(birth, d1, at)
        transit_dossier = extract_transit_dossier(d1, at)

        return {
            "natal": natal_dossier.model_dump(),
            "dasha": dasha_dossier.model_dump(),
            "transits": transit_dossier.model_dump(),
        }
