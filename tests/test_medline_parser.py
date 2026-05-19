from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from lxml import etree

from pubdelays.cli import main, parse_md5_sidecar
from pubdelays.parser.medline import parse_medline_xml


def write_gz(path: Path, text: str) -> Path:
    with gzip.open(path, "wb") as handle:
        handle.write(text.encode("utf-8"))
    return path


def write_xml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def sample_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1</PMID>
      <Article>
        <Journal>
          <ISSN IssnType="Print">1234-5678</ISSN>
          <JournalIssue>
            <Volume>12</Volume>
            <Issue>3</Issue>
            <PubDate><Year>2017</Year><Month>Jan</Month><Day>5</Day></PubDate>
          </JournalIssue>
          <Title>Example Journal</Title>
        </Journal>
        <ArticleTitle>Example <i>title</i></ArticleTitle>
        <Pagination><MedlinePgn>1-4</MedlinePgn></Pagination>
        <Abstract><AbstractText Label="BACKGROUND">A result.</AbstractText></Abstract>
        <AuthorList>
          <Author>
            <LastName>Doe</LastName><ForeName>Jane</ForeName><Initials>J</Initials>
            <AffiliationInfo><Affiliation>Institute A</Affiliation></AffiliationInfo>
            <AffiliationInfo><Affiliation>Institute B</Affiliation></AffiliationInfo>
          </Author>
        </AuthorList>
        <Language>eng</Language>
        <ELocationID EIdType="doi">10.123/example</ELocationID>
        <ArticleDate><Year>2016</Year><Month>12</Month><Day>31</Day></ArticleDate>
        <PublicationTypeList><PublicationType UI="D016428">Journal Article</PublicationType></PublicationTypeList>
        <GrantList><Grant><GrantID>G1</GrantID><Agency>Agency</Agency><Country>Hungary</Country></Grant></GrantList>
      </Article>
      <MedlineJournalInfo>
        <MedlineTA>Example J</MedlineTA><NlmUniqueID>NLM1</NlmUniqueID><ISSNLinking>1234-5678</ISSNLinking><Country>Hungary</Country>
      </MedlineJournalInfo>
      <MeshHeadingList>
        <MeshHeading>
          <DescriptorName UI="D000001" MajorTopicYN="Y">Term</DescriptorName>
          <QualifierName UI="Q000001" MajorTopicYN="N">qualifier</QualifierName>
        </MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <History>
        <PubMedPubDate PubStatus="received"><Year>2016</Year><Month>10</Month><Day>1</Day></PubMedPubDate>
        <PubMedPubDate PubStatus="accepted"><Year>2016</Year><Month>11</Month><Day>2</Day></PubMedPubDate>
      </History>
      <ArticleIdList><ArticleId IdType="pmid">1</ArticleId><ArticleId IdType="doi">10.123/fallback</ArticleId></ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>2</PMID>
      <Article>
        <Journal><JournalIssue><PubDate><MedlineDate>2015 Winter-2016 Spring</MedlineDate></PubDate></JournalIssue><Title>Old Journal</Title></Journal>
        <ArticleTitle>Old article</ArticleTitle>
        <ELocationID EIdType="pii">S1</ELocationID>
        <ArticleDate><Year>2014</Year><Month>12</Month></ArticleDate>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList><ArticleId IdType="doi">10.123/fallback-only</ArticleId></ArticleIdList></PubmedData>
  </PubmedArticle>
  <DeleteCitation><PMID>3</PMID></DeleteCitation>
</PubmedArticleSet>
"""


def test_parse_custom_fields_and_delete_citation(tmp_path: Path) -> None:
    xml_path = write_gz(tmp_path / "sample.xml.gz", sample_xml())
    records = list(
        parse_medline_xml(
            xml_path,
            year_info_only=False,
            parse_downto_mesh_subterms=True,
        )
    )

    assert len(records) == 3
    article = records[0]
    assert article["pmid"] == "1"
    assert article["pubdate"] == "2017-01-05"
    assert article["article_date"] == "2016-12-31"
    assert article["history"] == {"received": "2016-10-01", "accepted": "2016-11-02"}
    assert article["grant_ids"] == [
        {
            "grant_id": "G1",
            "grant_acronym": "",
            "country": "Hungary",
            "agency": "Agency",
        }
    ]
    assert article["affiliations"] == "Institute A|Institute B"
    assert article["doi"] == "10.123/example"
    assert article["mesh_terms"] == "D000001:Term* / Q000001:qualifier"
    assert records[1]["pubdate"] == "2015"
    assert records[1]["article_date"] is None
    assert records[1]["doi"] == "10.123/fallback-only"
    assert records[2] == {"pmid": "3", "delete": True}


def test_plain_xml_streams_without_gzip(tmp_path: Path) -> None:
    xml_path = write_xml(tmp_path / "sample.xml", sample_xml())
    records = list(parse_medline_xml(xml_path))
    assert [record["pmid"] for record in records] == ["1", "2", "3"]



def test_min_pub_year_is_explicit_filter(tmp_path: Path) -> None:
    xml_path = write_gz(tmp_path / "sample.xml.gz", sample_xml())
    records = list(parse_medline_xml(xml_path, min_pub_year=2016))
    assert [record["pmid"] for record in records] == ["1", "3"]


def test_malformed_xml_fails_fast_unless_recovery_is_enabled(tmp_path: Path) -> None:
    malformed_xml = sample_xml().replace("</PubmedArticleSet>", "")
    xml_path = write_xml(tmp_path / "malformed.xml", malformed_xml)

    with pytest.raises(etree.XMLSyntaxError):
        list(parse_medline_xml(xml_path))

    recovered = list(parse_medline_xml(xml_path, recover=True))
    assert [record["pmid"] for record in recovered] == ["1", "2", "3"]


def test_untrusted_xml_does_not_expand_external_entities(tmp_path: Path) -> None:
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("LEAKED_FROM_HOST", encoding="utf-8")
    xml_path = write_xml(
        tmp_path / "xxe.xml",
        f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE PubmedArticleSet [<!ENTITY xxe SYSTEM "{secret_path.as_uri()}">]>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1</PMID>
      <Article>
        <Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>
        <ArticleTitle>prefix-&xxe;-suffix</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
''',
    )

    record = list(parse_medline_xml(xml_path, recover=True))[0]

    assert "LEAKED_FROM_HOST" not in record["title"]


def test_cli_parse_jsonl(tmp_path: Path) -> None:
    input_dir = tmp_path / "xml"
    output_dir = tmp_path / "jsonl"
    input_dir.mkdir()
    write_gz(input_dir / "sample.xml.gz", sample_xml())
    manifest_path = tmp_path / "manifest.sqlite"

    exit_code = main(
        [
            "parse",
            "--manifest",
            str(manifest_path),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--jobs",
            "1",
            "--format",
            "jsonl",
            "--parse-mesh-subterms",
        ]
    )
    assert exit_code == 0

    output_path = output_dir / "sample.xml.gz.jsonl"
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3
    assert rows[0]["history"]["accepted"] == "2016-11-02"

    validate_code = main(["validate", "--manifest", str(manifest_path), str(output_dir)])
    assert validate_code == 0


def test_cli_parse_recover_malformed_xml(tmp_path: Path) -> None:
    input_dir = tmp_path / "xml"
    output_dir = tmp_path / "jsonl"
    input_dir.mkdir()
    write_xml(input_dir / "malformed.xml", sample_xml().replace("</PubmedArticleSet>", ""))

    strict_code = main(
        [
            "parse",
            "--manifest",
            str(tmp_path / "strict.sqlite"),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--jobs",
            "1",
        ]
    )
    assert strict_code == 1
    assert not (output_dir / "malformed.xml.jsonl").exists()

    recover_code = main(
        [
            "parse",
            "--manifest",
            str(tmp_path / "recover.sqlite"),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--jobs",
            "1",
            "--recover-malformed-xml",
        ]
    )
    assert recover_code == 0
    rows = [
        json.loads(line)
        for line in (output_dir / "malformed.xml.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["pmid"] for row in rows] == ["1", "2", "3"]



def test_parse_md5_sidecar_formats() -> None:
    digest = "d41d8cd98f00b204e9800998ecf8427e"
    assert parse_md5_sidecar(f"{digest}  pubmed25n0001.xml.gz") == (
        digest,
        "pubmed25n0001.xml.gz",
    )
    assert parse_md5_sidecar(f"MD5 (pubmed25n0001.xml.gz) = {digest}") == (
        digest,
        "pubmed25n0001.xml.gz",
    )
