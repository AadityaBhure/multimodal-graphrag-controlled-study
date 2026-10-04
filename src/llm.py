"""Shared non-fatal Groq generation at temperature zero."""
from groq import Groq

from src.config import Settings, settings

TEXT_SYSTEM_PROMPT = """You are a research assistant answering questions about retrieval-augmented generation research papers.
Use ONLY the retrieved evidence supplied to you.
Do not invent paper names, methods, results, authors, or claims.
If the evidence is insufficient, state that clearly.
Whenever possible cite source paper IDs such as [P010]."""

ANSWER_INSTRUCTIONS = """Give a concise answer supported directly by the evidence. Cite paper IDs in the exact form [P010].
Distinguish the queried method from its variants, baselines, and experimental comparisons.
Do not transfer a variant's mechanism or an experimental observation to the base method.
Omit procedural details not explicitly supported by the retrieved text; state evidence limitations when necessary."""
ANSWER_INSTRUCTIONS += "\nIf evidence mentions a number of actions without naming each one, do not infer or invent that enumeration. Prefer a short prose explanation of the supported mechanisms."

GRAPH_SYSTEM_PROMPT = """You are a research assistant answering questions about retrieval-augmented generation research papers.
You have been given a retrieved knowledge subgraph together with supporting text from papers connected to that subgraph.
Use ONLY the supplied graph and text evidence.
Do not invent relationships or paper claims.
If the evidence is insufficient, state that clearly.
Whenever possible cite paper IDs such as [P011]."""

GROUNDING_RULES = """
Answer in one short paragraph. Include only mechanisms explicitly attributed to the named method.
When excerpts mix a method, variants, and experimental comparisons, omit variant-specific
implementation details instead of combining them into a single pipeline. A mention of a number
of actions does not establish what those actions are: never supply an unnamed action list.
Do not turn table captions or experimental outcomes into algorithm steps.
Use exact paper-ID citations such as [P010], not chunk IDs. State limitations of the supplied evidence."""
TEXT_SYSTEM_PROMPT += GROUNDING_RULES
GRAPH_SYSTEM_PROMPT += GROUNDING_RULES


class LLM:
    def __init__(self, config: Settings = settings):
        self.config = config

    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        if not self.config.groq_configured:
            return {"answer": "Generation disabled: GROQ_API_KEY is not configured.",
                    "status": "generation_disabled", "generation_error": None}
        try:
            with Groq(api_key=self.config.groq_api_key, timeout=60, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=self.config.groq_model, temperature=0,
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": user_prompt}])
            answer = response.choices[0].message.content
            if not answer:
                raise RuntimeError("Groq returned an empty answer")
            return {"answer": answer, "status": "ok", "generation_error": None}
        except Exception as exc:
            message = str(exc).replace(self.config.groq_api_key, "[REDACTED]")
            return {"answer": "Generation failed; retrieved evidence remains available.",
                    "status": "generation_error", "generation_error": message}
