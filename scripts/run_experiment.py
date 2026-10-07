"""Run Phase 5 synthetic infrastructure checks, never a scientific baseline."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.experiments.config import load_runner_config
from research.experiments.runner import run
from research.experiments.synthetic import SyntheticSystem, ScriptedSyntheticSystem

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--config',required=True)
    p.add_argument('--benchmark',default='data/MMG_STARK_MAG/benchmark')
    p.add_argument('--output',required=True)
    p.add_argument('--release')
    p.add_argument('--responses',help='Prewritten synthetic fixture response JSON')
    a=p.parse_args()
    config=load_runner_config(a.config)
    if config.system_id == SyntheticSystem.system_id and not a.responses:
        system=SyntheticSystem()
    elif config.system_id == ScriptedSyntheticSystem.system_id and a.responses:
        system=ScriptedSyntheticSystem(a.responses)
    else:
        p.error('Phase 5 supports only explicitly configured synthetic systems')
    print(run(config,a.benchmark,a.output,system,release_path=a.release))
