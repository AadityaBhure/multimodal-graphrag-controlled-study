"""Pinned, local-only BGE cross-encoder; never a generation/API call."""
from pathlib import Path
import json
from research.evaluation.benchmark import digest
from research.common.serialization import content_hash
class LocalReranker:
    def __init__(self,config_path,model_dir):
        self.config=json.loads(Path(config_path).read_text(encoding='utf-8'));self.model_dir=Path(model_dir);self.model=None;self.tokenizer=None;self.truncations=0
        hashes={p.name:digest(p) for p in self.model_dir.iterdir() if p.is_file()}
        self.fingerprint=content_hash({'config':self.config,'files':hashes});self.files=hashes
    def load(self):
        if self.model is not None:return
        import torch
        from transformers import AutoTokenizer,AutoModelForSequenceClassification
        torch.set_num_threads(self.config['threads'])
        self.tokenizer=AutoTokenizer.from_pretrained(self.model_dir,local_files_only=True,trust_remote_code=False)
        self.model=AutoModelForSequenceClassification.from_pretrained(self.model_dir,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.float32).eval()
    def __call__(self,query,texts):
        self.load();import torch
        result=[];self.truncations=0
        with torch.inference_mode():
            for text in texts:
                raw=self.tokenizer(query,text,truncation=False)
                self.truncations+=len(raw['input_ids'])>self.config['max_length']
                inputs=self.tokenizer(query,text,padding=True,truncation=True,max_length=self.config['max_length'],return_tensors='pt')
                result.append(float(self.model(**inputs).logits.reshape(-1)[0]))
        return result
