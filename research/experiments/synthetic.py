"""Deterministic fixture system only. It performs no retrieval or LLM calls."""
from research.evaluation.contracts import SystemOutput, Observation


class SyntheticSystem:
    system_id = 'synthetic-fixture'
    version = '1'
    fingerprint = 'fixed-empty-answer-no-tools-v1'

    def execute(self, request):
        # The fixed response is independent of gold, source, modality and hop labels.
        return SystemOutput(answer='[]', answer_ids=(), ranked_paper_ids=(), evidence=(), context='',
                            retained_evidence_ids=(), observation=Observation(
                                retrieval_calls=0, tool_calls=0, llm_calls=0))


class ScriptedSyntheticSystem:
    """Prewritten fixture outputs. The response file hash is part of run identity."""
    system_id = 'synthetic-scripted'
    version = '1'

    def __init__(self, path):
        from research.evaluation.benchmark import read_json, digest
        self.responses = {key: SystemOutput.model_validate(value) for key, value in read_json(path).items()}
        self.fingerprint = digest(path)

    def execute(self, request):
        return self.responses[request.query_id]
