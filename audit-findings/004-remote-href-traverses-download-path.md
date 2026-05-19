# Remote Href Traverses Download Path

## Classification

Path traversal, medium severity. Confidence: certain.

## Affected Locations

`legacy/data_processing/get_and_verify_pubmed_xml.sh:21`

## Summary

The script parses remote `href` values from the PubMed baseline directory listing and uses each captured value directly in a local `curl -o "$DOWNLOAD_DIR/{}"` output path. Before the patch, the capture allowed `/` path separators, so an attacker-controlled listing could provide traversal paths such as `../outside/victim.gz` and cause writes outside the intended XML download directory.

## Provenance

Reported by Swival.dev Security Scanner: https://swival.dev

## Preconditions

The script fetches an attacker-controlled or malicious baseline directory listing from the HTTPS endpoint.

## Proof

At `legacy/data_processing/get_and_verify_pubmed_xml.sh:21`, the original pipeline extracted any `href` ending in `.gz` or `.md5`:

```sh
grep -oP '(?<=href=")[^"]*\.(gz|md5)'
```

That value was passed unchanged through `xargs` into:

```sh
curl -o "$DOWNLOAD_DIR/{}" https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/{}
```

An attacker-controlled listing containing:

```html
<a href="../outside/victim.gz">x</a>
```

would produce the local output path:

```text
/users/zsimi/pubdelays/data/raw_data/pubmed/xmls/../outside/victim.gz
```

The local filesystem resolves `..`, so `curl -o` writes outside `DOWNLOAD_DIR` if the destination parent directory exists and is writable.

The reproducer confirmed the equivalent path behavior: writing to `download/../outside/victim.gz` overwrites `outside/victim.gz`.

## Why This Is A Real Bug

The vulnerable value crosses directly from remote HTML into a filesystem output path without basename normalization or separator validation. The `.gz` or `.md5` suffix filter does not prevent traversal because filenames like `../outside/victim.gz` still match. Under the stated precondition, this gives the remote listing control over a writable output location outside the intended download directory.

## Fix Requirement

Reject path separators in remote filenames before constructing local output paths, or normalize each remote value to a basename and only write that basename under `DOWNLOAD_DIR`.

## Patch Rationale

The patch changes the extraction regex from:

```sh
(?<=href=")[^"]*\.(gz|md5)
```

to:

```sh
(?<=href=")[^"/]*\.(gz|md5)
```

This prevents captured `href` values from containing `/`. Because `../outside/victim.gz` requires path separators, it is no longer accepted by the pipeline and cannot be substituted into `"$DOWNLOAD_DIR/{}"` as a traversal path.

## Residual Risk

None

## Patch

```diff
diff --git a/legacy/data_processing/get_and_verify_pubmed_xml.sh b/legacy/data_processing/get_and_verify_pubmed_xml.sh
index b4194d3..e9dab09 100755
--- a/legacy/data_processing/get_and_verify_pubmed_xml.sh
+++ b/legacy/data_processing/get_and_verify_pubmed_xml.sh
@@ -18,7 +18,7 @@ mkdir -p $DOWNLOAD_DIR
 START_TIME=$(date +%s)

 # Use wget with FTP options to download all files and log any errors
-curl -s https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/ | grep -oP '(?<=href=")[^"]*\.(gz|md5)' | xargs -n 1 -P 4 -I {} curl -o "$DOWNLOAD_DIR/{}" https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/{}
+curl -s https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/ | grep -oP '(?<=href=")[^"/]*\.(gz|md5)' | xargs -n 1 -P 4 -I {} curl -o "$DOWNLOAD_DIR/{}" https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/{}

 # curl -s https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/ | grep -oP '(?<=href=")[^"]*\.(gz|md5)' | xargs -n 1 -P 4 -I {} curl -o "$DOWNLOAD_DIR/{}" https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/{}
```
