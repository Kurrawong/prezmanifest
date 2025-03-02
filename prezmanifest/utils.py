from collections.abc import Generator
from pathlib import Path
import datetime
import httpx
from datetime import datetime

from kurra.file import load_graph
from kurra.sparql import query
from kurra.db import sparql
from rdflib import BNode, Dataset, Graph, Literal, Node, URIRef
from rdflib.namespace import DCAT, OWL, PROF, RDF, SDO, SKOS

from prezmanifest.definednamespaces import MRR, PREZ

KNOWN_PROFILES = {
    URIRef("http://www.opengis.net/def/geosparql"): {
        "path": Path(__file__).parent / "validator-geosparql-1.1.ttl",
        "main_entity_classes": [SDO.Dataset, DCAT.Dataset]
    },
    URIRef("https://data.idnau.org/pid/cp"): {
        "path": Path(__file__).parent / "validator-idn-cp.ttl",
        "main_entity_classes": [SDO.Dataset, DCAT.Dataset]
    },
    URIRef("https://w3id.org/profile/vocpub"): {
        "path": Path(__file__).parent / "validator-vocpub-4.10.ttl",
        "main_entity_classes": [SKOS.ConceptScheme]
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


def path_or_url(s: str) -> Path|str:
    """Converts a string into a Path, preserving http(s)://..."""
    return s if s.startswith("http") else Path(s)


def localise_path(p: Path|str, root: Path) -> Path:
    if str(p).startswith("http"):
        return p
    else:
        return Path(str(p).replace(str(root) + "/", ""))


def absolutise_path(p: Path|str, root: Path) -> Path:
    if str(p).startswith("http"):
        return p
    else:
        return root / p


def get_files_from_artifact(
        manifest: Path | tuple[Path, Path, Graph],
        artifact: Node
) -> list[Path|str] | Generator[Path]:
    """Returns an iterable (list or generator) of Path objects for files within an artifact literal.

    This function will correctly interpret artifacts such as 'file.ttl', '*.ttl', '**/*.trig' etc.
    """
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    if isinstance(artifact, Literal):
        if "*" not in str(artifact):
            return [manifest.parent / path_or_url(str(artifact))]
        else:
            artifact_str = str(artifact)
            glob_marker_location = artifact_str.find("*")
            glob_parts = [
                artifact_str[:glob_marker_location],
                artifact_str[glob_marker_location:],
            ]

            return Path(manifest.parent / path_or_url(glob_parts[0])).glob(glob_parts[1])
    elif isinstance(artifact, BNode):
        contentLocation = manifest_graph.value(
            subject=artifact, predicate=SDO.contentLocation
        )
        if str(contentLocation).startswith("http"):
            return [str(contentLocation)]
        else:
            return [manifest.parent / str(contentLocation)]
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
        manifest: Path | tuple[Path, Path, Graph],
        iri_or_path: URIRef | Literal
) -> Graph:
    """Returns the graph of a validator from either the path of a SHACL file or a known IRI->profile validator file"""
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    if isinstance(iri_or_path, URIRef):
        if iri_or_path not in KNOWN_PROFILES.keys():
            raise ValueError(
                f"You have specified conformance to an unknown profile. Known profiles are {', '.join(KNOWN_PROFILES.keys())}"
            )
        return load_graph(KNOWN_PROFILES[iri_or_path]["path"])

    else:
        return load_graph(absolutise_path(iri_or_path, manifest_path))


def get_manifest_paths_and_graph(manifest: Path | tuple[Path, Path, Graph]) -> (Path, Graph):
    """Reads either a Manifest file from a Path, or a Manifest file from a Path and its root directory,
    a Path, and the Manifest as a deserialized Graph and returns the Manifest Path, its root dir as a Path
    and its content as a Graph"""
    if isinstance(manifest, Path):
        manifest_path = manifest
        manifest_root = Path(manifest).parent.resolve()
        manifest_graph = load_graph(manifest)
    else:
        manifest_path = manifest[0]
        manifest_root = manifest[1]
        manifest_graph = manifest[2]

    return manifest_path, manifest_root, manifest_graph


def get_catalogue_iri_from_manifest(manifest: Path | tuple[Path, Graph]) -> URIRef:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

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


# TODO
def does_target_contain_this_catalogue(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    sparql_username: str = None,
    sparql_password: str = None,
    destination_file: Path = None,
) -> bool:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    # get the IRI of the catalogue from the manifest
    cat_iri = get_catalogue_iri_from_manifest(manifest)

    # check if the IRI is in the target
    pass


def make_httpx_client(
    sparql_username: str = None,
    sparql_password: str = None,
):
    auth = None
    if sparql_username:
        if sparql_password:
            auth = httpx.BasicAuth(sparql_username, sparql_password)
    return httpx.Client(auth=auth)


def get_main_entity_iri_via_conformance_claims(
        artifact: Path,
        manifest: Path,
        artifact_graph: Graph = None,
        ccs: list[URIRef] = None
) -> URIRef:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)
    artifact_path = absolutise_path(artifact, manifest_root)
    known_entity_classes = []
    if len(ccs) > 0:
        if ccs[0] is not None:
            for cc in ccs:
                for m_e_c in KNOWN_PROFILES[cc]["main_entity_classes"]:
                    known_entity_classes.append(str(m_e_c))

    if len(known_entity_classes) < 1:
        known_entity_classes = [str(x) for x in KNOWN_ENTITY_CLASSES]

    known_entity_classes_str = f"<{'>\n                <'.join(known_entity_classes)}>"
    q = f"""
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX schema: <https://schema.org/>

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
                f"based on the classes {', '.join(ccs)}. There must only be one."
            )
        else:
            raise ValueError(
                f"The artifact at {artifact_path} has no recognizable Main Entity, "
                f"based on the classes {', '.join(ccs)}. There must only be one."
            )

    return mes[0]


def get_version_indicators_for_artifact(
        manifest: Path | tuple[Path, Path, Graph],
        artifact: Path,
        main_entity: str = None,
        conformance_claims: list[URIRef] = None
) -> dict:
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)
    artifact_path = absolutise_path(artifact, manifest_root)
    
    indicators = {
        "modified_date": None,
        "version": None,
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": None,
    }

    g = load_graph(artifact_path)

    # if we aren't given a Main Entity, let's look for one using the Main Entity Classes
    if main_entity is None:
        main_entity_classes = None
        # if the Manifest indicates this artifact conforms to something, work out the main entity classes from that
        # else, just try common types
        if conformance_claims is not None:
            for cc in conformance_claims:
                if cc in KNOWN_PROFILES.keys():
                    main_entity_classes = KNOWN_PROFILES[cc]["main_entity_classes"]

        # if no Conformance Classes are give, try all known Entity classes
        if main_entity_classes is None:
            main_entity_classes = KNOWN_ENTITY_CLASSES

        if main_entity is None:
            main_entities = []
            main_entities_classes_str = f"<{'>\n                <'.join(main_entity_classes)}>"
            q = f"""
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX schema: <https://schema.org/>
        
                SELECT ?me
                WHERE {{
                    VALUES ?t {{
                        {main_entities_classes_str.strip()}
                    }}
                    ?me a ?t .
                }}
                """
            for r in query(g, q, return_python=True, return_bindings_only=True):
                main_entities.append(r["me"]["value"])
            # for c in main_entity_classes:
            #     for s in g.subjects(RDF.type, c):
            #         main_entities.append(s)

            if len(main_entities) != 1:
                if len(main_entities) > 1:
                    raise ValueError(
                        f"The artifact at {artifact_path} has more than one Main Entity: {', '.join(main_entities)} "
                        f"based on the classes {', '.join(main_entity_classes)}. There must only be one."
                    )
                else:
                    raise ValueError(
                        f"The artifact at {artifact_path} has no recognizable Main Entity, "
                        f"based on the classes {', '.join(main_entity_classes)}. There must only be one."
                    )

            main_entity = str(main_entities[0])

    indicators["main_entity_iri"] = main_entity

    # if we have a Main Entity at this point, we can get the content-based Indicators
    if main_entity is not None:
        q = f"""
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX schema: <https://schema.org/>
            
            SELECT ?md ?vi ?v
            WHERE {{
                OPTIONAL {{
                    <{main_entity}> dcterms:modified|schema:dateModified ?md .
                }}
                
                OPTIONAL {{
                    <{main_entity}> owl:versionIRI ?vi .
                }}
                
                OPTIONAL {{
                 <{main_entity}> owl:versionInfo|schema:version|dcterms:hasVersion ?v .
             }}
            }}
            """
        for r in query(g, q, return_python=True, return_bindings_only=True):
            if r.get("md") is not None:
                indicators["modified_date"] = datetime.strptime(r["md"]["value"], "%Y-%m-%d")
            if r.get("vi") is not None:
                indicators["version_iri"] = r["vi"]["value"]
            if r.get("v") is not None:
                indicators["version"] = r["v"]["value"]

    # if not, we may still get file-based indicators
    if artifact_path.is_file():
        indicators["file_size"] = artifact_path.stat().st_size

    return indicators


def get_version_indicators_for_graph_in_sparql_endpoint(
    main_entity: str,
    sparql_endpoint: str,
    http_client: httpx.Client | None = None,
) -> dict:
    if not sparql_endpoint.startswith("http"):
        raise ValueError(
            f"The sparql_endpoint you have supplied does not look valid: {sparql_endpoint}"
        )

    indicators = {
        "modified_date": None,
        "version": None,
        "version_iri": None,
        "file_size": None,
        "main_entity_iri": main_entity,
    }

    q = f"""
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX schema: <https://schema.org/>

        SELECT ?md ?vi ?v
        WHERE {{
            GRAPH ?g {{
                OPTIONAL {{
                    <{main_entity}> dcterms:modified|schema:dateModified ?md .
                }}
    
                OPTIONAL {{
                    <{main_entity}> owl:versionIRI ?vi .
                }}
    
                OPTIONAL {{
                    <{main_entity}> owl:versionInfo|schema:version|dcterms:hasVersion ?v .
                }}
            }}
        }}
        """
    res = sparql(sparql_endpoint, q, http_client, return_python=True, return_bindings_only=True)
    if len(res) == 0:
        raise ValueError(
            "The system got no results from its querying of the SPARQL endpoint"
        )

    for r in res:
        if r.get("md") is not None:
            indicators["modified_date"] = datetime.strptime(r["md"]["value"], "%Y-%m-%d")
        if r.get("vi") is not None:
            indicators["version_iri"] = r["vi"]["value"]
        if r.get("v") is not None:
            indicators["version"] = r["v"]["value"]

    return indicators


def first_is_more_recent_than_second_using_version_indicators(first: dict, second: dict) -> bool:
    """Tries modified date first - only if both indicators have it - then version IRI then version"""
    if first.get("modified_date") and second.get("modified_date"):
        return first["modified_date"] > second["modified_date"]

    if first.get("version_iri") and second.get("version_iri"):
        return first["version_iri"] > second["version_iri"]

    if first.get("version") and second.get("version"):
        return first["version"] > second["version"]


def local_artifact_is_more_recent_then_stored_data(
    manifest: Path | tuple[Path, Path, Graph],
    artifact: Path,
    sparql_endpoint: str = None,
    http_client: httpx.Client | None = None,
):
    """Tests to see if the given artifact is more recent than a previously stored copy of its content"""
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)
    local = get_version_indicators_for_artifact(manifest_path, artifact)
    me = local["main_entity_iri"]

    remote = get_version_indicators_for_graph_in_sparql_endpoint(
        me,
        sparql_endpoint,
        http_client
    )

    return first_is_more_recent_than_second_using_version_indicators(local, remote)


def denormalise_artifacts(manifest: Path | tuple[Path, Path, Graph] = None) -> list[tuple[Path, str, URIRef, dict]]:
    """Returns a list of tuples of each asset's path, main entity IRI, manifest role and version indicators"""
    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(manifest)

    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX prez: <https://prez.dev/>
        PREFIX prof: <http://www.w3.org/ns/dx/prof/>
        PREFIX schema: <https://schema.org/>

        SELECT ?a ?me ?cc ?dm ?vi ?v ?r
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
                    ?bn schema:dateModified ?dm .
                } 
                
                OPTIONAL {
                    ?bn owl:versionIRI ?vi .
                }
                
                OPTIONAL {
                    ?bn owl:versionInfo|schema:version|dcterms:hasVersion ?v .
                }     
                
                BIND(COALESCE(?cc_local, ?cc_resource) AS ?cc)
                   
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
                
                FILTER isLITERAL(?a)
            }
        }
        """

    cat_entries = []
    for r in query(manifest_graph, q, return_python=True, return_bindings_only=True):
        cat_entries.append((
            path_or_url(r["a"]["value"]),
            r["me"]["value"] if r.get("me") is not None else None,
            r["cc"]["value"] if r.get("cc") is not None else None,
            r["dm"]["value"] if r.get("dm") is not None else None,
            r["vi"]["value"] if r.get("vi") is not None else None,
            r["v"]["value"] if r.get("v") is not None else None,
            URIRef(r["r"]["value"]),
            dict())
        )

    # separate out all individual artifacts
    cat_entries_expanded = []
    for cat_entry in cat_entries:
        if "*" in str(cat_entry[0]):
            files = get_files_from_artifact(manifest_graph, manifest, Literal(cat_entry[0]))
            for file in files:
                cat_entries_expanded.append((localise_path(file, manifest_root), *cat_entry[1:]))
        else:
            cat_entries_expanded.append(cat_entry)

    # fill in missing Main Entities, but only for Resources with certain Roles
    cat_entries_main_entities_present = []
    for cat_entry in cat_entries_expanded:
        if not cat_entry[1] and cat_entry[6] in [MRR.ResourceData, MRR.CatalogueData]:
            me = get_main_entity_iri_via_conformance_claims(
                absolutise_path(cat_entry[0], manifest_root),
                manifest,
                None,
                [URIRef(cat_entry[2]) if cat_entry[2] is not None else None],
            )
            cat_entries_main_entities_present.append((cat_entry[0], me, *cat_entry[2:]))
        else:
            cat_entries_main_entities_present.append(cat_entry)

    # get the Version Indicators for each artifact that we have a Main Entity for
    cat_entries_with_vis = []
    for ce in cat_entries_main_entities_present:
        if ce[1] is not None:
            vi = get_version_indicators_for_artifact(
                (manifest_path, manifest_root, manifest_graph),
                ce[0],
                ce[1],
                ce[2]
            )
            cat_entries_with_vis.append((*ce[:-1], vi))
        else:
            cat_entries_with_vis.append(ce)

    return cat_entries_with_vis
