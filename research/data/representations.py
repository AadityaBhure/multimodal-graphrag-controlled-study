"""Deterministic Phase 3 normalization. No inference or value imputation."""
from datetime import date
import json
import math
import unicodedata

import pyarrow as pa

RAW_FIELDS = ("Date", "Year", "PaperCitationCount", "PaperRank", "DocType", "JournalId", "JournalDisplayName",
              "ConferenceSeriesId", "ConferenceSeriesDisplayName", "ConferenceInstanceId",
              "ConferenceInstancesDisplayName", "OriginalVenue", "ConferenceSeriesId.1")


def nullable(value):
    if value is None or value == -1 or value == "-1" or value == "" or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def integer(value):
    value = nullable(value)
    if value is None:
        return None
    result = int(value)
    if result != value:
        raise ValueError(f"Non-integral source value: {value!r}")
    return result


def alias(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def venue(row):
    for id_key, name_key, namespace in (
        ("JournalId", "JournalDisplayName", "journal"),
        ("ConferenceSeriesId", "ConferenceSeriesDisplayName", "conference_series"),
        ("ConferenceInstanceId", "ConferenceInstancesDisplayName", "conference_instance"),
    ):
        source_id, name = integer(row.get(id_key)), nullable(row.get(name_key))
        if source_id is not None or name is not None:
            return {"venue_namespace": namespace, "venue_id": str(source_id) if source_id is not None else None,
                    "venue_name": name, "venue_type": namespace}
    name = nullable(row.get("OriginalVenue"))
    if name is not None:
        return {"venue_namespace": "original_venue", "venue_id": None, "venue_name": name, "venue_type": None}
    return {"venue_namespace": None, "venue_id": None, "venue_name": None, "venue_type": None}


def raw_json(row):
    # Reversible JSON for nonfinite source sentinels, without nonstandard NaN literals.
    values = {k: ({"nonfinite_float": repr(row.get(k))} if isinstance(row.get(k), float)
                  and not math.isfinite(row[k]) else row.get(k)) for k in RAW_FIELDS}
    return json.dumps(values, sort_keys=True, ensure_ascii=False, allow_nan=False)


def normalized(node_id, row):
    if row["new_id"] != node_id:
        raise ValueError("Global source ID mismatch")
    typ = row["type"]
    label = row["title"] if typ == "paper" else nullable(row["DisplayName"])
    if label is not None and not isinstance(label, str):
        raise ValueError("Non-string semantic label")
    canonical = {"canonical_id": f"stark:{node_id}", "stark_node_id": node_id,
                 "source_id": integer(row["id"]), "mag_id": integer(row["mag_id"]),
                 "entity_type": typ, "display_name": label}
    graph = {"node_id": node_id, "canonical_id": f"stark:{node_id}", "node_type": typ,
             "label": label, "search_text": label}
    aliases = [] if label is None or not alias(label) else [
        {"alias": alias(label), "canonical_id": f"stark:{node_id}", "stark_node_id": node_id, "entity_type": typ}]
    text, structured = None, None
    if typ == "paper":
        if not isinstance(row["title"], str) or not isinstance(row["abstract"], str):
            raise ValueError("Audited paper text is expected to be present strings")
        text = {"paper_id": node_id, "title": row["title"], "abstract": row["abstract"],
                "content": row["title"] + "\n\n" + row["abstract"]}
        publication_date = nullable(row.get("Date"))
        structured = {"paper_id": node_id, "publication_date": date.fromisoformat(publication_date) if publication_date is not None else None,
                      "publication_year": integer(row.get("Year")), "citation_count": integer(row.get("PaperCitationCount")),
                      "paper_rank": integer(row.get("PaperRank")), "document_type": nullable(row.get("DocType")),
                      **venue(row), "raw_source_json": raw_json(row)}
    return {"canonical": [canonical], "nodes": [graph], "aliases": aliases,
            "text": [text] if text else [], "structured": [structured] if structured else []}


SCHEMAS = {
    "canonical": pa.schema([("canonical_id", pa.string()), ("stark_node_id", pa.int64()), ("source_id", pa.int64()),
                            ("mag_id", pa.int64()), ("entity_type", pa.string()), ("display_name", pa.string())]),
    "nodes": pa.schema([("node_id", pa.int64()), ("canonical_id", pa.string()), ("node_type", pa.string()),
                        ("label", pa.string()), ("search_text", pa.string())]),
    "aliases": pa.schema([("alias", pa.string()), ("canonical_id", pa.string()), ("stark_node_id", pa.int64()), ("entity_type", pa.string())]),
    "text": pa.schema([("paper_id", pa.int64()), ("title", pa.string()), ("abstract", pa.string()), ("content", pa.string())]),
    "structured": pa.schema([("paper_id", pa.int64()), ("publication_date", pa.date32()), ("publication_year", pa.int32()),
                             ("citation_count", pa.int64()), ("paper_rank", pa.int64()), ("document_type", pa.string()),
                             ("venue_namespace", pa.string()), ("venue_id", pa.string()), ("venue_name", pa.string()),
                             ("venue_type", pa.string()), ("raw_source_json", pa.string())]),
    "edges": pa.schema([("edge_id", pa.int64()), ("source_edge_id", pa.int64()), ("source_id", pa.int64()),
                        ("relation", pa.string()), ("relation_id", pa.int8()), ("target_id", pa.int64()), ("derived_inverse", pa.bool_())]),
}
