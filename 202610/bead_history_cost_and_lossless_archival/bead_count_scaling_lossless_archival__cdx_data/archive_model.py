import collections,io,json,shutil,statistics,tarfile,tempfile,time
from pathlib import Path
from compression import zstd
import sase_core_rs as rs
ROOT=Path(__file__).resolve().parent
SOURCE=Path.cwd()/'sase/repos/beads'

def timed(fn):
    fn(); times=[]
    for _ in range(7):
        start=time.perf_counter_ns(); result=fn(); times.append((time.perf_counter_ns()-start)/1e6); del result
    return {'median_ms':statistics.median(times),'min_ms':min(times),'max_ms':max(times),'samples_ms':times}

with tempfile.TemporaryDirectory(prefix='archive-model-',dir=ROOT) as tmp:
    d=Path(tmp); full=d/'full'; full.mkdir()
    shutil.copytree(SOURCE/'events',full/'events')
    for name in ['config.json','issues.jsonl']: shutil.copy2(SOURCE/name,full/name)
    rows=rs.bead_read_store(str(full)); status={r['id']:r['status'] for r in rows}
    counts=collections.Counter(); bytecounts=collections.Counter(); files=sorted((full/'events/streams').glob('*.jsonl')); stream_categories=collections.Counter()
    member_data={str(f.relative_to(full)):f.read_bytes() for f in files}
    for name in ['events/manifest.json','config.json','issues.jsonl']: member_data[name]=(full/name).read_bytes()
    for f in files:
        live_ids=set()
        for line in f.read_bytes().splitlines(keepends=True):
            if not line.strip(): continue
            event=json.loads(line); sid=event['issue_id']; category='closed' if status.get(sid)=='closed' else 'active' if sid in status else 'removed_or_unknown'
            counts[category]+=1;bytecounts[category]+=len(line)
            if sid in status: live_ids.add(sid)
        category='all_closed_current_rows' if live_ids and all(status[i]=='closed' for i in live_ids) else 'mixed_or_active' if live_ids else 'no_current_rows'
        stream_categories[category]+=1
    packed=io.BytesIO()
    with tarfile.open(fileobj=packed,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for name,data in sorted(member_data.items()):
            info=tarfile.TarInfo(name);info.size=len(data);tf.addfile(info,io.BytesIO(data))
    decoded=zstd.decompress(zstd.compress(packed.getvalue(),level=3))
    with tarfile.open(fileobj=io.BytesIO(decoded),mode='r:') as tf:
        restored={m.name:tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
    assert restored==member_data
    out={'stats':rs.bead_stats(str(full)),'event_count_by_current_status':dict(counts),'event_bytes_by_current_status':dict(bytecounts),'streams_by_current_status':dict(stream_categories),'full_snapshot_archive_bytes':len(zstd.compress(packed.getvalue(),level=3)),'restore_verified_files':len(restored),'restore_byte_equality':True}
    # Counterfactual cost only: active current state, without event history or cold-reference handling.
    active=[r for r in rows if r['status']!='closed']; slim=d/'projection-only'; slim.mkdir()
    (slim/'issues.jsonl').write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in active))
    target=active[0]['id']; assert rs.bead_show(str(slim),target)==active[0]
    out['counterfactual_active_projection']={'beads':len(active),'bytes':(slim/'issues.jsonl').stat().st_size,'show':timed(lambda:rs.bead_show(str(slim),target)),'active_list':timed(lambda:rs.bead_list(str(slim)))}
    (ROOT/'archive_model_results.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out),flush=True)
