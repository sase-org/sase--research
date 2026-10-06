import gzip,hashlib,io,importlib.metadata,json,os,platform,shutil,sqlite3,statistics,subprocess,tarfile,tempfile,time
from pathlib import Path
from compression import zstd
import sase_core_rs as rs
ROOT=Path(__file__).resolve().parent
SOURCE=Path.cwd()/'sase/repos/beads'
REPS=7

def timed(fn,reps=REPS):
    fn(); values=[]
    for _ in range(reps):
        start=time.perf_counter_ns(); result=fn(); values.append((time.perf_counter_ns()-start)/1e6); del result
    return {'median_ms':statistics.median(values),'min_ms':min(values),'max_ms':max(values),'samples_ms':values}

def signatures():
    files=sorted((SOURCE/'events').rglob('*'))+[SOURCE/'config.json',SOURCE/'issues.jsonl']
    return [(str(f.relative_to(SOURCE)),f.stat().st_size,f.stat().st_mtime_ns) for f in files if f.is_file()]

def head(): return subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()

with tempfile.TemporaryDirectory(prefix='real-copy-',dir=ROOT) as tmp:
    d=Path(tmp)
    before=signatures(); source_head=head()
    shutil.copytree(SOURCE/'events',d/'events')
    for name in ['config.json','issues.jsonl']: shutil.copy2(SOURCE/name,d/name)
    assert before==signatures() and source_head==head(),'Source changed during snapshot; retry on a stable store'
    rows=rs.bead_read_store(str(d)); target=next(r['id'] for r in rows if r['status']!='closed')
    files=sorted((d/'events/streams').glob('*.jsonl')); packed=b''.join(f.read_bytes() for f in files)
    result={'source_head':source_head,'rust_binding':importlib.metadata.version('sase-core-rs'),'source_stable_during_copy':True,'stats':rs.bead_stats(str(d)),'streams':len(files),'events':len(packed.splitlines()),'event_bytes':len(packed),'projection_bytes':(d/'issues.jsonl').stat().st_size,'load_at_start':os.getloadavg(),'repetitions':REPS,'warmups':1,'operations':{}}
    def save(): (ROOT/'live_results.json').write_text(json.dumps(result,indent=2)+'\n')
    operations={'show':lambda:rs.bead_show(str(d),target),'active_list':lambda:rs.bead_list(str(d),statuses=['open','claimed','ready','in_progress','snoozed']),'stats':lambda:rs.bead_stats(str(d)),'legacy_projection_read':lambda:rs.bead_read_legacy_jsonl(str(d)),'legacy_flag_scan':lambda:rs.bead_prune_removed_flag_event_streams(str(d)),'append_note':lambda:rs.bead_append_note(str(d),target,'Isolated benchmark; not a live mutation','researcher-cdx'),'export_projection':lambda:rs.bead_export_jsonl(str(d))}
    for name,fn in operations.items():
        result['operations'][name]=timed(fn); save(); print(name,json.dumps(result['operations'][name]),flush=True)
    cold=time.perf_counter(); rs.bead_touch_index_refresh(str(d),str(d/'touch.json')); result['touch_index_cold_ms']=(time.perf_counter()-cold)*1000
    result['operations']['touch_index_warm']=timed(lambda:rs.bead_touch_index_refresh(str(d),str(d/'touch.json'))); save()
    result['compression']={}
    stream_bytes=io.BytesIO()
    with tarfile.open(fileobj=stream_bytes,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for f in files:
            info=tarfile.TarInfo(str(f.relative_to(d))); data=f.read_bytes(); info.size=len(data); info.mtime=0; tf.addfile(info,io.BytesIO(data))
    for name,data in [('events_concat',packed),('events_tar',stream_bytes.getvalue())]:
        row={'raw_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        for codec,encode,decode in [('gzip6',lambda b:gzip.compress(b,compresslevel=6,mtime=0),gzip.decompress),('zstd3',lambda b:zstd.compress(b,level=3),zstd.decompress)]:
            start=time.perf_counter(); encoded=encode(data); enc_ms=(time.perf_counter()-start)*1000
            start=time.perf_counter(); decoded=decode(encoded); dec_ms=(time.perf_counter()-start)*1000
            assert decoded==data
            row[codec]={'bytes':len(encoded),'ratio':len(data)/len(encoded),'encode_ms':enc_ms,'decode_ms':dec_ms}
        result['compression'][name]=row
    index=d/'prototype.sqlite'
    with sqlite3.connect(index) as conn:
        conn.execute('CREATE TABLE projected(id TEXT PRIMARY KEY,status TEXT NOT NULL,parent_id TEXT,payload TEXT NOT NULL)')
        conn.executemany('INSERT INTO projected VALUES (?,?,?,?)',[(r['id'],r['status'],r.get('parent_id'),json.dumps(r,separators=(',',':'))) for r in rows])
        conn.execute('CREATE INDEX projected_status ON projected(status,id)');conn.commit()
    def index_show():
        with sqlite3.connect(index) as conn: return json.loads(conn.execute('SELECT payload FROM projected WHERE id=?',(target,)).fetchone()[0])
    result['operations']['prototype_index_show']=timed(index_show); result['load_at_end']=os.getloadavg(); save()
    print('LIVE_BENCHMARK_COMPLETE',json.dumps({k:v for k,v in result.items() if k!='operations'}),flush=True)
