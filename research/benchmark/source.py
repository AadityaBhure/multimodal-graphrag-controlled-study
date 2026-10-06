"""Read-only bounded access to frozen Phase 3 representations for construction."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import duckdb
import pyarrow.parquet as pq
from research.common.config import PROJECT_ROOT
from scripts.audit_stark_mag import digest


class Source:
    def __init__(self, config, root=None):
        self.root = Path(root) if root else PROJECT_ROOT / 'data/MMG_STARK_MAG'
        self.config = config
        self.manifest = json.loads((self.root / 'manifest.json').read_text(encoding='utf-8'))
        self.con = duckdb.connect(':memory:')
        self.con.execute(f"SET memory_limit='{config.duckdb_memory_limit}'")
        self.con.execute(f'SET threads={config.duckdb_threads}')
        self.con.execute('SET preserve_insertion_order=false')
        work = self.root / '_build/phase4'
        work.mkdir(parents=True, exist_ok=True)
        self.con.execute(f"SET temp_directory='{work.as_posix()}/duckdb_temp'")
        for name, path in [('texts','text/text_documents.parquet'),('nodes','graph/nodes.parquet'),('registry','canonical/canonical_entities.parquet')]:
            self.con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{(self.root/path).as_posix()}')")
        self.con.execute(f"ATTACH '{(self.root/'structured/stark_mag.duckdb').as_posix()}' AS structured (READ_ONLY)")
        self.con.execute('CREATE VIEW papers AS SELECT * FROM structured.papers_structured')
        self.csr = {n: np.load(self.root/f'graph/adjacency/{n}.npy', mmap_mode='r', allow_pickle=False)
                    for n in ('indptr','neighbors','edge_ids','relation_ids','derived_inverse')}
        self.labels = {}
        self.text_cache = {}
        self.structured_cache = {}
        self.graph_cache = {}

    def verify(self):
        for f in self.manifest['files']:
            p = self.root / f['path']
            assert p.stat().st_size == f['bytes'] and digest(p) == f['sha256'], p
        raw = self.root/'raw/stark_mag'
        manifest = json.loads((raw/'raw_manifest.json').read_text(encoding='utf-8'))
        for f in manifest['files']:
            assert digest(raw/f['path']) == f['sha256'], f['path']
        return {'representation_files':len(self.manifest['files']), 'raw_files':len(manifest['files']),
                'representation_manifest_sha256':digest(self.root/'manifest.json'), 'raw_manifest_sha256':digest(raw/'raw_manifest.json')}

    def label(self, node):
        node = int(node)
        if node not in self.labels:
            self.labels[node] = self.con.execute('SELECT label FROM nodes WHERE node_id=?',[node]).fetchone()[0]
        return self.labels[node]

    def adjacent(self, node, relation=None, inverse=None):
        a,z = map(int,self.csr['indptr'][int(node):int(node)+2])
        for pos in range(a,z):
            if relation is not None and int(self.csr['relation_ids'][pos]) != relation:
                continue
            if inverse is not None and bool(self.csr['derived_inverse'][pos]) != inverse:
                continue
            yield int(self.csr['neighbors'][pos]),int(self.csr['edge_ids'][pos])

    def degree(self, node):
        return int(self.csr['indptr'][node+1]-self.csr['indptr'][node])

    def graph(self, condition):
        key = json.dumps(condition,sort_keys=True)
        if key in self.graph_cache:
            return self.graph_cache[key]
        anchor = condition['anchor_id']
        paths = {anchor: []}
        steps = {'author':[(3,False)], 'institution':[(0,True),(3,False)],
                 'institution_citations':[(0,True),(3,False),(1,False)]}[condition['kind']]
        visits = 0
        for relation,inverse in steps:
            next_paths = {}
            for node,path in sorted(paths.items()):
                for target, edge in self.adjacent(node,relation,inverse):
                    visits += 1
                    if visits > 200000:
                        raise ValueError('Construction anchor expansion exceeds budget')
                    next_paths.setdefault(target,path+[{'source':node,'target':target,'edge_id':edge,
                                                        'relation_id':relation,'derived_inverse':inverse}])
            paths = next_paths
        if 'additional_author' in condition:
            allowed = {p for p,_ in self.adjacent(condition['additional_author'],3,False)}
            paths = {p:v for p,v in paths.items() if p in allowed}
        result = (set(paths),paths)
        if len(self.graph_cache) >= 8:
            self.graph_cache.pop(next(iter(self.graph_cache)))
        self.graph_cache[key] = result
        return result

    def text(self, condition):
        if condition.get('operator') not in ('any','all') or not condition.get('phrases'):
            raise ValueError('Unsupported text construction predicate')
        key = json.dumps(condition,sort_keys=True)
        if key not in self.text_cache:
            clauses = ['contains(lower(abstract), ?)']*len(condition['phrases'])
            separator = ' OR ' if condition['operator']=='any' else ' AND '
            where='('+separator.join(clauses)+')'
            args=list(condition['phrases'])
            if condition.get('required_extra_phrase'):
                where+=' AND contains(lower(abstract), ?)';args.append(condition['required_extra_phrase'])
            self.text_cache[key] = {r[0] for r in self.con.execute('SELECT paper_id FROM texts WHERE '+where,args).fetchall()}
        return self.text_cache[key]

    @staticmethod
    def sql_predicate(condition):
        allowed = {'publication_year','publication_date','citation_count','paper_rank','venue_namespace','venue_id'}
        ops = {'=','>=','<=','>','<'}
        clauses,values=[],[]
        if not condition.get('filters'):
            raise ValueError('Empty structured construction predicate')
        for item in condition['filters']:
            if item['field'] not in allowed or item['operator'] not in ops:
                raise ValueError('Unsupported construction predicate')
            clauses.append(item['field']+' '+item['operator']+' ?')
            values.append(item['value'])
        return ' AND '.join(clauses),values

    def structured(self, condition):
        key = json.dumps(condition,sort_keys=True)
        if key not in self.structured_cache:
            where,args=self.sql_predicate(condition)
            result={r[0] for r in self.con.execute('SELECT paper_id FROM papers WHERE '+where,args).fetchall()}
            # Do not retain a large cache of full-corpus filter results.
            if len(self.structured_cache) >= 20:
                self.structured_cache.clear()
            self.structured_cache[key]=result
        return self.structured_cache[key]

    def candidates(self, conditions):
        return {m:getattr(self,m)(c)[0] if m=='graph' else getattr(self,m)(c) for m,c in conditions.items()}

    def row(self, paper):
        cursor=self.con.execute('SELECT * FROM papers WHERE paper_id=?',[paper])
        return dict(zip([d[0] for d in cursor.description],cursor.fetchone()))

    def abstract(self,paper):
        return self.con.execute('SELECT abstract FROM texts WHERE paper_id=?',[paper]).fetchone()[0]

    def titles(self, ids):
        wanted=set(ids)
        result={}
        for batch in pq.ParquetFile(self.root/'text/text_documents.parquet').iter_batches(batch_size=10000,columns=['paper_id','title']):
            for paper,title in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
                if paper in wanted:
                    result[paper]=title
        return result

    def close(self):
        self.con.close()
