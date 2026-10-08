"""Phase 6 bounded development/validation execution. Four API calls maximum per invocation."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.experiments.config import load_runner_config
from research.experiments.runner import run
from research.evaluation.benchmark import BenchmarkReader
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores
from research.baselines.system import BaselineSystem,SOURCES
from research.baselines.generation import GroqGenerator,OfflineGenerator

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True)
    p.add_argument('--offline',action='store_true');p.add_argument('--dataset',default='data/MMG_STARK_MAG')
    a=p.parse_args();config=load_runner_config(a.config)
    if config.mode!='development' or not set(config.splits)<={'train','validation'}:p.error('Phase 6 runs must use train/validation only')
    if a.offline and config.model_ids:p.error('Offline execution requires an explicitly named offline config with no model IDs')
    if not a.offline and config.model_ids!=('openai/gpt-oss-120b',):p.error('Groq model must be explicitly configured')
    reader=BenchmarkReader(Path(a.dataset)/'benchmark')
    count=sum(1 for split in config.splits for q in reader.records(split) if not config.query_ids or q.query_id in config.query_ids)
    if not a.offline and count>4:p.error('Large API batches are not authorized in Phase 6; select at most four smoke queries')
    options=BaselineOptions.model_validate(config.retrieval_parameters)
    store=Stores(a.dataset,ROOT/'artifacts/phase6/work'/config.system_id,options,modalities=SOURCES[config.system_id])
    generator=OfflineGenerator() if a.offline else GroqGenerator(options)
    try:
        system=BaselineSystem(config,store,generator,ROOT/'artifacts/phase6/cache')
        print(run(config,reader.root,a.output,system))
    finally:
        generator.close();store.close()
