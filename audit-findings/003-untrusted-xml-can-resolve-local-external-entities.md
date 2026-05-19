# Untrusted XML Can Resolve Local External Entities

## Classification

High severity information disclosure via XML External Entity expansion.

## Affected Locations

`src/pubdelays/parser/medline.py:476`

## Summary

`parse_medline_xml` parsed attacker-supplied MEDLINE XML with `lxml.etree.iterparse` without disabling DTD loading or entity resolution. A malicious XML document could define a local `file://` external entity and reference it inside parsed article text. The expanded file contents were returned in publication records and could also be written by the CLI JSONL output path.

## Provenance

Reproduced and patched from a verified Swival.dev Security Scanner finding: https://swival.dev

Confidence: certain.

## Preconditions

- The parser processes attacker-supplied MEDLINE XML.
- The host running the parser has readable local files.
- The attacker can place an external entity reference in a parsed article text field such as `ArticleTitle`, `AbstractText`, or similar.

## Proof

The vulnerable flow was:

- `parse_medline_xml(...)` opens the supplied XML path.
- It passed the file handle directly to `lxml.etree.iterparse(...)` without `load_dtd=False` or `resolve_entities=False`.
- A malicious XML document defined `<!ENTITY xxe SYSTEM "file:///tmp/.../secret.txt">`.
- The entity was referenced as `<ArticleTitle>prefix-&xxe;-suffix</ArticleTitle>`.
- During parsing, the external entity was expanded.
- `_stringify_children(...).itertext()` collected the expanded text.
- The returned record contained `"title": "prefix-LEAKED_FROM_HOST_FILE-suffix"`.
- The CLI `parse` command propagated the leaked value into `evil.xml.jsonl`.

## Why This Is A Real Bug

This is exploitable because the parser accepts XML content and converts parsed text fields into caller-visible records. `lxml` can resolve local external entities when entity resolution is not explicitly disabled. The reproduced payload caused host file contents to appear in the returned publication record, proving confidentiality impact rather than a theoretical parser-hardening issue.

## Fix Requirement

Configure XML parsing so untrusted documents cannot load DTDs or resolve external entities.

Required parser behavior:

- Do not load DTDs.
- Do not resolve entities.
- Preserve existing streaming parse behavior.
- Preserve existing `recover` behavior for explicit salvage runs.

## Patch Rationale

The patch updates `etree.iterparse(...)` in `parse_medline_xml` to pass:

- `load_dtd=False`
- `resolve_entities=False`

This directly blocks the vulnerable mechanism while keeping the existing event-driven streaming parse and `recover` option unchanged.

## Residual Risk

None

## Patch

```diff
diff --git a/src/pubdelays/parser/medline.py b/src/pubdelays/parser/medline.py
index d1f4326..a69c2cc 100644
--- a/src/pubdelays/parser/medline.py
+++ b/src/pubdelays/parser/medline.py
@@ -495,7 +495,13 @@ def parse_medline_xml(
     pipeline-level filter. Leave it as `None` for lossless parsing.
     """
     with _open_xml(path) as handle:
-        context = etree.iterparse(handle, events=("end",), recover=recover)
+        context = etree.iterparse(
+            handle,
+            events=("end",),
+            recover=recover,
+            load_dtd=False,
+            resolve_entities=False,
+        )
         for _, element in context:
             if element.tag == "DeleteCitation":
                 for child in element.iterchildren():
```
