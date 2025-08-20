import os
import sys
import csv
import argparse
import fnmatch
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET_DEFAULT = (
"סתם טקסט"
)

def windows_all_drives():
    import ctypes
    drives = []
    GetLogicalDrives = ctypes.windll.kernel32.GetLogicalDrives
    GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
    DRIVE_UNKNOWN, DRIVE_NO_ROOT_DIR, DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_REMOTE, DRIVE_CDROM, DRIVE_RAMDISK = range(7)

    bitmask = GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            root = f"{chr(65+i)}:\\"
            dtype = GetDriveTypeW(ctypes.c_wchar_p(root))
            #scan fixed, removable, and remote (network) drives; skip CD-ROM/RAMDISK/invalid
            if dtype in (DRIVE_FIXED, DRIVE_REMOVABLE, DRIVE_REMOTE):
                drives.append(root)
    return drives

def posix_roots():
    roots = set(['/'])
    for base in ('/mnt', '/media', '/Volumes'):
        if os.path.isdir(base):
            for entry in os.scandir(base):
                if entry.is_dir(follow_symlinks=False):
                    roots.add(entry.path)
    return sorted(roots)

def discover_roots():
    if os.name == 'nt':
        return windows_all_drives()
    return posix_roots()


ENCODINGS = ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1255")

def read_text_with_fallback(p: Path, max_bytes: int):
    """
    Try reading text with several encodings. Returns (text, encoding) or (None, None).
    Limits file size to max_bytes to avoid huge reads.
    """
    try:
        size = p.stat().st_size
        if size > max_bytes:
            return None, None
    except Exception:
        return None, None
    for enc in ENCODINGS:
        try:
            with p.open('r', encoding=enc, errors='strict') as f:
                return f.read(), enc
        except UnicodeError:
            continue
        except Exception:
            break 
    try:
        with p.open('r', encoding='utf-8', errors='ignore') as f:
            return f.read(), 'utf-8-ignore'
    except Exception:
        return None, None

def scan_file_for_target(path: Path, target: str, max_bytes: int):
    text, enc = read_text_with_fallback(path, max_bytes)
    if text is None:
        return None

    hits = []
    if target in text:
        for idx, line in enumerate(text.splitlines(), start=1):
            if target in line:
                preview = line.strip()
                if len(preview) > 200:
                    preview = preview[:200] + "…"
                hits.append((idx, preview))
    if hits:
        return {
            "path": str(path),
            "encoding": enc,
            "matches": hits
        }
    return None

def should_skip_dir(dirname: str):
    name = os.path.basename(dirname).lower()
    #common heavy or protected dirs to skip; adjust as needed
    skip_names = {
        '$recycle.bin', 'system volume information', 'proc', 'dev', 'sys', 'run', 'lost+found'
    }
    return name in skip_names

def walk_all_text_files(root: str, follow_symlinks: bool, include_hidden: bool):
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=follow_symlinks):
        pruned = []
        for d in dirnames:
            full = os.path.join(dirpath, d)
            if not include_hidden:
                if os.name != 'nt' and d.startswith('.'):
                    continue
            if should_skip_dir(full):
                continue
            pruned.append(d)
        dirnames[:] = pruned

        for fn in filenames:
            if not include_hidden and os.name != 'nt' and fn.startswith('.'):
                continue
            if fnmatch.fnmatch(fn.lower(), "*.txt"):
                yield Path(dirpath) / fn



def main():
    parser = argparse.ArgumentParser(
        description="Search all accessible disks/partitions for a target Hebrew string inside .txt files."
    )
    parser.add_argument("--target", default=TARGET_DEFAULT, help="Target substring to search for.")
    parser.add_argument("--max-file-bytes", type=int, default=50 * 1024 * 1024,
                        help="Skip files larger than this many bytes (default 50MB).")
    parser.add_argument("--workers", type=int, default=min(8, (os.cpu_count() or 4)),
                        help="Thread workers for parallel scanning (I/O bound).")
    parser.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks/junctions (may loop).")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden files/dirs on POSIX.")
    parser.add_argument("--roots", nargs="*", default=None,
                        help="Optional list of starting roots to scan. If omitted, auto-discover all drives.")
    parser.add_argument("--output", default="matches.csv", help="CSV file to write results.")
    args = parser.parse_args()

    target = args.target
    roots = args.roots if args.roots else discover_roots()

    print("Scanning roots:")
    for r in roots:
        print("  -", r)
    print(f"\nTarget length: {len(target)} chars")
    print(f"Workers: {args.workers} | Max file size: {args.max_file_bytes} bytes\n")

    candidates = []
    for root in roots:
        try:
            for path in walk_all_text_files(root, args.follow_symlinks, args.include_hidden):
                candidates.append(path)
        except Exception as e:
            print(f"[WARN] Could not walk {root}: {e}", file=sys.stderr)

    print(f"Discovered .txt files: {len(candidates)}\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(scan_file_for_target, p, target, args.max_file_bytes): p for p in candidates}
        processed = 0
        try:
            for fut in as_completed(futures):
                processed += 1
                if processed % 500 == 0:
                    print(f"...processed {processed}/{len(candidates)} files")
                try:
                    r = fut.result()
                    if r:
                        results.append(r)
                        print(f"[HIT] {r['path']}  (encoding={r['encoding']})  lines={','.join(str(x[0]) for x in r['matches'])}")
                except Exception as e:
                    p = futures[fut]
                    print(f"[ERROR] {p}: {e}", file=sys.stderr)
                    #uncomment for debug
                    #traceback.print_exc()
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Stopping early…")

    #write CSV report
    out = Path(args.output)
    try:
        with out.open("w", newline='', encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["path", "encoding", "line_number", "line_preview"])
            for item in results:
                for ln, preview in item["matches"]:
                    w.writerow([item["path"], item["encoding"], ln, preview])
        print(f"\nDone. Matches: {sum(len(it['matches']) for it in results)} lines in {len(results)} files.")
        print(f"Report written to: {out.resolve()}")
    except Exception as e:
        print(f"[ERROR] Could not write report: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
