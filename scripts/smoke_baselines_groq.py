"""Four reviewed-payload Groq calls, one validation query per baseline, no retries."""
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.evaluation.benchmark import read_json
from research.experiments.config import load_runner_config
from research.experiments.runner import run,materialize,write
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores
from research.baselines.system import BaselineSystem,SOURCES
from research.baselines.generation import GroqGenerator,PROMPT
from scripts.audit_stark_mag import process_memory


class PreviewCheckedGenerator(GroqGenerator):
    def __init__(self,options,preview):
        self.preview=preview
        super().__init__(options)
    def generate(self,question,context,seed):
        expected={'model':self.options.model,'temperature':0,'seed':seed,'max_completion_tokens':self.options.max_completion_tokens,
            'reasoning_effort':'low','response_format':{'type':'json_object'},'messages':[{'role':'system','content':PROMPT},
                {'role':'user','content':'QUESTION\n'+question+'\n\nEVIDENCE\n'+context}]}
        if expected!=self.preview:raise ValueError('Payload differs from exact local review preview')
        return super().generate(question,context,seed)


if __name__=='__main__':
    started=time.perf_counter();results=[]
    for baseline in SOURCES:
        config=load_runner_config(ROOT/f'configs/baselines/{baseline}.json')
        assert config.splits==('validation',) and config.query_ids==('generated:69a22c3b4989b07ed6c3:normal',) and config.mode=='development'
        options=BaselineOptions.model_validate(config.retrieval_parameters)
        store=Stores(ROOT/'data/MMG_STARK_MAG',ROOT/'artifacts/phase6/work'/baseline,options,modalities=SOURCES[baseline])
        generator=PreviewCheckedGenerator(options,read_json(ROOT/f'documentation/phase6/api_payload_preview/{baseline}.json'))
        try:
            system=BaselineSystem(config,store,generator,ROOT/'artifacts/phase6/cache-final')
            directory=ROOT/f'documentation/phase6/groq_smoke/{baseline}'
            run(config,ROOT/'data/MMG_STARK_MAG/benchmark',directory,system)
            record=materialize(directory)[0]
            results.append({'baseline':baseline,'query_id':record.query_id,'answer_ids':record.answer_ids,'metrics':record.metrics,
                'errors':[e.model_dump() for e in record.errors],'observation':record.observation.model_dump(),
                'resources':process_memory(),'experiment_id':record.experiment_id})
            print(baseline,'calls',record.observation.llm_calls,'errors',len(record.errors),flush=True)
        finally:generator.close();store.close()
    write(ROOT/'documentation/phase6/groq_resources.json',{'elapsed_seconds':time.perf_counter()-started,'runs':results,
        'maximum_calls':4,'actual_calls':sum(r['observation']['llm_calls'] for r in results),'estimated_cost':None,'pricing_source':None})
