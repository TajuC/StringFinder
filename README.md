Snippet Finder for .txt files (Python)

Overview
This repository provides a ready to run Python script that searches all accessible disks and directories for a target text inside .txt files. It prints each match with the full file path, the containing directory, and the matching line numbers. A CSV report is also produced for later review.

Capabilities
Automatically discovers drives on Windows and common mount points on Linux and macOS, or you can specify roots manually. Scans only .txt files for speed and reliability. Reads files using robust encoding fallbacks including UTF-8, UTF-16 little endian, UTF-16 big endian, and Windows-1255. Runs work in parallel with a configurable number of threads and shows progress on long scans. Results are printed to the console and written to a CSV file named matches.csv.

Requirements
Python 3.8 or newer. No third-party packages are required.

Installation
Clone the repository and change into the project directory. Creating a virtual environment is optional.

Linux and macOS
```
git clone https://github.com/TajuC/StringFinder
cd <your-repo>
python -m venv .venv
. .venv/bin/activate
```

Windows PowerShell
```
git clone https://github.com/TajuC/StringFinder
cd <your-repo>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Quick start
Run the script with default settings to scan all discovered roots.
```
python find_snippet_txt.py
```

Common usage
Set a custom search string.
```
python find_snippet_txt.py --target "your text here"
```
Limit the scan to specific roots.
```
python find_snippet_txt.py --roots C:\ D:```
```
python find_snippet_txt.py --roots / /mnt/external
```
Tune performance, follow symlinks when needed, choose a different output file.
```
python find_snippet_txt.py --workers 16 --follow-symlinks --output results.csv
```
Adjust the maximum file size to process. The default is 52428800 bytes which is 50 MB.
```
python find_snippet_txt.py --max-file-bytes 104857600
```
Include hidden files and directories on POSIX systems if desired.
```
python find_snippet_txt.py --include-hidden
```

Output example
Console output shows the file and its parent directory and the line numbers where matches were found.
```
[HIT] File: C:\Users\Name\Documents\text\sample.txt
      Dir : C:\Users\Name\Documents\text
      Encoding: utf-8, Lines: 42
```
CSV file matches.csv contains one row per matching line with columns path, encoding, line_number, line_preview.

Options
--target sets the substring to search for. If omitted, the script uses the built in sample text.
--max-file-bytes sets a size limit for files to examine.
--workers sets the number of worker threads.
--follow-symlinks enables traversal through symlinks and junctions.
--include-hidden includes hidden files and directories on POSIX systems.
--roots accepts one or more starting directories or drive roots.
--output sets the CSV output path.

Performance notes
Scanning is limited by disk throughput. Increasing workers overlaps I/O but cannot exceed storage bandwidth. Restricting the scan to a subset of roots reduces total time. Following symlinks can cause redundant traversal and is disabled by default. A sensible maximum file size avoids spending time on very large logs that are unlikely to contain the target string.

Permissions
Some directories require elevated privileges. On Windows, run from an Administrator terminal if you need maximum coverage. On Linux or macOS, use sudo only if necessary.

Troubleshooting
Access denied messages are expected on protected paths; the script continues scanning. If network drives are slow, specify local roots. If you expect matches but none are found, verify exact spacing and punctuation in the target string and confirm the files are plain text with one of the supported encodings.

License
MIT. Add a LICENSE file to the repository if you intend to distribute this project.
