"""Read-only UI integration smoke; no Groq calls and no benchmark experiment creation."""
from pathlib import Path
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.ui.service import ResearchService,performance
from research.ui.explorer import DatasetExplorer
from research.experiments.runner import write
from scripts.audit_stark_mag import process_memory

if __name__=='__main__':
    start=time.perf_counter();service=ResearchService();checks=[]
    examples=json.loads((ROOT/'research/ui/examples.json').read_text(encoding='utf-8'))
    try:
        for example in examples:
            run=service.retrieve(example['question'],example['method'])
            assert not run['output']['errors'],run['output']['errors']
            assert run['output']['observation']['llm_calls']==0 and run['output']['answer_ids'] is None
            write(ROOT/f"documentation/phase6_5/{example['method']}_example.json",run)
            if example['method']=='B1':assert 1172724 in run['output']['ranked_paper_ids'],'Text title lookup did not find its source paper'
            if example['method']=='B2':assert run['output']['evidence'] and all(e['source_type']=='graph' for e in run['output']['evidence'])
            if example['method']=='B3':assert len(run['output']['ranked_paper_ids'])==1
            checks.append({'label':example['label'],'method':example['method'],'paper_ids':run['output']['ranked_paper_ids'],
                           'performance':performance(run),'resources':process_memory()})
            print(example['method'],'UI retrieval PASS',flush=True)
    finally:service.close()
    explorer=DatasetExplorer()
    try:
        papers=explorer.papers('refractory');assert len(papers)<=20
        detail=explorer.paper(1172724);assert detail['text']['paper_id']==detail['structured']['paper_id']==detail['registry']['stark_node_id']
        graph=explorer.neighbors(1172724);assert len(graph['rows'])<=25
        assert explorer.ready().index is None
        write(ROOT/'documentation/phase6_5/explorer_sample.json',{'papers':papers,'detail':detail,'neighborhood':graph})
    finally:explorer.close()
    write(ROOT/'documentation/phase6_5/integration_checks.json',{'status':'pass','examples':checks,
        'explorer_papers':len(papers),'explorer_edges':len(graph['rows']),'llm_calls':0,
        'elapsed_seconds':time.perf_counter()-start,'resources':process_memory()})
