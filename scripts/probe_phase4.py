"""Bounded read-only construction feasibility probe."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.benchmark.contracts import load_benchmark_config
from research.benchmark.source import Source
if __name__=='__main__':
    s=Source(load_benchmark_config('configs/phase4.yaml'))
    for split, phrases in s.config.text_claims.items():
        for phrase in phrases:
            n=len(s.text({'operator':'all','phrases':[phrase]}))
            graph=s.con.execute('SELECT count(*) FROM nodes WHERE contains(lower(label),?)',[phrase]).fetchone()[0]
            print(split,repr(phrase),n,graph,flush=True)
    s.close()
