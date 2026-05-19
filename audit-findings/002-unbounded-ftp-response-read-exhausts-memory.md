# Unbounded FTP Response Read Exhausts Memory

## Classification

Denial of service, medium severity.

## Affected Locations

`legacy/data_processing/pubmed_journals.py:9`

## Summary

`legacy/data_processing/pubmed_journals.py` fetches `ftp://ftp.ncbi.nih.gov/pubmed/J_Medline.txt` and reads the entire FTP response into memory with `response.read().decode('utf-8')`. Because the FTP response is unauthenticated, integrity-unprotected, and unbounded before allocation, a malicious FTP mirror or network attacker can provide an oversized response that exhausts process memory and causes denial of service.

## Provenance

Verified and reproduced from Swival.dev Security Scanner findings: https://swival.dev

Confidence: certain.

## Preconditions

- The script is run.
- An attacker controls the FTP response body, either through a malicious PubMed FTP mirror or by intercepting/modifying the unauthenticated FTP session.

## Proof

The affected script opens the hardcoded FTP URL:

```python
ftp_url = 'ftp://ftp.ncbi.nih.gov/pubmed/J_Medline.txt'

with urllib.request.urlopen(ftp_url) as response:
    data = response.read().decode('utf-8')
```

`response.read()` is called without a maximum byte count. This allocates the full attacker-controlled response body as a bytes object before any parsing or validation. `.decode('utf-8')` then allocates a decoded string, and the later `data.split('\n')` creates another large list of strings.

An oversized FTP response can therefore cause excessive memory allocation, process termination, or job hang.

## Why This Is A Real Bug

The data source uses FTP, which does not authenticate the server response or provide transport integrity. Under the stated preconditions, the response body is attacker-controlled.

The code performs an unbounded read before any size check:

```python
response.read()
```

This is a concrete memory-exhaustion primitive because the process attempts to materialize the entire remote response in memory. The reproduced propagation path confirms the failing operation and impact.

## Fix Requirement

The script must not read an unbounded remote response into memory. It must either:

- Stream and process the response in bounded chunks, or
- Enforce a maximum response size before decoding and parsing.

## Patch Rationale

The patch enforces a fixed maximum FTP response size:

```python
MAX_FTP_RESPONSE_BYTES = 10 * 1024 * 1024
```

It then reads at most one byte beyond that limit:

```python
raw_data = response.read(MAX_FTP_RESPONSE_BYTES + 1)
```

If the response exceeds the configured maximum, the script raises an error before decoding or splitting:

```python
if len(raw_data) > MAX_FTP_RESPONSE_BYTES:
    raise ValueError('FTP response exceeds maximum allowed size')
```

This prevents unbounded allocation while preserving the existing parsing behavior for responses within the expected size.

## Residual Risk

None

## Patch

```diff
diff --git a/legacy/data_processing/pubmed_journals.py b/legacy/data_processing/pubmed_journals.py
index 87b234f..a2f1f6c 100644
--- a/legacy/data_processing/pubmed_journals.py
+++ b/legacy/data_processing/pubmed_journals.py
@@ -3,10 +3,14 @@ import urllib.request

 # FTP URL
 ftp_url = 'ftp://ftp.ncbi.nih.gov/pubmed/J_Medline.txt'
+MAX_FTP_RESPONSE_BYTES = 10 * 1024 * 1024

 # Fetch data from FTP
 with urllib.request.urlopen(ftp_url) as response:
-    data = response.read().decode('utf-8')
+    raw_data = response.read(MAX_FTP_RESPONSE_BYTES + 1)
+    if len(raw_data) > MAX_FTP_RESPONSE_BYTES:
+        raise ValueError('FTP response exceeds maximum allowed size')
+    data = raw_data.decode('utf-8')

 # Initialize CSV writer
 keys = ['JrId', 'JournalTitle', 'MedAbbr', 'ISSN (Print)', 'ISSN (Online)', 'IsoAbbr', 'NlmId']
```
