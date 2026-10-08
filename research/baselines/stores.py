"""Read-only modality-separated stores. No full Python graph is constructed."""
from pathlib import Path
import re
import numpy as np
import duckdb
from research.evaluation.benchmark import read_json,digest
from research.baselines.structured import compile_plan


def literal(value):
    return "'"+str(value).replace("'","''")+"'"


class QueryEncoder:
    def __init__(self,root,options):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        from huggingface_hub import try_to_load_from_cache
        tokenizer=try_to_load_from_cache(options.embedding,'tokenizer.json',revision=options.embedding_revision)
        if not isinstance(tokenizer,str):raise FileNotFoundError('Pinned MiniLM tokenizer is not cached')
        self.tokenizer=Tokenizer.from_file(tokenizer)
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding(pad_id=0,pad_token='[PAD]')
        opts=ort.SessionOptions();opts.intra_op_num_threads=options.threads;opts.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(Path(root)/'text/faiss/model.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
        self.fingerprint={'model':options.embedding,'revision':options.embedding_revision,'tokenizer_sha256':digest(tokenizer),
                          'onnx_sha256':digest(Path(root)/'text/faiss/model.onnx'),'backend':'onnx-cpu-fp32','max_tokens':256}

    def encode(self,texts):
        encoded=self.tokenizer.encode_batch(texts)
        feed={'input_ids':np.array([e.ids for e in encoded],dtype=np.int64),
              'attention_mask':np.array([e.attention_mask for e in encoded],dtype=np.int64),
              'token_type_ids':np.array([e.type_ids for e in encoded],dtype=np.int64)}
        vectors=self.session.run(['embeddings'],feed)[0]
        if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5):
            raise ValueError('Invalid MiniLM query vectors')
        return vectors.astype(np.float32,copy=False)


class Stores:
    def __init__(self,root,work,options,*,modalities):
        self.root=Path(root).resolve();self.options=options
        work=Path(work).resolve()
        if work.is_relative_to(self.root):raise ValueError('Temporary storage cannot overlap frozen dataset')
        work.mkdir(parents=True,exist_ok=True)
        self.manifest=read_json(self.root/'manifest.json');self.manifest_hash=digest(self.root/'manifest.json')
        self.files={r['path']:r for r in self.manifest['files']};self.checked=set()
        self.con=duckdb.connect(':memory:',config={'memory_limit':options.memory_limit,'threads':options.threads,
                                                  'temp_directory':str(work/'duckdb_temp')})
        self.modalities=set(modalities);self.encoder=None;self.index=None;self.csr=None
        if 'text' in self.modalities:
            self.con.execute('CREATE VIEW texts AS SELECT * FROM read_parquet('+literal(self.verify('text/text_documents.parquet'))+')')
            self.mapping=np.load(self.verify('text/faiss/row_to_paper_id.npy'),mmap_mode='r',allow_pickle=False)
        if 'graph' in self.modalities:
            self.con.execute('CREATE VIEW nodes AS SELECT * FROM read_parquet('+literal(self.verify('graph/nodes.parquet'))+')')
            self.csr={n:np.load(self.verify('graph/adjacency/'+n+'.npy'),mmap_mode='r',allow_pickle=False)
                      for n in ('indptr','neighbors','edge_ids','relation_ids','derived_inverse')}
        if 'structured' in self.modalities:
            self.con.execute('ATTACH '+literal(self.verify('structured/stark_mag.duckdb'))+' AS structured (READ_ONLY)')
            self.con.execute('CREATE VIEW papers AS SELECT * FROM structured.papers_structured')

    def verify(self,relative):
        row=self.files[relative];path=self.root/relative
        if relative not in self.checked:
            if path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:raise ValueError('Frozen representation checksum mismatch')
            self.checked.add(relative)
        return path

    def encode(self,texts):
        if self.encoder is None:
            self.verify('text/faiss/model.onnx')
            self.encoder=QueryEncoder(self.root,self.options)
        return self.encoder.encode(texts)

    def text_search(self,question,k):
        if 'text' not in self.modalities:raise ValueError('Text access not enabled')
        if self.index is None:
            import faiss
            faiss.omp_set_num_threads(self.options.threads)
            self.index=faiss.read_index(str(self.verify('text/faiss/index.faiss')))
            if self.index.ntotal!=len(self.mapping) or self.index.d!=384:raise ValueError('FAISS mapping mismatch')
        scores,rows=self.index.search(self.encode([question]),k)
        ranked=[(int(self.mapping[r]),float(score)) for r,score in zip(rows[0],scores[0]) if r>=0]
        return sorted(ranked,key=lambda x:(-x[1],x[0]))

    def texts(self,ids):
        if 'text' not in self.modalities:raise ValueError('Graph baseline cannot read abstract/text view')
        if not ids:return {}
        rows=self.con.execute('SELECT paper_id,title,abstract,content FROM texts WHERE paper_id IN ('+','.join('?' for _ in ids)+')',list(ids)).fetchall()
        return {r[0]:dict(zip(('paper_id','title','abstract','content'),r)) for r in rows}

    def seed_nodes(self,question):
        if 'graph' not in self.modalities:raise ValueError('Graph access not enabled')
        # Bounded lexical candidate resolution followed by semantic graph-label seed ranking.
        stop={'which','what','papers','paper','these','requirements','least','most','with','from','that','have','this','recorded','abstract','explicitly','includes','case','insensitive','author','authors','affiliated','satisfy','publication','citation','count','rank','year','and','the','for','are','was','were','one'}
        tokens=list(dict.fromkeys(t for t in re.findall(r'\w+',question.lower()) if len(t)>=3 and t not in stop))[:16]
        if not tokens:return []
        terms=['CAST(contains(lower(label), ?) AS INTEGER)' for _ in tokens]
        score='+'.join(terms)
        sql='SELECT node_id,label,node_type, CASE WHEN length(label)>=4 AND contains(?,lower(label)) THEN 1 ELSE 0 END AS exact, ('+score+') AS matches FROM nodes WHERE label IS NOT NULL AND ('+' OR '.join('contains(lower(label), ?)' for _ in tokens)+') ORDER BY exact DESC,matches DESC,length(label),node_id LIMIT ?'
        rows=self.con.execute(sql,[question.lower()]+tokens+tokens+[self.options.seed_pool]).fetchall()
        if not rows:return []
        vectors=self.encode([question]+[r[1] for r in rows]);similarity=vectors[1:]@vectors[0]
        order=sorted(range(len(rows)),key=lambda i:(-rows[i][3],-float(similarity[i]),rows[i][0]))[:self.options.seed_k]
        return [{'node_id':int(rows[i][0]),'label':rows[i][1],'node_type':rows[i][2],'score':float(similarity[i])} for i in order]

    def nodes(self,ids):
        if not ids:return {}
        rows=self.con.execute('SELECT node_id,label,node_type FROM nodes WHERE node_id IN ('+','.join('?' for _ in ids)+')',list(ids)).fetchall()
        return {r[0]:{'node_id':r[0],'label':r[1],'node_type':r[2]} for r in rows}

    def structured(self,plan,k):
        if 'structured' not in self.modalities:raise ValueError('Structured access not enabled')
        sql,args=compile_plan(plan,k)
        cursor=self.con.execute(sql,args)
        names=[d[0] for d in cursor.description]
        return [dict(zip(names,row)) for row in cursor.fetchall()]

    def structured_rows(self,ids):
        if 'structured' not in self.modalities:raise ValueError('Structured access not enabled')
        if not ids:return {}
        if len(ids)>100 or any(type(i) is not int for i in ids):raise ValueError('Invalid bounded ID lookup')
        cursor=self.con.execute('SELECT paper_id,publication_year,publication_date,citation_count,paper_rank,venue_namespace,venue_id,venue_name,document_type FROM papers WHERE paper_id IN ('+','.join('?' for _ in ids)+')',ids)
        names=[d[0] for d in cursor.description]
        return {row[0]:dict(zip(names,row)) for row in cursor.fetchall()}

    def close(self):
        self.con.close()
        self.index=None;self.encoder=None;self.csr=None
