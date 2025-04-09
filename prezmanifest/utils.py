from collections.abc import Generator
from enum import Enum
from pathlib import Path

import httpx
from dateutil.parser import parse as date_parse
from kurra.db import sparql
from kurra.file import load_graph
from kurra.sparql import query
from rdflib import BNode, Dataset, Graph, Literal, Node, URIRef
from rdflib.namespace import DCAT, OWL, PROF, RDF, SDO, SKOS

import prezmanifest
from prezmanifest.definednamespaces import MRR, PREZ

KNOWN_PROFILES = {
    URIRef("http://www.opengis.net/def/geosparql"): {
        "path": Path(__file__).parent / "validator-geosparql-1.1.ttl",
        "main_entity_classes": [SDO.Dataset, DCAT.Dataset],
    },
    URIRef("https://data.idnau.org/pid/cp"): {
        "path": Path(__file__).parent / "validator-idn-cp.ttl",
        "main_entity_classes": [SDO.Dataset, DCAT.Dataset],
    },
    URIRef("https://w3id.org/profile/vocpub"): {
        "path": Path(__file__).parent / "validator-vocpub-4.10.ttl",
        "main_entity_classes": [SKOS.ConceptScheme],
    },
}

KNOWN_ENTITY_CLASSES = [
    SKOS.ConceptScheme,
    OWL.Ontology,
    DCAT.Resource,
    SDO.CreativeWork,
    SDO.Dataset,
    DCAT.Dataset,
    SDO.DefinedTerm,
    SDO.DataCatalog,
    DCAT.Catalog,
]

ENTITY_CLASSES_PER_PROFILE = {
    "": "",
}


def path_or_url(s: str) -> Path | str:
    """Converts a string into a Path, preserving http(s)://..."""
    if s.startswith("http") and "://" in str(s):
        return s
    else:
        return Path(s)


def localise_path(p: Path | str, root: Path) -> Path:
    if str(p).startswith("http") and "://" in str(p):
        return p
    else:
        return Path(str(p).replace(str(root) + "/", ""))


def absolutise_path(p: Path | str, root: Path) -> Path | str:
    if str(p).startswith("http") and "://" in str(p):
        if "://" not in str(p):
            return str(p).replace(":/", "://")
        else:
            return str(p)
    else:
        return root / p


def get_files_from_artifact(
    manifest: Path | tuple[Path, Path, Graph], artifact: Node
) -> list[Path | str] | Generator[Path]:
    """Returns an iterable (list or generator) of Path objects for files within an artifact literal.

    This function will correctly interpret artifacts such as 'file.ttl', '*.ttl', '**/*.trig' etc.
    """
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    if str(artifact).startswith("http") and "://" in str(artifact):
        return [str(artifact)]
    elif isinstance(artifact, Literal):
        if "*" not in str(artifact):
            return [manifest_root / path_or_url(str(artifact))]
        else:
            artifact_str = str(artifact)
            glob_marker_location = artifact_str.find("*")
            glob_parts = [
                artifact_str[:glob_marker_location],
                artifact_str[glob_marker_location:],
            ]
            return Path(manifest_root / path_or_url(glob_parts[0])).rglob(glob_parts[1])
    elif isinstance(artifact, BNode):
        contentLocation = manifest_graph.value(
            subject=artifact, predicate=SDO.contentLocation
        )
        if str(contentLocation).startswith("http") and "://" in str(contentLocation):
            return [str(contentLocation)]
        else:
            return [manifest_root / str(contentLocation)]
    else:
        raise TypeError(f"Unsupported artifact type: {type(artifact)}")


def get_identifier_from_file(file: Path) -> list[URIRef]:
    """Returns a list if RDFLib graph identifier (URIRefs) from a triples or quads file
    for all owl:Ontology and skos:ConceptScheme objects"""
    if file.name.endswith(".ttl"):
        g = Graph().parse(file)
        for entity_class in KNOWN_ENTITY_CLASSES:
            v = g.value(predicate=RDF.type, object=entity_class)
            if v is not None:
                return [v]
    elif file.name.endswith(".trig"):
        gs = []
        d = Dataset()
        d.parse(file, format="trig")
        for g in d.graphs():
            gs.append(g.identifier)
        return gs
    else:
        return []


def get_validator_graph(
    manifest: Path | tuple[Path, Path, Graph], iri_or_path: URIRef | Literal
) -> Graph:
    """Returns the graph of a validator from either the path of a SHACL file or a known IRI->profile validator file"""
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    if isinstance(iri_or_path, URIRef):
        if iri_or_path not in KNOWN_PROFILES.keys():
            raise ValueError(
                f"You have specified conformance to an unknown profile. Known profiles are {', '.join(KNOWN_PROFILES.keys())}"
            )
        return load_graph(KNOWN_PROFILES[iri_or_path]["path"])

    else:
        return load_graph(absolutise_path(iri_or_path, manifest_root))


def get_manifest_paths_and_graph(
    manifest: Path | tuple[Path, Path, Graph],
) -> (Path, Graph):
    """Reads either a Manifest file from a Path, or a Manifest file from a Path and its root directory,
    a Path, and the Manifest as a deserialized Graph and returns the Manifest Path, its root dir as a Path
    and its content as a Graph"""
    if isinstance(manifest, Path):
        manifest_path = manifest
        manifest_root = Path(manifest).parent.resolve()
        manifest_graph = prezmanifest.validate(manifest)
    else:  # (Path, Path, Graph)
        manifest_path = manifest[0]
        manifest_root = manifest[1]
        manifest_graph = manifest[2]

    return manifest_path, manifest_root, manifest_graph


def get_catalogue_iri_from_manifest(
    manifest: Path | tuple[Path, Path, Graph],
) -> URIRef:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    for m in manifest_graph.subjects(RDF.type, PREZ.Manifest):
        for r in manifest_graph.objects(m, PROF.hasResource):
            for role in manifest_graph.objects(r, PROF.hasRole):
                if role == MRR.CatalogueData:
                    artifacts = manifest_graph.objects(r, PROF.hasArtifact)
                    for x in artifacts:
                        a = x
                    if isinstance(a, Literal):
                        a_graph = load_graph(manifest_root / str(a))
                        return a_graph.value(
                            predicate=RDF.type, object=DCAT.Catalog
                        ) or a_graph.value(predicate=RDF.type, object=SDO.DataCatalog)

    raise ValueError(f"No catalogue object IRI found in Manifest {manifest_root}")


def target_contains_this_manifests_catalogue(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    http_client: httpx.Client | None = None,
) -> bool:
    # get the IRI of the catalogue from the manifest
    cat_iri = get_catalogue_iri_from_manifest(manifest)

    q = """
        PREFIX olis: <https://olis.dev/>
        
        ASK
        WHERE {
          GRAPH olis:SystemGraph {
            VALUES ?graph_type {
              olis:RealGraph 
              olis:VirtualGraph
            }
            <xxx> a ?graph_type
          }
        }
        """.replace(
        "xxx", cat_iri
    )

    return query(
        sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True
    )


def make_httpx_client(
    sparql_username: str = None,
    sparql_password: str = None,
):
    auth = None
    if sparql_username:
        if sparql_password:
            auth = httpx.BasicAuth(sparql_username, sparql_password)
    return httpx.Client(auth=auth)


def get_main_entity_iri_of_artifact(
    artifact: Path,
    manifest: Path | tuple[Path, Path, Graph],
    artifact_graph: Graph = None,
    cc: URIRef = None,
    atype: URIRef = None,
) -> URIRef:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )
    artifact_path = absolutise_path(artifact, manifest_root)
    known_entity_classes = []
    if cc is not None:
        if cc in KNOWN_PROFILES.keys():
            for m_e_c in KNOWN_PROFILES[cc]["main_entity_classes"]:
                known_entity_classes.append(str(m_e_c))

    if atype is not None:
        known_entity_classes.append(str(atype))

    if len(known_entity_classes) < 1:
        known_entity_classes = [str(x) for x in KNOWN_ENTITY_CLASSES]

    known_entity_classes_str = f"<{'>\n                <'.join(known_entity_classes)}>"
    q = f"""
        SELECT ?me
        WHERE {{
            VALUES ?t {{
                {known_entity_classes_str.strip()}
            }}
            ?me a ?t .
        }}
        """
    mes = []

    g = artifact_graph if artifact_graph is not None else load_graph(artifact_path)

    if not isinstance(g, Graph):
        raise ValueError(f"Could not load a graph of the artifact at {artifact_path}")

    for r in query(g, q, return_python=True, return_bindings_only=True):
        if r.get("me"):
            mes.append(r["me"]["value"])

    if len(mes) != 1:
        if len(mes) > 1:
            raise ValueError(
                f"The artifact at {artifact_path} has more than one Main Entity: {', '.join(mes)} "
                f"based on the class {cc if cc is not None else '(none given)'}. There must only be one."
            )
        else:
            raise ValueError(
                f"The artifact at {artifact_path} has no recognizable Main Entity, "
                f"based on the classes {cc if cc is not None else '(none given)'}. There must be one."
            )

    return URIRef(mes[0])


def get_version_indicators_local(
    manifest: Path | tuple[Path, Path, Graph], artifact: Path, version_indicators: dict
):
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )
    artifact_path = absolutise_path(artifact, manifest_root)
    artifact_graph = load_graph(artifact_path)

    # if we aren't given a Main Entity, let's look for one using the Main Entity Classes
    if version_indicators.get("main_entity") is None:
        version_indicators["main_entity"] = get_main_entity_iri_of_artifact(
            artifact,
            (manifest_path, manifest_root, manifest_graph),
            artifact_graph,
            version_indicators.get("conformance_claim"),
            version_indicators.get("additional_type"),
        )

    # if we have a Main Entity at this point, we can get the content-based Indicators
    if version_indicators.get("main_entity") is not None:
        q = f"""
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX schema: <https://schema.org/>
            
            SELECT ?md ?vi ?v
            WHERE {{
                OPTIONAL {{
                    <{version_indicators["main_entity"]}> dcterms:modified|schema:dateModified ?md .
                }}
                
                OPTIONAL {{
                    <{version_indicators["main_entity"]}> owl:versionIRI ?vi .
                }}
                
                OPTIONAL {{
                 <{version_indicators["main_entity"]}> owl:versionInfo|schema:version|dcterms:hasVersion ?v .
             }}
            }}
            """
        # only use values for Version Indicators if not already present - i.e. from the manifest
        for r in query(
            artifact_graph, q, return_python=True, return_bindings_only=True
        ):
            if version_indicators.get("modified_date") is None:
                if r.get("md") is not None:
                    version_indicators["modified_date"] = date_parse(r["md"]["value"])
            if version_indicators.get("version_iri") is None:
                if r.get("vi") is not None:
                    version_indicators["version_iri"] = r["vi"]["value"]
            if version_indicators.get("version_info") is None:
                if r.get("v") is not None:
                    version_indicators["version_info"] = r["v"]["value"]
    # if not, we may still get file-based indicators
    if artifact_path.is_file():
        version_indicators["file_size"] = artifact_path.stat().st_size

    return


def get_version_indicators_sparql(
    main_entity: str,
    sparql_endpoint: str,
    http_client: httpx.Client | None = None,
) -> dict:
    if not sparql_endpoint.startswith("http") and "://" in str(sparql_endpoint):
        raise ValueError(
            f"The sparql_endpoint you have supplied does not look valid: {sparql_endpoint}"
        )

    indicators = {
        "modified_date": None,
        "version_info": None,
        "version_iri": None,
        "file_size": None,
        "main_entity": main_entity,
    }

    q = f"""
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX schema: <https://schema.org/>

        SELECT ?md ?vi ?v
        WHERE {{
            GRAPH ?g {{
                VALUES ?me {{
                    <{main_entity}>
                    <{main_entity + "-catalogue"}>
                }}
                OPTIONAL {{
                    ?me dcterms:modified|schema:dateModified ?md .
                }}
    
                OPTIONAL {{
                    ?me owl:versionIRI ?vi .
                }}
    
                OPTIONAL {{
                    ?me owl:versionInfo|schema:version|dcterms:hasVersion ?v .
                }}
            }}
        }}
        """
    res = sparql(
        sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True
    )
    if len(res) == 0:
        raise ValueError(
            "The system got no results from its querying of the SPARQL endpoint"
        )

    for r in res:
        if r.get("md") is not None:
            indicators["modified_date"] = date_parse(r["md"]["value"])
        if r.get("vi") is not None:
            indicators["version_iri"] = r["vi"]["value"]
        if r.get("v") is not None:
            indicators["version_info"] = r["v"]["value"]

    return indicators


class VersionIndicatorComparison(Enum):
    First = "first"
    Second = "second"
    Neither = "neither"
    CantCalculate = "cant_calculate"


def compare_version_indicators(first: dict, second: dict) -> VersionIndicatorComparison:
    """Compares Modified Date, Version IRI & Version info for each and returns latest"""

    """Even weighted aggregate score for each version indicator"""
    first_score = 0
    second_score = 0
    has_modified_date_comparison = first.get("modified_date") and second.get(
        "modified_date"
    )
    has_version_iri_comparison = first.get("version_iri") and second.get("version_iri")
    has_version_info_comparison = first.get("version_info") and second.get(
        "version_info"
    )

    if (
        not has_modified_date_comparison
        and not has_version_iri_comparison
        and not has_version_info_comparison
    ):
        return VersionIndicatorComparison.CantCalculate

    if has_modified_date_comparison:
        if first["modified_date"] > second["modified_date"]:
            first_score += 1
        elif first["modified_date"] == second["modified_date"]:
            pass
        else:
            second_score += 1

    if has_version_iri_comparison:
        if first["version_iri"] > second["version_iri"]:
            first_score += 1
        elif first["version_iri"] == second["version_iri"]:
            pass
        else:
            second_score += 1

    if has_version_info_comparison:
        if first["version_info"] > second["version_info"]:
            first_score += 1
        elif first["version_info"] == second["version_info"]:
            pass
        else:
            second_score += 1

    # TODO: add test for file_size, Git version etc.

    if first_score > second_score:
        return VersionIndicatorComparison.First
    elif second_score == first_score:
        return VersionIndicatorComparison.Neither
    else:
        return VersionIndicatorComparison.Second


def which_is_more_recent(
    version_indicators: dict,
    sparql_endpoint: str = None,
    http_client: httpx.Client | None = None,
) -> VersionIndicatorComparison:
    """Tests to see if the given artifact is more recent than a previously stored copy of its content"""

    remote = get_version_indicators_sparql(
        version_indicators["main_entity"], sparql_endpoint, http_client
    )

    return compare_version_indicators(version_indicators, remote)


def denormalise_artifacts(manifest: Path | tuple[Path, Path, Graph] = None) -> dict:
    """For each Artifiact in the Manifest, return a dict:

    Artifact path,
    Main Entity,
    Conformance Claims
    Date Modified
    Version IRI
    Version Info
    Role
    Version Indicators

    of each asset's path, main entity IRI, manifest role and version indicators"""

    artifacts_info = {}

    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    # for each artifact, get what we can directly from the Manifest
    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX prez: <https://prez.dev/>
        PREFIX prof: <http://www.w3.org/ns/dx/prof/>
        PREFIX schema: <https://schema.org/>

        SELECT ?a ?me ?cc ?atype ?dm ?vi ?v ?r
        WHERE {
            # if the Resource has a Blank Node artifact, it must provide the Main Entity IRI
            {
                ?x 
                    prof:hasArtifact ?bn ;
                    prof:hasRole ?r ;
                .
                
                ?bn 
                    schema:mainEntity ?me ;
                    schema:contentLocation ?a ;
                .
                
                OPTIONAL {
                    ?bn dcterms:conformsTo ?cc_local .
                }
                
                OPTIONAL {
                    ?x dcterms:conformsTo ?cc_resource .
                }
                
                OPTIONAL {
                    ?bn schema:additionalType ?atype_local .
                }
                
                OPTIONAL {
                    ?x schema:additionalType ?atype_resource .
                }                
                
                OPTIONAL {
                    ?bn schema:dateModified ?dm .
                } 
                
                OPTIONAL {
                    ?bn owl:versionIRI ?vi .
                }
                
                OPTIONAL {
                    ?bn owl:versionInfo|schema:version|dcterms:hasVersion ?v .
                }     
                
                BIND(COALESCE(?cc_local, ?cc_resource) AS ?cc)
                
                BIND(COALESCE(?atype_local, ?atype_resource) AS ?atype)
                   
                FILTER isBLANK(?bn)
            }
            UNION 
            {
                ?x 
                    prof:hasArtifact ?a ;
                    prof:hasRole ?r ;
                .
                
                OPTIONAL {
                    ?x dcterms:conformsTo ?cc .
                }
                
                OPTIONAL {
                    ?x schema:additionalType ?atype .
                }                
                
                FILTER isLITERAL(?a)
            }
        }
        """

    for r in query(manifest_graph, q, return_python=True, return_bindings_only=True):
        artifact = path_or_url(r["a"]["value"])
        files = get_files_from_artifact(
            (manifest_path, manifest_root, manifest_graph), Literal(artifact)
        )

        for file in files:
            me = URIRef(r["me"]["value"]) if r.get("me") is not None else None
            role = URIRef(r["r"]["value"])
            dm = r["dm"]["value"] if r.get("dm") is not None else None
            vi = r["vi"]["value"] if r.get("vi") is not None else None
            v = r["v"]["value"] if r.get("v") is not None else None
            cc = URIRef(r["cc"]["value"]) if r.get("cc") is not None else None
            atype = URIRef(r["atype"]["value"]) if r.get("atype") is not None else None

            artifacts_info[file] = {
                "main_entity": me,
                "role": role,
                "date_modified": dm,
                "version_iri": vi,
                "version_info": v,
                "file_size": None,
                "conformance_claim": cc,
                "additional_type": atype,
            }

    # get Version Indicators info only for Resources with certain Roles
    for k, v in artifacts_info.items():
        if v["role"] in [MRR.CatalogueData, MRR.ResourceData]:
            get_version_indicators_local(
                (manifest_path, manifest_root, manifest_graph), k, v
            )

    return artifacts_info


def artifact_file_name_from_graph_id(graph_id: str) -> str:
    s = graph_id.replace("://", "--")
    s = s.replace("/", "-")
    s = s.replace("#", "--")
    return s + ".ttl"


def store_remote_artifact_locally(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str,
    graph_id: str,
    http_client: httpx.Client | None = None,
) -> Graph:
    """Writes a remote graph to a local file and registers that file as a Resource in the given Manifest.

    Only the Resource Role ResourceData is supported."""
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )
    q = """
        CONSTRUCT {
            ?s ?p ?o
        }
        WHERE {
            GRAPH <xxx> {
                ?s ?p ?o
            }
        }
        """.replace(
        "xxx", graph_id
    )
    r = query(sparql_endpoint, q, http_client)
    artifact_path = str(artifact_file_name_from_graph_id(graph_id))
    r.serialize(destination=manifest_root / artifact_path, format="longturtle")

    new_manifest_graph = Graph()
    new_manifest_graph += manifest_graph

    for m in new_manifest_graph.subjects(RDF.type, PREZ.Manifest):
        new_r = BNode()
        for r in new_manifest_graph.objects(m, PROF.hasResource):
            if (r, PROF.hasRole, MRR.ResourceData) in new_manifest_graph:
                new_r = r

        a = BNode()
        new_manifest_graph.add(
            (
                a,
                SDO.contentLocation,
                Literal(artifact_path),  # relative to manifest_root
            )
        )
        new_manifest_graph.add((a, SDO.mainEntity, URIRef(graph_id)))
        new_manifest_graph.add((new_r, PROF.hasArtifact, a))
        new_manifest_graph.add(
            (new_r, PROF.hasRole, MRR.ResourceData)  # only one supported for now
        )
        new_manifest_graph.add((m, PROF.hasResource, new_r))

    return new_manifest_graph


def update_local_artifact(
    manifest: Path | tuple[Path, Path, Graph],
    artifact_path: Path,
    sparql_endpoint: str,
    graph_id: str,
    http_client: httpx.Client | None = None,
):
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )
    q = """
        CONSTRUCT {
            ?s ?p ?o
        }
        WHERE {
            GRAPH <xxx> {
                ?s ?p ?o
            }
        }
        """.replace(
        "xxx", graph_id
    )
    r = query(sparql_endpoint, q, http_client)
    r.serialize(destination=artifact_path, format="longturtle")
