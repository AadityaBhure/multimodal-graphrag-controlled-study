"""Versioned Phase 9 controller / critic prompts. Frozen before any Phase 9 validation outcome exists.

System intents are the exact wording of Phase 9 addendum §4 (AR-03) and §2.3 (AR-01 controller); schema
descriptions and the structured-tool grammar are appended as tool-interface documentation (identical for
every call, no benchmark content). Any edit changes PROMPT_VERSION_HASH and therefore every experiment ID.
"""
import json
from research.common.serialization import content_hash

PROMPT_VERSION = 'phase9-prompts-v1'

STRUCTURED_GRAMMAR = (
    'The structured tool accepts ONLY conjunctive clauses in this phrasing (joined by "and"): '
    '"the recorded publication year is <at least|at most|greater than|less than|before|after|exactly> <integer>"; '
    '"the recorded citation count is ... <integer>"; "the recorded paper rank is ... <integer>"; '
    '"the recorded publication date is <before|after|exactly> <YYYY-MM-DD>"; '
    '"the recorded normalized venue namespace is <journal|conference_series|conference_instance|original_venue>"; '
    '"the recorded document type is \\"<exact string>\\"" (same for venue name / venue id). '
    'Anything else returns no structured rows.')

# ---------------------------------------------------------------- AR-01 multi-step controller
AR01_CONTROLLER_SYSTEM = (
    'You are a multi-step retrieval controller. Using only the original query and the retrieved evidence shown, decide '
    'whether the evidence is already sufficient to answer the query. If it is not, write the next retrieval subquery. '
    'Do not answer the query. Do not invent evidence. Return JSON only: '
    '{"sufficient": boolean, "next_subquery": string, "reason": string}. '
    'When sufficient is true, next_subquery must be an empty string.')

# ---------------------------------------------------------------- AR-03
AGENT_SCHEMA = (
    'AgentAction JSON schema (exactly these keys): {"iteration": int, "source": "text"|"graph"|"structured"|"stop", '
    '"retrieval_query": string, "domain": string|null, "entities": [string], "relations": [string], '
    '"structured_intent": string|null, "reason_code": "textual"|"relational"|"numeric"|"hybrid"|"correction", '
    '"stop_reason": string|null}. Use source "stop" only when no further retrieval can help; give stop_reason then. '
    'Sources: text = dense retrieval over paper title+abstract using retrieval_query; graph = knowledge-graph retrieval '
    '(authors, institutions, citations, fields) using retrieval_query plus entities; structured = read-only metadata '
    'lookup using structured_intent. ' + STRUCTURED_GRAMMAR)

AGENT_SYSTEM = (
    "You are a retrieval controller. Do not answer the user's question. Choose exactly one retrieval action or STOP using "
    'only the query, previous feedback, and currently retrieved evidence. Prefer the smallest next action that can resolve '
    'missing evidence. Do not invent evidence, gold labels, entities, relations, SQL, or facts. Never repeat an action that '
    'previously returned no new evidence unless the feedback explicitly requires it. Return JSON only matching AgentAction. '
    + AGENT_SCHEMA)

VALIDATOR_SYSTEM = (
    'You are an evidence-grounding validator. You do not have access to benchmark gold answers. Decide only whether the '
    'candidate answer fully addresses the query and every material claim/constraint is supported by the retrieved evidence. '
    'Reject answers that use the wrong entity/relation/source, rely on missing evidence, contain unsupported claims, or depend '
    'on a structured-query failure. Return JSON only: {"accept": boolean, "error_type": "none"|"wrong_source"|"wrong_entity"|'
    '"wrong_relation"|"insufficient_evidence"|"unsupported_answer"|"structured_query_error", "unsupported_claims": [string]}. '
    'Use error_type "none" if and only if accept is true.')

COMMENTOR_SYSTEM = (
    'You are a corrective retrieval critic. Using only the query, last AgentAction, and validator result, provide concise guidance '
    'for the next retrieval action. Do not answer the query and do not introduce new factual evidence. Return JSON only: '
    '{"feedback": string, "recommended_source": "text"|"graph"|"structured"|"none", "reason": string}.')

REPAIR_SYSTEM = (
    'Rewrite the supplied output into valid JSON matching the required schema exactly. Preserve its intended decision; '
    'do not add factual content. Return JSON only.')

SCHEMAS = {
    'ar01_controller': '{"sufficient": boolean, "next_subquery": string, "reason": string}',
    'agent': AGENT_SCHEMA,
    'validator': '{"accept": boolean, "error_type": "none"|"wrong_source"|"wrong_entity"|"wrong_relation"|"insufficient_evidence"|"unsupported_answer"|"structured_query_error", "unsupported_claims": [string]}',
    'commentor': '{"feedback": string, "recommended_source": "text"|"graph"|"structured"|"none", "reason": string}',
}
CAPS = {'ar01_controller': 128, 'agent': 256, 'validator': 256, 'commentor': 128, 'repair': 128}
FORCED_FEEDBACK = 'Previous action produced no new evidence. Choose a different source/action.'


def repair_user(kind, malformed):
    return 'REQUIRED SCHEMA\n' + SCHEMAS[kind] + '\n\nOUTPUT TO REWRITE\n' + malformed


def agent_user(question, feedback, iteration, queried, context):
    return ('QUERY\n' + question + '\n\nITERATION ' + str(iteration) + ' of 4. Sources already queried: ' +
            (', '.join(queried) if queried else 'none') + '\n\nPREVIOUS FEEDBACK\n' + (feedback or 'none') +
            '\n\nEVIDENCE\n' + context)


def validator_user(question, candidate, context):
    return 'QUERY\n' + question + '\n\nCANDIDATE ANSWER\n' + candidate + '\n\nEVIDENCE\n' + context


def commentor_user(question, action, validator):
    return ('QUERY\n' + question + '\n\nLAST ACTION\n' + json.dumps(action, sort_keys=True, ensure_ascii=False) +
            '\n\nVALIDATOR RESULT\n' + json.dumps(validator, sort_keys=True, ensure_ascii=False))


def controller_user(question, context, step):
    return 'QUERY\n' + question + '\n\nRETRIEVALS COMPLETED: ' + str(step) + ' of 3\n\nEVIDENCE\n' + context


PROMPT_VERSION_HASH = content_hash({'version': PROMPT_VERSION, 'ar01': AR01_CONTROLLER_SYSTEM, 'agent': AGENT_SYSTEM,
                                    'validator': VALIDATOR_SYSTEM, 'commentor': COMMENTOR_SYSTEM, 'repair': REPAIR_SYSTEM,
                                    'caps': CAPS, 'forced': FORCED_FEEDBACK, 'schemas': SCHEMAS})
