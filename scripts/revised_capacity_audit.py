"""Revised static capacity audit under the probe-confirmed admission rule (no API, no generation).

Pre-dispatch requirement = local o200k_harmony content tokens + 128 overhead reserve <= 8000.
The 1,024 completion cap is not charged at admission (groq-admission-probe-v1: HTTP 200 for
prompt ~1,543 + max 7,000). Post-call bucket use is modelled separately as provider prompt tokens
(content + 102) + actual completion tokens, with observed completion sizes and a worst case.
Input: current_capacity_audit.json (contexts built by the frozen code; hash-identical to current code).
"""
from pathlib import Path
import csv, json, math, statistics, sys
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'documentation/rq1_repair'
LIMIT, RESERVE, MEASURED, CAP, REFILL_PER_S = 8000, 128, 102, 1024, 8000 / 60
OBSERVED_EXCESS_DEBIT = 427        # largest (header bucket debit - provider total) seen: probe, cap 7000 (historical max 326)

old = json.loads((D / 'current_capacity_audit.json').read_text(encoding='utf-8'))
probe = json.loads((D / 'provider_diagnostic/call_04_admission_probe.json').read_text(encoding='utf-8'))
hist = json.loads((D / 'provider_diagnostic.json').read_text(encoding='utf-8'))['historical_phase8_v2_reconciliation']
completions = [h['completion'] for h in hist] + [probe['usage']['completion_tokens']]
completion_obs = {'n': len(completions), 'min': min(completions), 'max': max(completions), 'median': statistics.median(completions)}
rows = []
for r in old['rows']:
    kind = 'keyword_extraction' if r['stage'] == 'keyword_extraction' else 'final_answer'
    dynamic = r['status'] != 'STATIC'
    if dynamic:
        content = r['reservation_current_upper_bound'] - 256 - CAP      # sound upper bound on content tokens
    else:
        content = r['local_content_tokens']
    pre = content + RESERVE
    prompt = content + MEASURED
    row = {'query_id': r['query_id'], 'stress': r['stress'], 'modality': r['modality'], 'method': r['method'], 'stage': kind,
           'status': 'DYNAMIC_NOT_YET_CONSTRUCTABLE_UPPER_BOUND' if dynamic else 'STATIC',
           'message_sha256': r.get('message_sha256'), 'context_sha256': r.get('context_sha256'),
           'local_content_tokens' if not dynamic else 'local_content_tokens_upper_bound': content,
           'overhead_reserve': RESERVE, 'pre_dispatch_requirement': pre, 'limit_tokens': LIMIT,
           'pass': pre <= LIMIT, 'headroom': LIMIT - pre, 'completion_cap_sent_unchanged': CAP,
           'provider_prompt_estimate': prompt,
           'post_call_debit_expected_median_completion': prompt + completion_obs['median'],
           'post_call_debit_worst_case_cap_plus_excess': prompt + CAP + OBSERVED_EXCESS_DEBIT,
           'refill_seconds_worst_case': round((prompt + CAP + OBSERVED_EXCESS_DEBIT) / REFILL_PER_S, 1)}
    rows.append(row)
stat = [r for r in rows if r['status'] == 'STATIC']; dyn = [r for r in rows if r['status'] != 'STATIC']
fin = [r for r in stat if r['stage'] == 'final_answer']
worst = max(stat, key=lambda r: r['pre_dispatch_requirement'])
summary = {
    'admission_rule': 'local content tokens + 128 <= 8000; completion cap (1,024) not charged at admission',
    'static_requests': len(stat), 'static_final_requests': len(fin), 'static_keyword_requests': len(stat) - len(fin),
    'static_requests_fitting': sum(r['pass'] for r in stat), 'static_requests_failing': sum(not r['pass'] for r in stat),
    'every_statically_constructable_request_fits': all(r['pass'] for r in stat),
    'max_pre_dispatch_requirement': worst['pre_dispatch_requirement'],
    'max_request': {k: worst[k] for k in ('method', 'query_id', 'stress', 'modality', 'stage')},
    'minimum_headroom': min(r['headroom'] for r in stat), 'headroom_p10_median': [sorted(r['headroom'] for r in stat)[len(stat) // 10], statistics.median(r['headroom'] for r in stat)],
    'dynamic_cm03_final_requests': len(dyn), 'dynamic_upper_bounds_fitting': sum(r['pass'] for r in dyn),
    'dynamic_upper_bounds_exceeding_8000': sum(not r['pass'] for r in dyn),
    'dynamic_max_upper_bound_requirement': max(r['pre_dispatch_requirement'] for r in dyn),
    'dynamic_note': 'CM-03 upper bounds are sound but loose; true size known only after keywords exist, and CM-03 is not cleared by this audit',
    'old_rule_failures_for_comparison': {'count_over_8000_old_rule': old['summary']['count_over_8000_current'], 'old_max_reservation': old['summary']['max_reservation_current']},
    'post_call_model': {'bucket_debit': 'provider prompt tokens (content+102) + actual completion tokens; headers showed up to +427 unexplained extra debit (cap 7000 probe), up to +326 with cap 1024',
                        'observed_completion_tokens': completion_obs,
                        'worst_case_debit_max': max(r['post_call_debit_worst_case_cap_plus_excess'] for r in stat),
                        'worst_case_refill_seconds_max': max(r['refill_seconds_worst_case'] for r in stat),
                        'start_spacing_seconds_in_dispatcher': 90,
                        'conclusion': 'the 90 s start spacing exceeds the worst-case refill time, so the bucket is full at every dispatch; per-response headers still gate the next call'},
    'daily_budget': {'tpd_limit': 200000, 'note': 'see PROVIDER_AND_CM01_DIAGNOSTIC_REPORT.md: about 0.57-0.60M provider tokens in total => about 3 days'},
}
(D / 'revised_capacity_audit.json').write_text(json.dumps({'audit_id': 'rq1-revised-capacity-audit-v1', 'source': 'current_capacity_audit.json', 'summary': summary, 'rows': rows}, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
cols = sorted({k for r in rows for k in r})
with (D / 'revised_capacity_audit.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
print(json.dumps(summary, indent=1))
