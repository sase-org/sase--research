import copy, gc, gzip, hashlib, importlib.metadata, json, os, platform, shutil, statistics, sys, tempfile, time
from pathlib import Path
import sase_core_rs as rs
try:
    from compression import zstd
except ImportError:
    zstd = None
ROOT=Path(__file__).resolve().parent
REPS=7
BASE_TIME='2026-01-01T00:00:00Z'

def timed(fn, reps=REPS):
    fn()
    values=[]
    for _ in range(reps):
        start=time.perf_counter_ns(); result=fn(); values.append((time.perf_counter_ns()-start)/1e6)
        del result
    return {'median_ms':statistics.median(values),'min_ms':min(values),'max_ms':max(values),'samples_ms':values}

def dump(path,obj):
    path.write_text(json.dumps(obj,separators=(',',':'))+'\n')

with tempfile.TemporaryDirectory(prefix='seed-',dir=ROOT) as tmp:
    d=Path(tmp)
    rs.bead_init_store(str(d),'.','bench','researcher-cdx')
    outcome=rs.bead_create(str(d),{'title':'Synthetic bead','issue_type':'task','task_type':'bug','size':'small','description':'d'*256,'creation_reason':'Isolated performance experiment','now':BASE_TIME})
    seed=json.loads(next((d/'events/streams').glob('*.jsonl')).read_text().splitlines()[0])


def generate(d,n,history=1,description_bytes=256,layout='tasks',closed_fraction=.95):
    streams=d/'events/streams'; streams.mkdir(parents=True)
    dump(d/'config.json',{'issue_prefix':'bench','next_counter':n+1000000,'owner':'researcher-cdx'})
    buffers={}
    for i in range(n):
        bead_id=f'bench-{i+1}' if layout=='tasks' or i==0 else f'bench-1.{i}'
        event=copy.deepcopy(seed); issue=event['payload']['issue']; issue['id']=bead_id; event['issue_id']=bead_id
        issue['description']='d'*description_bytes
        issue['title']=f'Synthetic bead {i+1}'
        is_closed=i>=max(1,int(n*(1-closed_fraction)))
        issue['status']='closed' if is_closed else 'open'
        issue['closed_at']=BASE_TIME if is_closed else None
        issue['resolution']='done' if is_closed else None
        issue['close_reason']='Completed synthetic work' if is_closed else None
        if layout!='tasks':
            issue['issue_type']='plan' if i==0 else 'phase'; issue['tier']='epic' if i==0 else None
            issue['parent_id']=None if i==0 else 'bench-1'; issue['task_type']=None
            issue['design']='plans/synthetic.md' if i==0 else ''; issue['size']=None if i==0 else 'small'
        event['event_id']=f'{bead_id}:created'
        stream_id=bead_id if layout=='tasks' else 'bench-1'
        lines=buffers.setdefault(stream_id,[]); lines.append(json.dumps(event,separators=(',',':'))+'\n')
        for j in range(1,history):
            updated={'schema_version':1,'event_id':f'{bead_id}:update:{j}','timestamp':BASE_TIME,'actor':'researcher-cdx','operation':'issue_updated','issue_id':bead_id,'payload':{'kind':'issue_updated','fields':{'title':f'Synthetic bead {i+1} revision {j}'}}}
            lines.append(json.dumps(updated,separators=(',',':'))+'\n')
    for sid,lines in buffers.items(): (streams/f'{sid}.jsonl').write_text(''.join(lines))
    dump(d/'events/manifest.json',{'schema_version':1,'stream_count':len(buffers),'generated_from':'issues.jsonl','migration_tool':'research synthetic generator'})
    assert rs.bead_stats(str(d))['total']==n
    rs.bead_export_jsonl(str(d))
    packed=''.join(''.join(buffers[s]) for s in sorted(buffers)).encode()
    comp={'raw_bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest()}
    for name,encode,decode in [('gzip6',lambda b:gzip.compress(b,compresslevel=6,mtime=0),gzip.decompress)]+([] if zstd is None else [('zstd3',lambda b:zstd.compress(b,level=3),zstd.decompress)]):
        start=time.perf_counter(); encoded=encode(packed); enc_ms=(time.perf_counter()-start)*1000
        start=time.perf_counter(); recovered=decode(encoded); dec_ms=(time.perf_counter()-start)*1000
        assert recovered==packed
        comp[name]={'bytes':len(encoded),'ratio':len(packed)/len(encoded),'encode_ms':enc_ms,'decode_ms':dec_ms}
    return {'n':n,'history_events_per_bead':history,'layout':layout,'streams':len(buffers),'events':n*history,'description_bytes':description_bytes,'closed_fraction':closed_fraction,'projection_bytes':(d/'issues.jsonl').stat().st_size,'compression':comp}

result={'environment':{'python':sys.version,'platform':platform.platform(),'rust_binding':importlib.metadata.version('sase-core-rs'),'repetitions':REPS,'warmups':1,'time_clock':'perf_counter_ns','cwd':str(Path.cwd())},'scenarios':[]}
scenarios=[(100,1,256,'tasks'),(1000,1,256,'tasks'),(5000,1,256,'tasks'),(10000,1,256,'tasks'),(1000,5,256,'tasks'),(1000,25,256,'tasks'),(1000,1,8192,'tasks'),(1000,1,256,'epic'),(1000,25,256,'epic')]
if '--resume' in sys.argv and (ROOT/'results.json').exists():
    result=json.loads((ROOT/'results.json').read_text())
for n,h,b,layout in scenarios:
    if any((r['n'],r['history_events_per_bead'],r['description_bytes'],r['layout'])==(n,h,b,layout) for r in result['scenarios']): continue
    with tempfile.TemporaryDirectory(prefix='synthetic-',dir=ROOT) as tmp:
        d=Path(tmp); row=generate(d,n,h,b,layout)
        operations={'show':lambda:rs.bead_show(str(d),'bench-1'),'active_list':lambda:rs.bead_list(str(d),statuses=['open']),'stats':lambda:rs.bead_stats(str(d)),'legacy_projection_read':lambda:rs.bead_read_legacy_jsonl(str(d)),'append_note':lambda:rs.bead_append_note(str(d),'bench-1','Measured note','researcher-cdx',BASE_TIME),'export_projection':lambda:rs.bead_export_jsonl(str(d))}
        row['operations']={k:timed(fn) for k,fn in operations.items()}
        result['scenarios'].append(row)
        (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(row),flush=True)
print('BENCHMARK_COMPLETE',flush=True)
