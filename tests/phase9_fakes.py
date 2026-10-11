"""Offline fakes for Phase 9 policy tests: no store, no model, no API."""
import json
from research.common.contracts import EvidenceItem, Provenance
from research.common.serialization import canonical_json
from research.baselines.config import BaselineOptions
from research.agentic.llm import DurableLLM
from research.agentic.tools import ToolCall
from research.evaluation.contracts import SystemInput


def evidence(source, paper, payload=None, score=0.):
    payload = payload or ({'paper_id': paper, 'title': 't%d' % paper, 'abstract': 'a%d' % paper, 'content': 't%d\n\na%d' % (paper, paper)} if source == 'text'
                          else {'paper_id': paper, 'title': 't%d' % paper, 'path': [], 'nodes': [{'node_id': paper, 'label': 't%d' % paper, 'node_type': 'paper'}]} if source == 'graph'
                          else {'paper_id': paper, 'publication_year': 2000 + paper})
    return EvidenceItem(evidence_id='%s:paper:%d' % (source, paper), source_type=source, canonical_id='stark:%d' % paper,
                        payload=canonical_json(payload), score=score,
                        provenance=(Provenance(dataset_version='fixture', source_id=str(paper), locator='fixture'),))


class FakeStore:
    manifest_hash = 'fixture'
    manifest = {'dataset_version': 'fixture'}


class FakeTools:
    """Deterministic per-source evidence; records every call (the 'frozen retrievers')."""
    fingerprint = 'fake-tools'

    def __init__(self, papers=None, empty=()):
        self.papers = papers or {'text': [1, 2], 'graph': [3], 'structured': [4]}
        self.empty = set(empty)
        self.calls = []

    def call(self, source, retrieval_query, entities=(), relations=(), structured_intent=None):
        self.calls.append({'source': source, 'query': retrieval_query, 'entities': list(entities), 'structured_intent': structured_intent})
        items = [] if source in self.empty else [evidence(source, p) for p in self.papers[source]]
        return ToolCall(source, retrieval_query, items, {'status': 'ok'}, 1.0, False)


class ScriptedTransport:
    """Pops scripted raw outputs by role: role is inferred from the system prompt's first words."""
    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.log = []

    @staticmethod
    def role(payload):
        s = payload['messages'][0]['content']
        if s.startswith('You answer a research-paper retrieval question'):
            return 'final'
        for key, start in (('agent', 'You are a retrieval controller. Do not answer'), ('ar01_controller', 'You are a multi-step retrieval controller'),
                           ('validator', 'You are an evidence-grounding validator'), ('commentor', 'You are a corrective retrieval critic'),
                           ('repair', 'Rewrite the supplied output')):
            if s.startswith(start):
                return key
        raise AssertionError('unknown role: ' + s[:40])

    def __call__(self, payload):
        role = self.role(payload); self.log.append(role)
        queue = self.script[role]
        raw = queue.pop(0) if len(queue) > 1 else queue[0]
        return raw, {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}, 'stop', {'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-remaining-tokens': '8000', 'x-ratelimit-remaining-requests': '999'}


def make_llm(tmp_path, script):
    transport = ScriptedTransport(script)
    clock = [1000.0]
    llm = DurableLLM(tmp_path, transport=transport, clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    return llm, transport


def request(question='Which papers mention graphs?', qid='q1', seed=42, overlay=None):
    return SystemInput(query_id=qid, question=question, seed=seed, overlay=overlay)


def answer(ids):
    return json.dumps({'answer_ids': ids, 'explanation': 'x'})


def agent(source, query='q', **kw):
    base = {'iteration': 1, 'source': source, 'retrieval_query': query, 'domain': None, 'entities': [], 'relations': [],
            'structured_intent': None, 'reason_code': 'textual', 'stop_reason': None}
    base.update(kw)
    return json.dumps(base)


def verdict(accept, error='none'):
    return json.dumps({'accept': accept, 'error_type': error, 'unsupported_claims': []})


def note(source='none'):
    return json.dumps({'feedback': 'try again', 'recommended_source': source, 'reason': 'r'})


def options():
    return BaselineOptions()
