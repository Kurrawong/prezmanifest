from rdflib.namespace import DefinedNamespace, Namespace
from rdflib.term import URIRef


class MRR(DefinedNamespace):
    _NS = Namespace("https://prez.dev/ManifestResourceRoles/")
    _fail = True

    CatalogueData: URIRef
    CatalogueModel: URIRef
    ResourceData: URIRef
    ResourceModel: URIRef
    CatalogueAndResourceModel: URIRef
    CompleteCatalogueAndResourceLabels: URIRef
    IncompleteCatalogueAndResourceLabels: URIRef


class OLIS(DefinedNamespace):
    _NS = Namespace("https://olis.dev/")
    _fail = True

    NamedGraph: URIRef
    RealGraph: URIRef
    SystemGraph: URIRef
    VirtualGraph: URIRef

    isAliasFor: URIRef


class PREZ(DefinedNamespace):
    _NS = Namespace("https://prez.dev/")
    _fail = True

    Manifest: URIRef
