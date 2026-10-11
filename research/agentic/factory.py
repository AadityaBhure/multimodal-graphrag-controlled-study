"""Construction of the five RQ3 policies from frozen artifacts (partition, AR-01 model, AR-02 calibration)."""
import json
from pathlib import Path
from research.common.serialization import content_hash
from research.evaluation.benchmark import digest

ROOT = Path(__file__).resolve().parents[2]
METHODS = ('AR-B0', 'AR-B1', 'AR-01', 'AR-02', 'AR-03')
PHASE9 = ROOT / 'documentation/phase9'
ARTIFACTS = ROOT / 'artifacts/phase9'


def load_calibration(path=None):
    path = Path(path or PHASE9 / 'calibration/ar02_calibration.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    return data, digest(path)


def build_policy(method, store, options, tools, llm, config_hash='unbound', ar01_model_dir=None, ar02_model_dir=None, calibration_path=None):
    from research.agentic.policies import AlwaysAll, RuleRouted
    if method == 'AR-B0':
        return AlwaysAll(method, store, options, tools, llm, config_hash)
    if method == 'AR-B1':
        return RuleRouted(method, store, options, tools, llm, config_hash)
    if method == 'AR-01':
        from research.agentic.adaptive_rag import AdaptiveRAG
        from research.agentic.ar01_model import T5Router
        return AdaptiveRAG(method, store, options, tools, llm, config_hash, classifier=T5Router(ar01_model_dir or ARTIFACTS / 'ar01/best'))
    if method == 'AR-02':
        from research.agentic.crag import CorrectiveRAG, CrossEncoderEvaluator, Platt
        cal, cal_hash = load_calibration(calibration_path)
        return CorrectiveRAG(method, store, options, tools, llm, config_hash,
                             evaluator=CrossEncoderEvaluator(ar02_model_dir or ARTIFACTS / 'models/ms-marco-MiniLM-L-6-v2'),
                             platt=Platt(cal['platt']['coef'], cal['platt']['intercept']), lower=cal['thresholds']['lower'],
                             upper=cal['thresholds']['upper'], calibration_hash=cal_hash)
    if method == 'AR-03':
        from research.agentic.agent_g import AgentG
        return AgentG(method, store, options, tools, llm, config_hash)
    raise ValueError('Unknown RQ3 method')
