"""Bounded read-only browsing; explorer data is never used as generation context."""
from pathlib import Path
from threading import RLock
from research.common.config import PROJECT_ROOT
from research.baselines.config import BaselineOptions
from research.baselines.stores import Stores,literal
from research.baselines.retrieval import RELATIONS


class DatasetExplorer:
    def __init__(self,root=PROJECT_ROOT/'data/MMG_STARK_MAG',work=PROJECT_ROOT/'artifacts/research_ui/explorer'):
        self.root=Path(root);self.work=Path(work);self.store=None;self.lock=RLock()

    def ready(self):
        if self.store is None:
            self.store=Stores(self.root,self.work,BaselineOptions(),modalities=('text','graph','structured'))
        return self.store

    def papers(self,term='',after=-1,limit=20):
        if type(limit) is not int or not 1<=limit<=50 or type(after) is not int:raise ValueError('Invalid bounded page.')
        if len(term)>300:raise ValueError('Search text is too long.')
        with self.lock:
            store=self.ready()
            rows=store.con.execute('SELECT paper_id,title FROM texts WHERE paper_id>? AND contains(lower(title),lower(?)) ORDER BY paper_id LIMIT ?',
                                   [after,term,limit]).fetchall()
            return [{'paper_id':r[0],'title':r[1]} for r in rows]

    def paper(self,paper_id):
        if type(paper_id) is not int or paper_id<0:raise ValueError('Use a nonnegative STaRK global node ID.')
        with self.lock:
            store=self.ready();text=store.texts([paper_id]).get(paper_id)
            if text is None:return None
            structured=store.structured_rows([paper_id]).get(paper_id)
            if structured:structured={k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in structured.items()}
            path=store.verify('canonical/canonical_entities.parquet')
            cursor=store.con.execute('SELECT * FROM read_parquet('+literal(path)+') WHERE stark_node_id=?',[paper_id])
            row=cursor.fetchone();registry=dict(zip([c[0] for c in cursor.description],row)) if row else None
            return {'text':text,'structured':structured,'registry':registry,'representation_manifest_sha256':store.manifest_hash}

    def neighbors(self,node_id,offset=0,limit=25):
        if type(node_id) is not int or type(offset) is not int or type(limit) is not int or node_id<0 or offset<0 or not 1<=limit<=50:
            raise ValueError('Invalid bounded neighborhood request.')
        with self.lock:
            store=self.ready();csr=store.csr
            if node_id>=len(csr['indptr'])-1:raise ValueError('Node is outside the frozen graph.')
            start,end=map(int,csr['indptr'][node_id:node_id+2]);positions=range(min(start+offset,end),min(start+offset+limit,end))
            rows=[{'source':node_id,'target':int(csr['neighbors'][i]),'edge_id':int(csr['edge_ids'][i]),
                   'relation':RELATIONS[int(csr['relation_ids'][i])],'derived_inverse':bool(csr['derived_inverse'][i])} for i in positions]
            ids={node_id}|{r['target'] for r in rows};nodes=store.nodes(sorted(ids))
            return {'node_id':node_id,'degree':end-start,'offset':offset,'rows':rows,'nodes':list(nodes.values()),
                    'has_more':offset+len(rows)<end-start,'limit':limit}

    def close(self):
        with self.lock:
            if self.store is not None:self.store.close()
            self.store=None
