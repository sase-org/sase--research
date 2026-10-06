// Stage-by-stage timing of the bead event-store read path.
// Usage: stagebench <beads_dir> [runs]
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use sase_core::bead::events::reduce_event_streams;
use sase_core::bead::jsonl::{
    export_issues_to_jsonl, prune_removed_flag_event_streams, read_event_store,
};
use sase_core::bead::read::{
    read_legacy_jsonl_issues, read_store_issues, show_issue_detail,
};

fn stream_paths(dir: &Path) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = fs::read_dir(dir.join("events/streams"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().map(|x| x == "jsonl").unwrap_or(false))
        .collect();
    v.sort();
    v
}

fn time<F: FnMut()>(label: &str, runs: usize, mut f: F) -> f64 {
    f(); // warm-up
    let mut samples = Vec::with_capacity(runs);
    for _ in 0..runs {
        let t = Instant::now();
        f();
        samples.push(t.elapsed().as_secs_f64() * 1000.0);
    }
    samples.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let med = samples[samples.len() / 2];
    println!(
        "{label:<58} median {med:>9.2} ms   min {:>9.2}  max {:>9.2}",
        samples[0],
        samples[samples.len() - 1]
    );
    med
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dir = PathBuf::from(&args[1]);
    let runs: usize = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(7);
    let detail_id = args.get(3).cloned();

    let paths = stream_paths(&dir);
    println!("streams: {}", paths.len());

    time("1. list dir + stat every stream", runs, || {
        let mut n = 0u64;
        for p in stream_paths(&dir) {
            n += fs::metadata(&p).unwrap().len();
        }
        std::hint::black_box(n);
    });
    time("2. open + read all stream bytes", runs, || {
        let mut n = 0usize;
        for p in &paths {
            n += fs::read(p).unwrap().len();
        }
        std::hint::black_box(n);
    });
    time("3. untyped serde_json::Value parse of every line", runs, || {
        let mut n = 0usize;
        for p in &paths {
            let s = fs::read_to_string(p).unwrap();
            for line in s.lines() {
                if line.trim().is_empty() {
                    continue;
                }
                let v: serde_json::Value = serde_json::from_str(line).unwrap();
                n += v.is_object() as usize;
            }
        }
        std::hint::black_box(n);
    });
    time("4. prune_removed_flag_event_streams (detector, no-op)", runs, || {
        std::hint::black_box(prune_removed_flag_event_streams(&dir).unwrap());
    });
    let t_store = time("5. read_event_store (4 + typed parse + stream validate)", runs, || {
        std::hint::black_box(read_event_store(&dir).unwrap());
    });
    let (_m, streams) = read_event_store(&dir).unwrap();
    let events: usize = streams.iter().map(|s| s.events.len()).sum();
    println!("events: {events}");
    let t_reduce = time("6. reduce_event_streams (clone+validate+merge+apply+sort)", runs, || {
        std::hint::black_box(reduce_event_streams(&streams).unwrap());
    });
    time("6a. deep clone of all parsed streams (validated_event_streams copy)", runs, || {
        std::hint::black_box(streams.clone());
    });
    time("6b. stream.validate() for every stream", runs, || {
        for s in &streams { s.validate().unwrap(); }
    });
    time("5a. typed BeadEventRecordWire parse only (no prune)", runs, || {
        let mut n = 0usize;
        for p in &paths {
            let s = fs::read_to_string(p).unwrap();
            for line in s.lines() {
                if line.trim().is_empty() { continue; }
                let v: sase_core::bead::events::BeadEventRecordWire = serde_json::from_str(line).unwrap();
                n += v.event_id.len();
            }
        }
        std::hint::black_box(n);
    });
    let issues = reduce_event_streams(&streams).unwrap();
    println!("issues: {}", issues.len());
    time("7. clone of reduced Vec<IssueWire>", runs, || {
        std::hint::black_box(issues.clone());
    });
    time("8. read_store_issues (production read path)", runs, || {
        std::hint::black_box(read_store_issues(&dir).unwrap());
    });
    time("9. export_issues_to_jsonl (projection serialization)", runs, || {
        std::hint::black_box(export_issues_to_jsonl(&issues).unwrap());
    });
    time("10. read_legacy_jsonl_issues (parse issues.jsonl)", runs, || {
        std::hint::black_box(read_legacy_jsonl_issues(&dir).unwrap());
    });
    if let Some(id) = detail_id {
        time("11. show_issue_detail (sase bead read core)", runs, || {
            std::hint::black_box(show_issue_detail(&dir, &id).unwrap());
        });
    }
    println!(
        "sum(5,6) = {:.1} ms (production read ≈ this)",
        t_store + t_reduce
    );
}
