from mailbox import MMDF
from pathlib import Path

import httpx
from kurra.db.gsp import clear, upload
from kurra.sparql import query
from kurra.utils import load_graph
from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import DCAT, PROF, RDF, SDO

import prezmanifest.utils
from prezmanifest.definednamespaces import MRR
from prezmanifest.utils import (
    VersionIndicatorComparison,
    absolutise_path,
    denormalise_artifacts,
    get_manifest_paths_and_graph,
    store_remote_artifact_locally,
    update_local_artifact,
    which_is_more_recent,
)


def sync(
    manifest: Path | tuple[Path, Path, Graph],
    sparql_endpoint: str = None,
    http_client: httpx.Client = httpx.Client(),
    update_remote: bool = True,
    update_local: bool = True,
    add_remote: bool = True,
    add_local: bool = True,
) -> dict:
    """Syncronises a set of resources in files or storage locations - from - described by a Manifest with a SPARQL Endpoint
    - to.

    Args:
        manifest: the PrezManifest manifest describing the 'from' resources
        sparql_endpoint: a SPARQL endpoint URL to sync resources to
        http_client: an httpx client to use for making requests
        update_remote: whether to update the to artifacts with newer from ones
        update_local: whether to update the from artifacts with newer to ones
        add_remote: whether to add artifacts to the to location with newer from ones
        add_local: whether to add artifacts to the from location with newer to ones

    Returns:
        a dictionary of the state of syncronisation, per artifact
    """

    # list all from resources
    # find all matching to resources
    sync_status = {}

    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )

    # For each Artifact in the Manifest
    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))
    local_entities = [v["main_entity"] for k, v in artifacts.items()]

    cat_iri = None
    cat_artifact_path = None
    for k, v in artifacts.items():
        if v["role"] in [MRR.ResourceData, MRR.CatalogueData]:
            # save cat_iri for later
            if v["role"] in MRR.CatalogueData:
                cat_iri = v["main_entity"]
                cat_artifact_path = absolutise_path(k, manifest_root)

            # See if each is known remotely (via Main Entity Graph IRI)
            known = query(
                sparql_endpoint,
                "ASK {GRAPH <xxx> {?s ?p ?o}}".replace("xxx", str(v["main_entity"])),
                http_client=http_client,
                return_format="python",
                return_bindings_only=True,
            )
            # If not known by graph IRI, just check if it's the catalogue (+ "-catalogue" to IRI)
            if not known and v["role"] == MRR.CatalogueData:
                known = query(
                    sparql_endpoint,
                    "ASK {GRAPH <xxx> {?s ?p ?o}}".replace(
                        "xxx", str(v["main_entity"] + "-catalogue")
                    ),
                    http_client=http_client,
                    return_format="python",
                    return_bindings_only=True,
                )

            # If known, compare it
            if known:
                replace = which_is_more_recent(
                    v,
                    sparql_endpoint,
                    http_client,
                )
                if replace == VersionIndicatorComparison.First:
                    direction = "upload"
                elif replace == VersionIndicatorComparison.Second:
                    direction = "download"
                elif replace == VersionIndicatorComparison.Neither:
                    direction = "same"
                elif VersionIndicatorComparison.CantCalculate:
                    direction = "upload"
            else:  # not known at remote location so forward sync - upload
                direction = "add-remotely"

            sync_status[str(k)] = {
                "main_entity": v["main_entity"],
                "direction": direction,
                "sync": v["sync"],
            }

    # Check for things at remote not known in local
    q = """
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX schema: <https://schema.org/>
    
        SELECT ?p
        WHERE {
            GRAPH ?g {
                <xxx> schema:hasPart|dcterms:hasPart ?p
            }
        }
        """.replace("xxx", str(cat_iri))
    for x in query(
        sparql_endpoint,
        q,
        http_client=http_client,
        return_format="python",
        return_bindings_only=True,
    ):
        remote_entity = x["p"]
        if remote_entity not in local_entities:
            sync_status[str(remote_entity)] = {
                "main_entity": URIRef(remote_entity),
                "direction": "add-locally",
                "sync": True,
            }

    update_remote_catalogue = False
    for k, v in sync_status.items():
        if v["sync"]:
            if update_remote and v["direction"] == "upload":
                clear(sparql_endpoint, v["main_entity"], http_client)
                upload(
                    sparql_endpoint,
                    Path(k),
                    v["main_entity"],
                    False,
                    http_client=http_client,
                )

            if add_remote and v["direction"] == "add-remotely":
                # no need to clear() as this asset doesn't exist remotely
                upload(
                    sparql_endpoint,
                    Path(k),
                    v["main_entity"],
                    False,
                    http_client=http_client,
                )
                update_remote_catalogue = True

            if add_local and v["direction"] == "add-locally":
                updated_local_manifest = store_remote_artifact_locally(
                    (manifest_path, manifest_root, manifest_graph),
                    sparql_endpoint,
                    v["main_entity"],
                    http_client,
                )

                updated_local_manifest.bind(
                    "mrr", "https://prez.dev/ManifestResourceRoles"
                )
                updated_local_manifest.serialize(
                    destination=manifest_path, format="longturtle"
                )
                cat = load_graph(cat_artifact_path)
                cat.add((cat_iri, SDO.hasPart, URIRef(v["main_entity"])))
                cat.serialize(destination=cat_artifact_path, format="longturtle")

            if update_local and v["direction"] == "download":
                update_local_artifact(
                    (manifest_path, manifest_root, manifest_graph),
                    Path(k),
                    sparql_endpoint,
                    v["main_entity"],
                    http_client,
                )

    if update_remote_catalogue:
        # TODO: work out why SILENT is needed. Why isn't the cat_iri graph known? Should have been uploaded by sync already
        query(sparql_endpoint, f"DROP SILENT GRAPH <{cat_iri}>")
        upload(
            sparql_endpoint,
            cat_artifact_path,
            cat_iri,
            False,
            http_client=http_client,
        )

    return sync_status


def make_catalogue(
    manifest: Path | tuple[Path, Path, Graph],
    reuse_cat_iri: bool = False,
    new_cat_iri: URIRef | str = None,
) -> Graph:
    """Makes a catalogue graph for a Manifest

    Args:
        manifest: the PrezManifest manifest to create the catalogue for
        cat_iri: the iri of the catalogue, if known
        reuse: whether to reuse the IRI of an existing catalogue if defined in the manifest


    Returns:
        a simple graph of the catalogue
        also writes back to the Manifest and overwrites or creates a catalogue artifact file
    """
    # create the return graph
    # read, add or create the catalogue IRI
    # add in each resource's IRI where role is ResourceData & *CatalogueAndResourceLabels

    if reuse_cat_iri:
        if new_cat_iri is not None:
            raise ValueError("If you select to reuse any existing catalogue 'reuse_cat_iri=True', then new_cat_iri must be None")
    else:
        if new_cat_iri is None:
            raise ValueError("If you select not to reuse any existing catalogue 'reuse_cat_iri=False', then new_cat_iri must be provided")

        if new_cat_iri is not None:
            new_cat_iri = URIRef(new_cat_iri) if isinstance(new_cat_iri, str) else new_cat_iri

    manifest_path, manifest_root, manifest_graph = get_manifest_paths_and_graph(
        manifest
    )
    manifest_graph: Graph


    # create the return graph
    c:Graph = None
    cat_path:Path = None


    # read, add or create the catalogue IRI
    # see if we already have one in the Manifest
    existing_cat = False
    for r in manifest_graph.objects(None, PROF.hasResource):
        if (r, PROF.hasRole, MRR.CatalogueData) in manifest_graph:
            existing_cat = True
            cat_path = next(manifest_graph.objects(r, PROF.hasArtifact))
            c = load_graph(manifest_root / cat_path)

    if cat_path is None:
        if Path(manifest_root / "catalogue.ttl").is_file():
            cat_path = manifest_root / f"catalogue.{prezmanifest.utils.make_dateModified()}.ttl"
        else:
            cat_path = manifest_root / "catalogue.ttl"

    # see if we can find an IRI for a catalogue, if we have one loaded in c
    if c is not None:
        cat_iri_existing = c.value(predicate=RDF.type, object=SDO.DataCatalog)
        if cat_iri_existing is None:
            c.value(predicate=RDF.type, object=DCAT.Catalog)

    # check we are able to reuse
    if reuse_cat_iri:
        if c is None:
            raise ValueError(
                f"You nave selected to reuse an existing catalogue "
                f"but no resource with CatalogueData was found in the manifest")

        if not cat_iri_existing:
            raise ValueError(
                f"You nave selected to reuse an existing catalogue but an IRI for one "
                f"could not be found in file {cat_path}")
        cat_iri = cat_iri_existing
    else:  # we are not reusing so scrub existing catalogue IRI and ensure at least cat declaration is present
        if c is not None:
            for p, o in c.predicate_objects(cat_iri_existing):
                c.remove((cat_iri_existing, p, o))
                c.add((new_cat_iri, p, o))
            for s, p in c.subject_predicates(cat_iri_existing):
                c.remove((s, p, cat_iri_existing))
                c.add((s, p, new_cat_iri))

        if c is None:
            c = Graph()
        cat_iri = new_cat_iri

        c.add((cat_iri, RDF.type, SDO.DataCatalog))

    # add/update basic catalogue facts
    c.remove((cat_iri, SDO.dateModified, None))
    c.add((cat_iri, SDO.dateModified, prezmanifest.utils.make_dateModified()))


    # add in each resource's IRI
    artifacts = denormalise_artifacts((manifest_path, manifest_root, manifest_graph))

    for k, v in artifacts.items():
        if v["role"] == MRR.ResourceData:
            c.add((cat_iri, SDO.hasPart, v["main_entity"]))


    # replace catalogue entry in manifest
    if existing_cat:
        pass
    else:
        """
        [
            prof:hasArtifact "catalogue.ttl" ;
            prof:hasRole <https://prez.dev/ManifestResourceRoles/CatalogueData> ;
        ] ;
        """
        import os
        cat_path_rel = os.path.relpath(
            cat_path,
            start=os.path.dirname(manifest_path)
        )

        r = BNode()
        manifest_graph.add((r, PROF.hasArtifact, Literal(cat_path_rel)))
        manifest_graph.add((r, PROF.hasRole, MRR.CatalogueData))
        for s in manifest_graph.subjects(PROF.hasResource, None):
            manifest_graph.add((s, PROF.hasResource, r))

    with open(manifest_path, "w") as f:
        f.write(manifest_graph.serialize(format="longturtle"))


    # save catalogue artifact
    c.serialize(format="longturtle", destination=cat_path)


    return c
