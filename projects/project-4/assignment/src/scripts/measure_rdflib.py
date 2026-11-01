from pathlib import Path
from urllib.parse import quote
from decimal import Decimal

import pandas as pd
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

# File locations
SRC = Path(__file__).resolve().parents[1]
INPUT = SRC / "data" / "readings_normalized.csv"
OUTPUT = SRC / "measure_cco.ttl"

EX = Namespace("http://example.org/measurements/")
BFO = Namespace("http://purl.obolibrary.org/obo/")

# Read the provided ontology to find its actual term IRIs.
ontology = Graph()
ontology.parse(SRC / "cco_merged.ttl", format="turtle")


def find_term(label):
    matches = {
        subject
        for subject, text in ontology.subject_objects(RDFS.label)
        if str(text).casefold() == label.casefold()
    }
    if len(matches) != 1:
        raise ValueError(f"Expected one term for {label!r}, found {matches}")
    return matches.pop()


ARTIFACT = find_term("Material Artifact")
SDC = BFO.BFO_0000020
MICE = find_term("Measurement Information Content Entity")
UNIT = find_term("Measurement Unit")

BEARER_OF = find_term("bearer of")
MEASURES = find_term("is a measurement of")
USES_UNIT = find_term("uses measurement unit")
HAS_VALUE = find_term("has decimal value")

# Start the output graph.
g = Graph()
g.bind("ex", EX)
g.bind("bfo", BFO)
g.bind("cco", Namespace("https://www.commoncoreontologies.org/"))

g.add((EX.ontology, RDF.type, OWL.Ontology))
g.add((
    EX.ontology,
    RDFS.label,
    Literal("Sensor measurement ontology", lang="en"),
))

df = pd.read_csv(INPUT, dtype=str)

for index, row in df.iterrows():
    artifact_id = row["artifact_id"]
    kind = row["sdc_kind"]
    unit_label = row["unit_label"]

    # Reuse the artifact, its measured quality, and the unit.
    artifact = EX[f"artifact/{quote(artifact_id, safe='')}"]
    sdc = EX[
        f"sdc/{quote(artifact_id, safe='')}/{quote(kind, safe='')}"
    ]
    unit = EX[f"unit/{quote(unit_label, safe='')}"]

    # Create a separate measurement individual for each CSV row.
    measurement = EX[f"measurement/{index + 1}"]

    # Types
    g.add((artifact, RDF.type, ARTIFACT))
    g.add((sdc, RDF.type, SDC))
    g.add((measurement, RDF.type, MICE))
    g.add((unit, RDF.type, UNIT))

    # Relationships from the diagram
    g.add((artifact, BEARER_OF, sdc))
    g.add((measurement, MEASURES, sdc))
    g.add((measurement, USES_UNIT, unit))
    g.add((
        measurement,
        HAS_VALUE,
        Literal(Decimal(row["value"]), datatype=XSD.decimal),
    ))

    # Preserve the timestamp using a local annotation property.
    g.add((
        measurement,
        EX.recordedAt,
        Literal(row["timestamp"], datatype=XSD.dateTime),
    ))

    # Human-readable, distinct labels
    g.add((artifact, RDFS.label, Literal(artifact_id, lang="en")))
    g.add((
        sdc,
        RDFS.label,
        Literal(f"{artifact_id} {kind}", lang="en"),
    ))
    g.add((
        measurement,
        RDFS.label,
        Literal(f"Measurement {index + 1}", lang="en"),
    ))
    g.add((unit, RDFS.label, Literal(unit_label, lang="en")))

g.add((EX.recordedAt, RDF.type, OWL.AnnotationProperty))
g.add((
    EX.recordedAt,
    RDFS.label,
    Literal("recorded at", lang="en"),
))

g.serialize(destination=OUTPUT, format="turtle")

print(f"Created {len(df)} measurement individuals.")
print(f"Wrote {len(g)} triples to {OUTPUT}")