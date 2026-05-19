# Remote Download Link Escapes Output Directory

## Classification

Path traversal, high severity.

## Affected Locations

`src/pubdelays/cli.py:607`

## Summary

`cmd_download()` trusted `href` values parsed from the remote PubMed index and used each link directly as a filesystem path component. A malicious listing could provide `../escaped.gz` or `/tmp/escaped.gz`; `output_dir / link` would then resolve outside the configured PubMed output directory, and `download_file()` would create parent directories and write the downloaded response there.

## Provenance

Verified and reproduced from a Swival.dev Security Scanner finding: https://swival.dev

Confidence: certain.

## Preconditions

- User runs the `download` command.
- The PubMed index HTML returned to the downloader is attacker-controlled or malicious.
- The malicious `href` ends in `.gz` or `.md5`, satisfying the existing `index_links()` regex.

## Proof

`index_links()` accepts any `href` ending in `.gz` or `.md5`:

```python
return sorted(set(re.findall(r'href="([^"]+\.(?:gz|md5))"', html)))
```

`cmd_download()` previously passed that value directly into the output path:

```python
executor.submit(download_file, base_url + link, output_dir / link, resume=args.resume)
```

This is unsafe because:

- `Path(output_dir) / "../escaped.gz"` escapes the output directory.
- `Path(output_dir) / "/tmp/escaped.gz"` discards `output_dir` entirely.
- `download_file()` creates `output_path.parent`.
- `download_file()` writes through `atomic_output_path(output_path)`.
- `atomic_output_path()` atomically replaces the attacker-selected final path.
- The later MD5 failure scan only checks `output_dir.glob("*.md5")`, so escaped files are not reliably caught by verification.

A malicious listing entry such as `href="../escaped.gz"` can therefore cause an attacker-controlled `.gz` or `.md5` response body to be written outside the configured PubMed download directory.

## Why This Is A Real Bug

The vulnerable path is reachable during normal `download` execution and requires only a malicious remote index entry matching the existing accepted suffixes. `pathlib` path joining does not confine untrusted relative or absolute paths to the intended directory. The sink performs filesystem creation and atomic replacement at the derived path, giving the attacker control over a write destination outside the expected containment boundary.

## Fix Requirement

Reject unsafe remote links before submitting downloads:

- Reject absolute paths.
- Reject paths whose resolved destination is not under the resolved output directory.
- Only submit downloads whose destination remains contained by `output_dir`.

## Patch Rationale

The patch resolves the configured output directory once, builds candidate output paths for each link, and validates each candidate before download submission:

```python
output_root = output_dir.resolve()
download_paths = []
for link in links:
    output_path = output_dir / link
    try:
        if Path(link).is_absolute():
            raise ValueError
        output_path.resolve().relative_to(output_root)
    except ValueError:
        err(f"unsafe download link: {link}")
        return 1
    download_paths.append((link, output_path))
```

This prevents both absolute-path replacement and `..` traversal because only paths whose resolved location is relative to `output_root` are accepted. The executor then uses the validated `(link, output_path)` pairs rather than recomputing paths from untrusted input.

## Residual Risk

None

## Patch

```diff
diff --git a/src/pubdelays/cli.py b/src/pubdelays/cli.py
index b9888a1..3441e91 100644
--- a/src/pubdelays/cli.py
+++ b/src/pubdelays/cli.py
@@ -628,10 +628,22 @@ def cmd_download(args: argparse.Namespace) -> int:

     downloaded = 0
     skipped = 0
+    output_root = output_dir.resolve()
+    download_paths = []
+    for link in links:
+        output_path = output_dir / link
+        try:
+            if Path(link).is_absolute():
+                raise ValueError
+            output_path.resolve().relative_to(output_root)
+        except ValueError:
+            err(f"unsafe download link: {link}")
+            return 1
+        download_paths.append((link, output_path))
     with ThreadPoolExecutor(max_workers=jobs) as executor:
         futures = [
-            executor.submit(download_file, base_url + link, output_dir / link, resume=args.resume)
-            for link in links
+            executor.submit(download_file, base_url + link, output_path, resume=args.resume)
+            for link, output_path in download_paths
         ]
         for future in as_completed(futures):
             stats = future.result()
```
