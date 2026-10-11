"""AR-03 AGENT-G-inspired multi-source agent + critic (Phase 1D §6.4 + addendum §4)."""
from research.agentic.policies import Policy
from research.agentic.rule_router import next_unqueried, normalize
from research.agentic.controllers import structured_call
from research.agentic.prompts import (AGENT_SYSTEM, VALIDATOR_SYSTEM, COMMENTOR_SYSTEM, agent_user, validator_user,
                                      commentor_user, FORCED_FEEDBACK, PROMPT_VERSION_HASH)
from research.agentic.tools import fixed_context, generate_final
from research.agentic.evidence import canonical_paper

T = 4


def normalized_action(a):
    return (a['source'], normalize(a['retrieval_query'] or ''), tuple(sorted(normalize(e) for e in a['entities'])),
            tuple(sorted(normalize(r) for r in a['relations'])), normalize(a['structured_intent'] or ''))


class AgentG(Policy):
    def fingerprint_parts(self):
        return {'prompts': PROMPT_VERSION_HASH, 'T': T}

    def run(self, request, memory, trace):
        q = request.question
        feedback, prev_norm, same_count = None, None, 0
        for t in range(1, T + 1):
            # ---- Agent (sees query, previous feedback, fixed serialised accumulated evidence)
            context = fixed_context(memory.ordered(), tuple(trace.queried), self.store, request.overlay, self.options)[0]
            action, events, results = structured_call(self.llm, 'agent', AGENT_SYSTEM,
                                                      agent_user(q, feedback, t, trace.queried, context), request.seed)
            trace.events.extend(events)
            trace.llm(results, t)
            if action is None:
                source = next_unqueried(q, trace.queried)
                trace.fallbacks.append({'type': 'agent_schema_repair_failed', 'iteration': t, 'router_source': source})
                action = {'iteration': t, 'source': source or 'stop', 'retrieval_query': q, 'domain': None, 'entities': [],
                          'relations': [], 'structured_intent': q if source == 'structured' else None, 'reason_code': 'correction',
                          'stop_reason': None if source else 'router_exhausted', 'schema_repair_failed': True}
            else:
                if action['iteration'] != t:
                    trace.events.append({'kind': 'agent_iteration_mismatch', 'declared': action['iteration'], 'actual': t})
                action = {**action, 'iteration': t}
            trace.events.append({'kind': 'agent_action', 'iteration': t, 'action': action})
            if action['source'] == 'stop':
                trace.stop_reason = 'agent_stop:' + (action.get('stop_reason') or 'unspecified')
                return {'kind': 'generate'}                     # Phase 1D: break and generate from evidence_memory
            # ---- exactly one retrieval tool
            _, new = self.retrieve(request, memory, trace, t, action['source'], action['retrieval_query'],
                                   entities=action['entities'], relations=action['relations'],
                                   structured_intent=action['structured_intent'], reason=action['reason_code'])
            norm = normalized_action(action)
            same_count = same_count + 1 if (norm == prev_norm and not new) else 0
            prev_norm = norm
            # ---- candidate answer (shared generator, fixed context)
            pack = fixed_context(memory.ordered(), tuple(trace.queried), self.store, request.overlay, self.options)
            context, retained, _, items, _ = pack
            allowed = [canonical_paper(e) for e in items if e.evidence_id in set(retained)]
            raw, ids, result, perr = generate_final(self.llm, q, context, allowed, request.seed)
            trace.llm([result], t)
            trace.events.append({'kind': 'candidate', 'iteration': t, 'answer_ids': list(ids) if ids is not None else None, 'parse_error': perr})
            # ---- validator
            if perr:
                verdict = {'accept': False, 'error_type': 'unsupported_answer',
                           'unsupported_claims': ['candidate failed the grounded-answer parser']}
                trace.events.append({'kind': 'validator_skipped', 'iteration': t, 'reason': 'candidate_unparseable'})
            else:
                verdict, events, results = structured_call(self.llm, 'validator', VALIDATOR_SYSTEM, validator_user(q, raw, context), request.seed)
                trace.events.extend(events)
                trace.llm(results, t)
                if verdict is None:
                    trace.fallbacks.append({'type': 'validator_schema_failure', 'iteration': t})
                    verdict = {'accept': False, 'error_type': 'insufficient_evidence', 'unsupported_claims': [], 'validator_schema_failure': True}
            trace.events.append({'kind': 'validator', 'iteration': t, 'verdict': verdict})
            if verdict['accept']:
                trace.stop_reason = 'validator_accepted'
                trace.extra['accepted_iteration'] = t
                return {'kind': 'provided', 'raw': raw, 'ids': ids, 'context_pack': pack}
            # ---- loop guard, terminal iteration, commentor
            if same_count >= 2:
                trace.stop_reason = 'loop_guard_insufficient_evidence'
                return {'kind': 'insufficient'}
            if t == T:
                trace.stop_reason = 'max_iterations_rejected'
                return {'kind': 'insufficient'}
            if same_count == 1:
                feedback = FORCED_FEEDBACK
                trace.events.append({'kind': 'forced_feedback', 'iteration': t})
                continue
            clean_action = {k: v for k, v in action.items() if k != 'schema_repair_failed'}
            clean_verdict = {k: v for k, v in verdict.items() if k != 'validator_schema_failure'}
            note, events, results = structured_call(self.llm, 'commentor', COMMENTOR_SYSTEM, commentor_user(q, clean_action, clean_verdict), request.seed)
            trace.events.extend(events)
            trace.llm(results, t)
            if note is None:
                trace.fallbacks.append({'type': 'commentor_schema_failure', 'iteration': t})
                feedback = FORCED_FEEDBACK
            else:
                feedback = note['feedback'] + (' Recommended source: ' + note['recommended_source'] if note['recommended_source'] != 'none' else '')
                trace.events.append({'kind': 'commentor', 'iteration': t, 'note': note})
        trace.stop_reason = 'max_iterations_rejected'
        return {'kind': 'insufficient'}
