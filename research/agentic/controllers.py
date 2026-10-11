"""Strict JSON parsing/validation of controller and critic outputs, with the single allowed schema repair.

No heuristic extraction: output that is not valid JSON of the exact schema is a failure (after one repair call).
"""
import json, re
from research.agentic.prompts import REPAIR_SYSTEM, CAPS, repair_user

SOURCES = ('text', 'graph', 'structured')
REASON_CODES = ('textual', 'relational', 'numeric', 'hybrid', 'correction')
ERROR_TYPES = ('none', 'wrong_source', 'wrong_entity', 'wrong_relation', 'insufficient_evidence', 'unsupported_answer', 'structured_query_error')


def _json(raw):
    clean = (raw or '').strip()
    if clean.startswith('```'):
        clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', clean)
    value = json.loads(clean)
    if not isinstance(value, dict):
        raise ValueError('not an object')
    return value


def _strs(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def validate_ar01_controller(o):
    if set(o) != {'sufficient', 'next_subquery', 'reason'} or type(o['sufficient']) is not bool or not isinstance(o['next_subquery'], str) or not isinstance(o['reason'], str):
        raise ValueError('ar01 controller schema')
    if not o['sufficient'] and not o['next_subquery'].strip():
        raise ValueError('missing next_subquery')
    return o


def validate_agent(o):
    keys = {'iteration', 'source', 'retrieval_query', 'domain', 'entities', 'relations', 'structured_intent', 'reason_code', 'stop_reason'}
    if set(o) != keys:
        raise ValueError('agent keys')
    if type(o['iteration']) is not int or o['source'] not in SOURCES + ('stop',) or o['reason_code'] not in REASON_CODES:
        raise ValueError('agent enums')
    if not isinstance(o['retrieval_query'], str) or not _strs(o['entities']) or not _strs(o['relations']):
        raise ValueError('agent types')
    for k in ('domain', 'structured_intent', 'stop_reason'):
        if o[k] is not None and not isinstance(o[k], str):
            raise ValueError('agent nullable')
    if o['source'] == 'structured' and not (o['structured_intent'] or '').strip():
        raise ValueError('structured action needs structured_intent')
    if o['source'] in ('text', 'graph') and not o['retrieval_query'].strip():
        raise ValueError('retrieval action needs retrieval_query')
    return o


def validate_validator(o):
    if set(o) != {'accept', 'error_type', 'unsupported_claims'} or type(o['accept']) is not bool or o['error_type'] not in ERROR_TYPES or not _strs(o['unsupported_claims']):
        raise ValueError('validator schema')
    return o


def validate_commentor(o):
    if set(o) != {'feedback', 'recommended_source', 'reason'} or not isinstance(o['feedback'], str) or o['recommended_source'] not in SOURCES + ('none',) or not isinstance(o['reason'], str):
        raise ValueError('commentor schema')
    return o


VALIDATORS = {'ar01_controller': validate_ar01_controller, 'agent': validate_agent, 'validator': validate_validator, 'commentor': validate_commentor}


def structured_call(llm, kind, system, user, seed):
    """One controller call plus at most one deterministic repair. Returns (object|None, events, results)."""
    cap = CAPS[kind]; events, results = [], []
    first = llm.chat(kind, system, user, cap, seed); results.append(first)
    ev = {'kind': kind, 'stage': first.stage_id, 'finish_reason': first.finish_reason, 'raw': first.raw, 'reused': first.reused}
    try:
        obj = VALIDATORS[kind](_json(first.raw)); ev['valid'] = True; events.append(ev)
        return obj, events, results
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        ev.update(valid=False, error=type(exc).__name__ + ':' + str(exc)[:80]); events.append(ev)
    rep = llm.chat('repair', REPAIR_SYSTEM, repair_user(kind, first.raw or ''), CAPS['repair'], seed); results.append(rep)
    rev = {'kind': kind + '_repair', 'stage': rep.stage_id, 'finish_reason': rep.finish_reason, 'raw': rep.raw, 'reused': rep.reused}
    try:
        obj = VALIDATORS[kind](_json(rep.raw)); rev['valid'] = True; events.append(rev)
        return obj, events, results
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        rev.update(valid=False, error=type(exc).__name__ + ':' + str(exc)[:80], schema_repair_failed=True); events.append(rev)
        return None, events, results
