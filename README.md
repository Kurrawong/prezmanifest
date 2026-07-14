# Prez Manifest

Prez Manifest - pm - is a tool that performs data management functions, such as synchronising between RDF files in a version control repository and an RDF DB, and also a data model that provides the scaffolding for data to be managed by the tool. The tool is implemented as a Python application and library.

## Contents

* [What is a pm Manifest?](#what-is-a-pm-manifest)
* [Functions](#functions)
* [Installation](#installation)
* [Use](#use)
* [Testing](#testing)
* [Extending](#extending)
* [License](#license)
* [Contact](#contact)
* [Case Studies](#case-studies)
* [Manifest Data Model](#manifest-data-model)

## What is a pm Manifest?

A pm _Manifest_ is an RDF file that describes and links to a set of files, usually stored in version control, that can be validated and managed by the pm tool. Usual management goals are:

* **validation** - checking content conforms to [SHACL Shapes Graphs](https://www.w3.org/TR/shacl12-core/#shapes-graph)
* **synchronisation** - maintaining data in an RDF DB up-to-date with files
* **labelling** - finding things that are missing labels and proving labels

A simple Manifest file, for [Geoscience Australia's vocabularies]() online at <https://github.com/GeoscienceAustralia/ga-vocabs/blob/master/manifest.ttl>, looks like this:

```turtle
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
PREFIX prez: <https://prez.dev/>
PREFIX prof: <http://www.w3.org/ns/dx/prof/>
PREFIX schema: <https://schema.org/>

[]
    a prez:Manifest ;
    prof:hasResource
        [
            prof:hasartefact "catalogue.ttl" ;
            prof:hasRole mrr:CatalogueData ;
            schema:name "Catalogue Definition" ;
        ] ,
        [
            prof:hasartefact "vocabularies/*.ttl" ;
            prof:hasRole mrr:ResourceData ;
            schema:name "Resource Data" ;
            dcterms:conformsTo <https://linked.data.gov.au/def/vocpub/validator> ;
        ] ,
        [
            prof:hasartefact "labels.ttl" ;
            prof:hasRole mrr:CompleteCatalogueAndResourceLabels ;
            schema:name "Labels" ;
        ] ;
.
```

In the file above, we have a `prez:Manifest` object which has 3 `prof:resource` instances, one for the "Catalogue Definition", the vocabularies - "Resource Data" - and "Labels". The vocabularies are shown to be conformant to the [VocPub profile of SKOS](https://linked.data.gov.au/def/vocpub/spec) which they will be validated against before any data synchronisation.

The complete data model of a pm Manifest file is online at: <https://prez.dev/manifest/>.

## Functions

The functions provided my pm are discoverable by running the tool as a command line application - see [Command Line](#command-line) below - and are:

* **validate**
    * performs SHACL validation on the Manifest, followed by existence checking for each resource - are they reachable
      by this script on the file system or over the Internet? Will also check
      any [Conformance Claims](#conformance-claims) given in the Manifest)
* **label**
    * lists all the IRIs for elements within a Manifest's resources that don't have labels. Given a source of additional
      labels, it can try to extract any
      missing labels and insert them into a Manifest as an additional labelling resource
        *  [KurrawongAI's Semantic Background](#kurrawongai-semantic-background) is included as a source of labels be default 
* **document**
    * **table**: can create a Markdown or ASCIIDOC table of Resources from a Prez Manifest file for use in README files
      in repositories
    * **catalogue**: add the IRIs of resources within a Manifest's 'Resource Data' object to a catalogue RDF file
* **sync**
    * synchronises resources listed in a Manifest with versions of them in a SPARQL Endpoint
    * acts as `load` if run against an empty SPARQL Endpoint
    * does not yet load background resources
*  **event**
    * event-based Prez Manifests actions - for advanced systems use

## Installation

This Python package is intended to be used as a Python library, called directly from other Python code, or on the
command line on Linux/UNIX-like systems.

### Library

It is available on [PyPI](https://pypi.org) at <https://pypi.org/project/prezmanifest/> so can be installed
using [Poetry](https://python-poetry.org) or PIP etc. We do recommend [UV](https://github.com/astral-sh/uv) as that's
the package manager we find easiest to work with.

### Command Line

To make available the command line script `pm` you need to first install `UV`, see
the [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv tool install prezmanifest
```

Now you can invoke `pm` anywhere in your terminal as long as `/local/bin/` is in your `PATH`.

### Latest

You can also always install the latest, unstable, release from its version control
repository: <https://github.com/Kurrawong/prez-manifest/>, but we make prezmanifest releases often, so the latest
shouldn't ever be too far ahead of the most recent release.

## Use

> [!TIP]
> See the [Case Study: Establish](#case-study-establish) below for a short description of the
> establishment of a new catalogue using prezmanifest.

### Library

Install as above and then, in your Python code, import the functions you want to use. Currently, these are the public
functions:

```python
from prezmanifest.validator import validate
from prezmanifest.labeller import LabellerOutputTypes, label
from prezmanifest.documentor import table, catalogue
from prezmanifest.loader import load
from prezmanifest.syncer import sync
```

### Command Line

All the functions of the library are made available as a command line application called `pm`. After installation, as
above, you can inspect the command line tool by asking for "help" like this:

```bash
pm -h
```

Which will print something like this:

```bash
Usage: pm [OPTIONS] COMMAND [ARGS]...

PrezManifest top-level Command Line Interface. Ask for help (-h) for each Command

╭─ Options ────────────────────────────────────────────────────────────────────────╮
│ --version  -v                                                                    │
│ --help     -h        Show this message and exit.                                 │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────╮
│ validate  Validate the structure and content of a Prez Manifest                  │
│ sync      Synchronize a Prez Manifest's resources with loaded copies of them in  │
│           a SPARQL Endpoint                                                      │
│ label     Discover labels missing from data in a in a Prez Manifest and patch    │
│           them                                                                   │
│ document  Create documentation from a Prez Manifest                              │
│ load      Load a Prez Manifest's content into a file or DB                       │
│ event     Event-based Prez Manifests actions                                     │
╰──────────────────────────────────────────────────────────────────────────────────╯
```

To find out more about each Command, ask for helo like this - for load:

```bash
pm load -h
```

> [!NOTE]
> If (when?) pm runs into problems such as trying to synchronise resources between files and an RDF DB with missmatching version numbers, you can always run [kurra](https://github.com/kurrawong.kurra) commands to directly manage DB resources.
> 
> For example, you can run `kurra db gsp put {FILE} {SPARQL-ENDPOINT} -g {GRAPH-NAME}` to force a replacement of the grapf, `GRAPH-NAME`, in the RDF DB with the contents of the `FILE`.

#### Logging

You can control the verbosity of the command line tool by setting the `PM_LOG_LEVEL` environment variable to one of
Python's standard logging levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. The default level is `WARNING`.

For example, to see detailed debug output:

```bash
PM_LOG_LEVEL=DEBUG pm load file my-manifest.ttl output.trig
```

Or for informational messages:

```bash
PM_LOG_LEVEL=INFO pm validate my-manifest.ttl
```

> [!TIP]
> See the [Case Study: Sync](#case-study-sync) below for a description of the different ways to sync

## Testing

Run `uv run pytest`, or Poetry etc. equivalents, to execute pytest. You must have Docker Desktop running to allow all
loader tests to be executed as some use temporary test containers.

## Extending

Many functions have been placed into `prezmanifest/utils.py` and hopefully extensions can be made to individual
functions there.

For example, to extend the criteria `prezmanifest` uses to judge the newness of a local v. a remote artefacts for the
`sync` function, see the [`compare_version_indicators()`](prezmanifest/utils.py#L397)

## License

This code is available for reuse according to the [BSD 3-Clause License](https://opensource.org/license/bsd-3-clause).

&copy; 2024-2025 KurrawongAI

## Contact

For all matters, please contact:

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>

## Case Studies

### Case Study: Establish

The Indigenous Studies Unit Catalogue is a new catalogue of resources - books, articles, boxes of archived documents -
produced by
the [Indigenous Studies Unit](https://mspgh.unimelb.edu.au/centres-institutes/onemda/research-group/indigenous-studies-unit)
at the [University of Melbourne](https://www.unimelb.edu.au).

The catalogue is available online via an instance of the [Prez](https://prez.dev) system at <https://data.idnau.org/pid/isu-catalogue>
and the content is managed in the GitHub repository <https://github.com/idn-au/isu-catalogue>.

The catalogue container object is constructed as a `schema:DataCatalog` (and also a `dcat:Catalog`, for compatibility
with legacy systems) containing multiple `schema:CreativeWork` instances with subtyping to indicate 'book', 'artwork'
etc.

The source of the catalogue metadata is the static RDF file `_background/catalogue-metadata.ttl` that was made by hand.

The source of the resources' information is the CSV file `_background/datasets.csv` which was created by hand during a
visit to the Indigenous Studies Unit. This CSV information was converted to RDF files in `resources/` using the custom
script `_background/resources_make.py`.

After creation of the catalogue container object's metadata and the primary resource information, prezmanifest was used
to improve the presentation of the data in Prez in the following ways:

1. A manifest files was created
    * based on the example in this repository in `tests/demo-vocabs/manifest.ttl`
    * the example was copy 'n pasted with only minor changes, see `manifest.ttl` in the ISU catalogue repo
    * the initial manifest file was validated with prezmanifest/validator: `pm validate isu-catalogue/manifest.ttl`
2. A labels file was automatically generated using prezmanifest/labeller
    * using the [KurrawongAI Semantic Background](https://github.com/Kurrawong/semantic-background) as a source of
      labels
    * using the command `pm label rdf isu-catalogue/manifest.ttl http://demo.dev.kurrawong.ai/sparql > labels.ttl`
    * the file, `labels.ttl` was stored in the ISU Catalogue repo `_background/` folder and indicated in the manifest
      file with the role of _Incomplete Catalogue And Resource Labels_ as it doesn't provide all missing labels
        * note that this storage could have been done automatically using the `pm label manifest` command
3. IRIs still missing labels were determined
    * using prezmanifest/labeller again with the command `pm label iris isu-catalogue/manifest.ttl > iris.txt`, all IRIs
      still missing labels were listed
4. Labels for remaining IRIs were manually created
    * there were only 7 important IRIs (as opposed to system objects that don't need labels) that still needed labels.
      These where manually created in the file `_background/labels-manual.ttl`
    * the manual labels file was added to the catalogue's manifest, also with a role of _Incomplete Catalogue And
      Resource Labels_
5. A final missing labels test was performed
    * running `pm label iris isu-catalogue/manifest.ttl > iris.txt` again indicated no important IRIs were still missing
      labels
6. The catalogue was enhanced
    * `pm document catalogue isu-catalogue/manifest.ttl` was run to add all the resources of the catalogue to the
      `catalogue.ttl` file
7. The manifest was documented
    * using prezmanifest/documentor, a Markdown table of the manifest's content was created using the command
      `pm document table isu-catalogue/manifest.ttl`
    * the output of this command - a Markdown table - is visible in the ISU Catalogue repo's README file.
8. The catalogue was prepared for upload
    * `pm load file isu-catalogue/manifest.ttl isu-catalogue.trig` was run
    * it produced a single _trig_ file `isu-catalogue.trig` containing RDF graphs which was one-time uploaded to the
      database delivering the catalogue
9. The catalogue and repo were synchronised
    * `pm sync` was then used repeatedly to synchronise updates to the files in version control with the RDF BY read by Prez

### Case Study: Sync

If I have a manifest locally, I can load it into a remote SPARQL Endpoint like this:

```bash
pm load sparql {PATH-TO-MANIFEST} {SPARQL-ENDPOINT}
```

Going forward, I don't have to blow away all the content in the SPARQL Endpoint and reload everything whenever I have
content changes, instead I can use the `sync` command.

`sync` compares "version indicators" per artefact, determines which is more recent and then reports on whether the local
artefact should be uploaded, teh remote one downloaded or whether there are new artefacts present locally or remotely.

The `tests/test_sync/` directory in this repository contains a _local_ and a _remote_ manifest and content. Following
the logic in the testing function `tests/test_sync/test_sync.py::test_sync`, if the _remote_ manifest is loaded, as per
`pm load sparql tests/test_sync/remote/manifest.ttl {SPARQL-ENDPOINT}` and then `sync` is run like this:

```bash
pm sync tests/test_sync/local/manifest.ttl {SPARQL-ENDPOINT}
```

You will see a report like this:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ artefact                          ┃ Main Entity                   ┃ Direction    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ /../../../artefact4.ttl           │ http://example.com/dataset/4  │ upload       │
│ /../../../artefact5.ttl           │ http://example.com/dataset/5  │ add-remotely │
│ /../../../artefact6.ttl           │ http://example.com/dataset/6  │ download     │
│ /../../../artefact7.ttl           │ http://example.com/dataset/7  │ upload       │
│ /../../../artefact9.ttl           │ http://example.com/dataset/9  │ same         │
│ /../../../artefacts/artefact1.ttl │ http://example.com/dataset/1  │ same         │
│ /../../../artefacts/artefact2.ttl │ http://example.com/dataset/2  │ upload       │
│ /../../../artefacts/artefact3.ttl │ http://example.com/dataset/3  │ upload       │
│ /../../../catalogue.ttl           │ https://example.com/sync-test │ same         │
│ http://example.com/dataset/8      │ http://example.com/dataset/8  │ add-locally  │
└───────────────────────────────────┴───────────────────────────────┴──────────────┘
```

This is telling you, per artefact, what `sync` will do.

* the local copy of `artefact4.ttl` is newer than the remote one, so it wants to "upload"
* the remote location is missing `artefact5.ttl`, so it wants to upload that too
* `artefact9` is the "same" - no action required
* `artefact6.ttl` is newer remotely, it should be downloaded

You can choose to have `sync` carry out all these actions or only some - default is all - by setting the `update_remote`
and so on input parameters. Setting all to `False` will cause `sync` to do nothing and report only what it _would_ do if
they were not set, e.g.:

```bash
pm sync tests/test_sync/local/manifest.ttl http://localhost:3030/test/ False False False False
```

Other than doing all this "manually" - interactively, on the command line - I might want to use `sync` in Python
application code or cloud _infracode_ scriptin.

For use in Python applications, just import prezmanifest - `uv add prezmanifest` etc. - and use, as per the use of
`sync` in `tests/test_sync/test_sync.py::test_sync`.

For use in _infracode_, note that the `pm sync` function can return the table above in JSON by setting the
`response format` input parameter, `-f`.

## Manifest Data Model

``` mermaid
graph LR
  Manifest --1:1-N--> Resource;
  Resource --1:1--> artifact;
  Resource --1:1--> role;
  Resource --1:0-1--> name;
  Resource --1:0-1--> decription;
```

The Manifest Model is simply a Manifest class, `prez:Manifest`, which MUST have 1 or more Resource Descriptors, `prof:ResourceDescriptor` indicated by the `prof:hasResource` predicate. 

Each Resource Descriptor MUST have exactly one `prof:hasArtifact` predicate indicating an RDF literal resource (string) giving a file path or path pattern containing the resource information, relative to the manifest.

Each Resource Descriptor MUST also have exactly one `prof:hasRole` predicate indicating a Concept from the _Manifest Resource Roles Vocabulary_.

Each Resource Descriptor MAY have a `schema:name` and/r a `schema:description` predicate indicating literal resources naming and describing it.

### Manifest Resource Roles Vocabulary

This roles vocabulary contains the allowed roles that a resource can play with respect to a Manifest.

The IRI of this vocabulary is:

* `https://prez.dev/ManifestResourceRoles`
    * the vocab namespace is `https://prez.dev/ManifestResourceRoles/`
    * recommended namespace prefix is `mrr`

Human-readable form:

| Concept IRI                               | Label                                   | Definition                                                                                                          | Parent                         |
|-------------------------------------------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------|
| `mrr:ContainerData`                       | Container Data                          | Data for the container, usually a Catalogue, including the identity of it and each item fo content                  | -                              |
| `mrr:ContentData`                         | Content Data                            | Data for the content of the container                                                                               | -                              |
| `mrr:ContainerAndContentModel`            | Container & Content Model               | The default model for the container and the content. Must be a set of SAHCL Shapes                                  | -                              |
| `mrr:ContainerModel`                      | Container Model                         | The default model for the container. Must be a set of SAHCL Shapes                                                  | `mrr:containerAndContentModel` |
| `mrr:ContentModel`                        | Content Model                           | The default model for the content. Must be a set of SAHCL Shapes                                                    | `mrr:containerAndContentModel` |
| `mrr:CompleteContainerAndContentLabels`   | Complete Content and Container Labels   | All the labels - possibly indluding names, descriptions & seeAlso links - for the Container and Content objects     | -                              |
| `mrr:IncompleteContainerAndContentLabels` | Incomplete Content and Container Labels | Some of the labels - possibly indluding names, descriptions & seeAlso links - for the Container and Content objects | -                              |

* <https://github.com/Kurrawong/prezmanifest/blob/main/prezmanifest/mrr.ttl>

### Validation

#### SHACL Validation

This [SHACL](https://www.w3.org/TR/shacl/) validator Shapes Graph file can be used by SHACL validation software such as 
[pySHACL](https://pypi.org/project/pyshacl/), to test the validity of a Manifest's RDF file with respect to this model:

* <https://github.com/Kurrawong/prezmanifest/blob/main/prezmanifest/validator.ttl>

This Shapes Graph is also loaded in to KurrawongAI's Semantic Background and is available via their validator tool 
online and can be selected there for use via the "Use Validators" button:

* <https://tools.kurrawong.ai/validate>

#### pm validation

Validation beyond just SHACL is needed for an effective manifest as the `manifest.ttl` file necessarily indicates 
other resources that must be present and correct for the whole manifest to work. To validate all aspects of a manifest,
use the in-build PrezManifest command: `pm validate {PATH-TO-MANIFEST-FILE}`.

This function also validates the contents linked to in the manifest as per their [Conformance Claims](#conformance-claims).

This pm validation is automatically performed before other pm commands like `sync`.

#### Conformance Claims

A claim that some data conforms to a standard or a profile. In Prez Manifest, this is about indicating that a Resource
is expected to conform to a standard.

In the [Geoscience Australia Vocabs' manifest](https://github.com/GeoscienceAustralia/ga-vocabs/blob/master/manifest.ttl),
there is a conformance claim for the vocabs to the [VocPub Profile's Validator](https://linked.data.gov.au/def/vocpub/validator)
which looks like this:

```turtle
#...
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX mrr: <https://prez.dev/ManifestResourceRoles/>
PREFIX prof: <http://www.w3.org/ns/dx/prof/>
        
[
    prof:hasArtifact "vocabularies/*.ttl" ;
    prof:hasRole mrr:ResourceData ;
    dcterms:conformsTo <https://linked.data.gov.au/def/vocpub/validator> ;
] .
#...
```

`pm validate` will acquire validators indicated in conformance claims, either from KurrawongAI's Semantic Background, or
from a locally-supplied SHACL validator Shapes Graph, and will validate all resources within that manifest resource with
it. In the GA Vocabs above, all vocabulary files in the path `"vocabularies/*.ttl"` will be validated with VocPub.

### Semantic Background

[KurrawongAI](https://kurrawong.ai) makes available about 100 well-known ontologies, 50 or so Shapes GRaph validators
and many vocabularies within its _Semantic Background_, an online reference dataset of RDF content that PrezManifest can 
access. this allows pm to acquire many labels for RDF elements within a manifest's resources and to validate resource 
without the user needing to supply anything.

You can see exactly what's in the Semantic Background, which is set up using PrezManifest manifests, here:

* <https://github.com/Kurrawong/semantic-background>

## Release Procedure

* format code: `task format`
* pass tests: `task test`
* update version in pyproject.toml
* commit all updates: `git commit -a "..."`
* make GitHub release
  * this will trigger pypi.yml workflow to publish to PyPI
* update version in pyproject.toml to next release alpha and push
