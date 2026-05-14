"""Streaming parser for PubMed/MEDLINE XML.

This module is intentionally self-contained. It is derived from the small
MEDLINE portion of `titipata/pubmed_parser`, with local fixes for this project:

- keep project-specific fields (`history`, `article_date`, `grant_ids`),
- `DeleteCitation` handling,
- avoid dependency on an installed `pubmed_parser` package,
- make missing XML nodes non-fatal where possible.
"""

from __future__ import annotations

import gzip
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from lxml import etree

__all__ = ["parse_medline_xml", "parse_article_info", "parse_grant_id", "split_mesh"]

MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

AFFILIATION_BOILERPLATE = "For a full list of the authors' affiliations please see the Acknowledgements section."


def _text(element: etree._Element | None, default: str = "") -> str:
    if element is None or element.text is None:
        return default
    return element.text.strip()


def _stringify_children(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _month_or_day_formatter(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return value.zfill(2)
    return MONTHS.get(value.lower())


def _open_xml(path: str | Path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return path.open("rb")


def _year_from_date(date: str | None) -> int | None:
    if not date or len(date) < 4:
        return None
    try:
        return int(date[:4])
    except ValueError:
        return None


def parse_pmid(pubmed_article: etree._Element) -> str:
    medline = pubmed_article.find("MedlineCitation")
    if medline is not None:
        pmid = _text(medline.find("PMID"))
        if pmid:
            return pmid

    article_ids = pubmed_article.find("PubmedData/ArticleIdList")
    if article_ids is None:
        return ""
    return _text(article_ids.find('ArticleId[@IdType="pmid"]'))


def parse_doi(pubmed_article: etree._Element) -> str:
    medline = pubmed_article.find("MedlineCitation")
    article = medline.find("Article") if medline is not None else None

    if article is not None:
        for elocation in article.findall("ELocationID"):
            if elocation.attrib.get("EIdType", "").lower() == "doi":
                doi = _text(elocation)
                if doi:
                    return doi

    article_ids = pubmed_article.find("PubmedData/ArticleIdList")
    if article_ids is None:
        return ""
    return _text(article_ids.find('ArticleId[@IdType="doi"]'))


def parse_mesh_terms(medline: etree._Element, parse_subs: bool = False) -> str:
    if parse_subs:
        return parse_mesh_terms_with_subs(medline)

    mesh = medline.find("MeshHeadingList")
    if mesh is None:
        return ""

    terms: list[str] = []
    for heading in mesh:
        descriptor = heading.find("DescriptorName")
        if descriptor is None:
            continue
        terms.append(f"{descriptor.attrib.get('UI', '')}:{_text(descriptor)}")
    return "; ".join(terms)


def parse_mesh_terms_with_subs(medline: etree._Element) -> str:
    mesh = medline.find("MeshHeadingList")
    if mesh is None:
        return ""

    terms: list[str] = []
    for heading in mesh:
        descriptor = heading.find("DescriptorName")
        if descriptor is None:
            continue

        term = f"{descriptor.attrib.get('UI', '')}:{_text(descriptor)}"
        if descriptor.attrib.get("MajorTopicYN", "") == "Y":
            term += "*"

        for qualifier in heading.findall("QualifierName"):
            term += f" / {qualifier.attrib.get('UI', '')}:{_text(qualifier)}"
            if qualifier.attrib.get("MajorTopicYN", "") == "Y":
                term += "*"

        terms.append(term)

    return "; ".join(terms)


def split_mesh(mesh: str) -> list[list[tuple[str, str]]]:
    """Split the compact MeSH representation returned by this parser."""
    if not mesh:
        return []

    parsed: list[list[tuple[str, str]]] = []
    for term in mesh.split("; "):
        if not term:
            continue
        subterms: list[tuple[str, str]] = []
        for subterm in term.split(" / "):
            if ":" not in subterm:
                continue
            ui, descriptor = subterm.split(":", 1)
            subterms.append((ui, descriptor))
        parsed.append(subterms)
    return parsed


def parse_publication_types(medline: etree._Element) -> str:
    publication_type_list = medline.find("Article/PublicationTypeList")
    if publication_type_list is None:
        return ""

    publication_types = []
    for publication_type in publication_type_list.findall("PublicationType"):
        publication_types.append(
            f"{publication_type.attrib.get('UI', '')}:{_text(publication_type)}"
        )
    return "; ".join(publication_types)


def parse_keywords(medline: etree._Element) -> str:
    keyword_list = medline.find("KeywordList")
    if keyword_list is None:
        return ""
    return "; ".join(
        _text(keyword) for keyword in keyword_list.findall("Keyword") if _text(keyword)
    )


def parse_chemical_list(medline: etree._Element) -> str:
    chemicals = medline.find("ChemicalList")
    if chemicals is None:
        return ""

    chemical_list = []
    for chemical in chemicals.findall("Chemical"):
        substance_name = chemical.find("NameOfSubstance")
        if substance_name is not None:
            chemical_list.append(
                f"{substance_name.attrib.get('UI', '')}:{_text(substance_name)}"
            )
    return "; ".join(chemical_list)


def parse_other_id(medline: etree._Element) -> dict[str, str]:
    pmc = ""
    other_ids: list[str] = []
    for other_id in medline.findall("OtherID"):
        value = _text(other_id)
        if not value:
            continue
        if "PMC" in value:
            pmc = value
        else:
            other_ids.append(value)
    return {"pmc": pmc, "other_id": "; ".join(other_ids)}


def parse_journal_info(medline: etree._Element) -> dict[str, str]:
    journal_info = medline.find("MedlineJournalInfo")
    if journal_info is None:
        return {
            "medline_ta": "",
            "nlm_unique_id": "",
            "issn_linking": "",
            "country": "",
        }

    return {
        "medline_ta": _text(journal_info.find("MedlineTA")),
        "nlm_unique_id": _text(journal_info.find("NlmUniqueID")),
        "issn_linking": _text(journal_info.find("ISSNLinking")),
        "country": _text(journal_info.find("Country")),
    }


def parse_grant_id(pubmed_article: etree._Element) -> list[dict[str, str]]:
    medline = pubmed_article.find("MedlineCitation")
    article = medline.find("Article") if medline is not None else None
    grants = article.find("GrantList") if article is not None else None
    if grants is None:
        return []

    grant_list: list[dict[str, str]] = []
    for grant in grants:
        grant_list.append(
            {
                "grant_id": _text(grant.find("GrantID")),
                "grant_acronym": _text(grant.find("Acronym")),
                "country": _text(grant.find("Country")),
                "agency": _text(grant.find("Agency")),
            }
        )
    return grant_list


def parse_author_affiliation(medline: etree._Element) -> list[dict[str, str]]:
    article = medline.find("Article")
    author_list = article.find("AuthorList") if article is not None else None
    if author_list is None:
        return []

    authors: list[dict[str, str]] = []
    for author in author_list.findall("Author"):
        affiliations = []
        for affiliation in author.findall("AffiliationInfo/Affiliation"):
            value = _text(affiliation).replace(AFFILIATION_BOILERPLATE, "").strip()
            if value:
                affiliations.append(value)

        authors.append(
            {
                "lastname": _text(author.find("LastName")),
                "forename": _text(author.find("ForeName")),
                "initials": _text(author.find("Initials")),
                "identifier": _text(author.find("Identifier")),
                "affiliation": "|".join(affiliations),
            }
        )
    return authors


def date_extractor(journal: etree._Element | None, year_info_only: bool) -> str:
    if journal is None:
        return ""

    issue = journal.find("JournalIssue")
    issue_date = issue.find("PubDate") if issue is not None else None
    if issue_date is None:
        return ""

    year = ""
    month = None
    day = None

    year_el = issue_date.find("Year")
    if year_el is not None:
        year = _text(year_el)
        if not year_info_only:
            month = _month_or_day_formatter(_text(issue_date.find("Month")))
            day = _month_or_day_formatter(_text(issue_date.find("Day")))
    else:
        medline_date = _text(issue_date.find("MedlineDate"))
        years = re.findall(r"\d{4}", medline_date)
        if years:
            year = years[0]

    if year_info_only or month is None:
        return year
    return "-".join(str(part) for part in [year, month, day] if part)


def history_extractor(pubmed_article: etree._Element) -> dict[str, str]:
    history = pubmed_article.find(".//History")
    if history is None:
        return {}

    date_dict: dict[str, str] = {}
    for pub_date in history.findall("PubMedPubDate"):
        pub_status = pub_date.get("PubStatus")
        year = _text(pub_date.find("Year"))
        month = _month_or_day_formatter(_text(pub_date.find("Month")))
        day = _month_or_day_formatter(_text(pub_date.find("Day")))
        if pub_status and year and month and day:
            date_dict[pub_status] = f"{year}-{month}-{day}"
    return date_dict


def article_date(pubmed_article: etree._Element) -> str | None:
    article_date_el = pubmed_article.find(".//ArticleDate")
    if article_date_el is None:
        return None

    year = _text(article_date_el.find("Year"))
    month = _month_or_day_formatter(_text(article_date_el.find("Month")))
    day = _month_or_day_formatter(_text(article_date_el.find("Day")))
    if year and month and day:
        return f"{year}-{month}-{day}"
    return None


def parse_references(
    pubmed_article: etree._Element, reference_list: bool
) -> list[dict[str, str]] | str:
    references: list[dict[str, str]] = []
    reference_list_data = pubmed_article.find("PubmedData/ReferenceList")
    if reference_list_data is not None:
        for ref in reference_list_data.findall("Reference"):
            article_ids = ref.find("ArticleIdList")
            pmid = (
                _text(article_ids.find('ArticleId[@IdType="pubmed"]'))
                if article_ids is not None
                else ""
            )
            references.append({"citation": _text(ref.find("Citation")), "pmid": pmid})

    if reference_list:
        return references
    return ";".join(ref["pmid"] for ref in references if ref["pmid"])


def parse_article_info(
    pubmed_article: etree._Element,
    year_info_only: bool,
    nlm_category: bool,
    author_list: bool,
    reference_list: bool,
    parse_subs: bool = False,
) -> dict[str, Any]:
    medline = pubmed_article.find("MedlineCitation")
    if medline is None:
        raise ValueError("PubmedArticle missing MedlineCitation")

    article = medline.find("Article")
    if article is None:
        raise ValueError("MedlineCitation missing Article")

    journal = article.find("Journal")

    title = _stringify_children(article.find("ArticleTitle"))
    volume = _text(article.find("Journal/JournalIssue/Volume"))
    issue = _text(article.find("Journal/JournalIssue/Issue"))
    issue = f"{volume}({issue})" if volume else ""
    pages = _text(article.find("Pagination/MedlinePgn"))
    languages = ";".join(
        _text(language) for language in article.findall("Language") if _text(language)
    )
    vernacular_title = _stringify_children(article.find("VernacularTitle"))

    category = "NlmCategory" if nlm_category else "Label"
    if article.find("Abstract/AbstractText") is not None:
        abstract_nodes = article.findall("Abstract/AbstractText")
        if len(abstract_nodes) > 1:
            parts: list[str] = []
            for abstract_node in abstract_nodes:
                section = abstract_node.attrib.get(category, "")
                if section and section != "UNASSIGNED":
                    parts.extend(["\n", section])
                section_text = _stringify_children(abstract_node)
                if section_text:
                    parts.append(section_text)
            abstract = "\n".join(parts).strip()
        else:
            abstract = _stringify_children(abstract_nodes[0])
    else:
        abstract = _stringify_children(article.find("Abstract"))

    authors_dict = parse_author_affiliation(medline)
    if author_list:
        authors: str | list[dict[str, str]] = authors_dict
        affiliations = None
    else:
        affiliations = ";".join(
            author["affiliation"]
            for author in authors_dict
            if author.get("affiliation")
        )
        authors = ";".join(
            "|".join(
                [
                    author.get("lastname", ""),
                    author.get("forename", ""),
                    author.get("initials", ""),
                    author.get("identifier", ""),
                ]
            )
            for author in authors_dict
        )

    journal_name = (
        " ".join(journal.xpath("Title/text()")) if journal is not None else ""
    )

    dict_out: dict[str, Any] = {
        "title": title,
        "issue": issue,
        "pages": pages,
        "abstract": abstract,
        "journal": journal_name,
        "authors": authors,
        "pubdate": date_extractor(journal, year_info_only),
        "article_date": article_date(pubmed_article),
        "history": history_extractor(pubmed_article),
        "pmid": parse_pmid(pubmed_article),
        "mesh_terms": parse_mesh_terms(medline, parse_subs=parse_subs),
        "publication_types": parse_publication_types(medline),
        "chemical_list": parse_chemical_list(medline),
        "keywords": parse_keywords(medline),
        "doi": parse_doi(pubmed_article),
        "references": parse_references(pubmed_article, reference_list),
        "grant_ids": parse_grant_id(pubmed_article),
        "delete": False,
        "languages": languages,
        "vernacular_title": vernacular_title,
    }
    if affiliations is not None:
        dict_out["affiliations"] = affiliations
    dict_out.update(parse_other_id(medline))
    dict_out.update(parse_journal_info(medline))
    return dict_out


def parse_medline_xml(
    path: str | Path,
    year_info_only: bool = True,
    nlm_category: bool = False,
    author_list: bool = False,
    reference_list: bool = False,
    parse_downto_mesh_subterms: bool = False,
    min_pub_year: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream MEDLINE XML records from `.xml` or `.xml.gz` files.

    `min_pub_year` is provided for convenience, but should be treated as a
    pipeline-level filter. Leave it as `None` for lossless parsing.
    """
    with _open_xml(path) as handle:
        context = etree.iterparse(handle, events=("end",), recover=True)
        for _, element in context:
            if element.tag == "DeleteCitation":
                for child in element.iterchildren():
                    if child.tag == "PMID":
                        yield {"pmid": _text(child), "delete": True}
                element.clear()
                continue

            if element.tag != "PubmedArticle":
                continue

            record = parse_article_info(
                element,
                year_info_only=year_info_only,
                nlm_category=nlm_category,
                author_list=author_list,
                reference_list=reference_list,
                parse_subs=parse_downto_mesh_subterms,
            )
            element.clear()

            if min_pub_year is not None:
                year = _year_from_date(record.get("pubdate"))
                if year is None or year < min_pub_year:
                    continue

            yield record
