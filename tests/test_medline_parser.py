from __future__ import annotations

import gzip
import json
from pathlib import Path

from pubdelays.cli import main, parse_md5_sidecar
from pubdelays.parser.medline import parse_medline_xml


def write_gz(path: Path, text: str) -> Path:
    with gzip.open(path, "wb") as handle:
        handle.write(text.encode("utf-8"))
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
        <Journal><JournalIssue><PubDate><Year>2015</Year></PubDate></JournalIssue><Title>Old Journal</Title></Journal>
        <ArticleTitle>Old article</ArticleTitle>
      </Article>
    </MedlineCitation>
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
    assert records[2] == {"pmid": "3", "delete": True}


def test_min_pub_year_is_explicit_filter(tmp_path: Path) -> None:
    xml_path = write_gz(tmp_path / "sample.xml.gz", sample_xml())
    records = list(parse_medline_xml(xml_path, min_pub_year=2016))
    assert [record["pmid"] for record in records] == ["1", "3"]


def test_cli_parse_jsonl(tmp_path: Path) -> None:
    input_dir = tmp_path / "xml"
    output_dir = tmp_path / "jsonl"
    input_dir.mkdir()
    write_gz(input_dir / "sample.xml.gz", sample_xml())

    exit_code = main(
        [
            "parse",
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
    rows = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 3
    assert rows[0]["history"]["accepted"] == "2016-11-02"

    validate_code = main(["validate", str(output_dir)])
    assert validate_code == 0


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
