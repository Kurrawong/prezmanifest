# Prez Manifest

This repository contains the `prezmanifest` Python package that provides a series of functions to work with Prez Manifests.

_A Prez Manifest is an RDF file that describes and links to a set of resources that can be loaded into an RDF database for the [Prez graph database publication system](http://prez.dev) to provide access to. The Prez Manifest specification is online at: <https://prez.dev/manifest/>._

The functions provided are:

* **validate**
    * performs SHACL validation on the Manifest, followed by existence checking for each resource - are they reachable by this script on the file system or over the Internet? Will also check any [Conformance Claims](#conformance-claims)given in the Manifest)
* **label**
    * lists all the IRIs for elements with a Manifest's Resources that don't have labels. Given a source of additional labels, such as the [KurrawongAI Semantic Background](#kurrawongai-semantic-background), it can try to extract any missing labels and insert them into a Manifest as an additional labelling resource
* **document**
    * **table**: can create a Markdown or ASCCIIDOC table of Resources from a Prez Manifest file for use in README files in repositories
    * **catalogue**: add the IRIs of resources within a Manifest's 'Resource Data' object to a catalogue RDF file
* **load**
    *  extract all the content of all Resources listed in a Prez Manifest and load it into either a single RDF multi-graph ('quads') file or into an RDF DB instance by using the Graph Store Protocol

## Installation

This Python package is intended to be used on the command line on Linux/UNIX-like systems and/or as a Python library, called directly from other Python code.

### Library 

It is available on [PyPI](https://pypi.org) at <https://pypi.org/project/prezmanifest/> so can be installed using [Poetry](https://python-poetry.org) or PIP etc. We do recommend [UV](https://github.com/astral-sh/uv) as the package manager we find easiest to work with.

### Command Line

To make available the command line script `pm` you need to first install `UV`, see the [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv tool install prezmanifest
```

Now you can invoke `pm` anywhere in your termina as long as `~/,local/bin/` is in your `PATH`.

### Latest

You can also always install the latest, unstable, release from its version control repository: <https://github.com/Kurrawong/prez-manifest/>, but we make prezmanifest releases often, so the latest shouldn't ever be too far ahead of the most recent release.

## Use

> [!TIP]
> See the [Case Study](#case-study---indigenous-studies-unit-catalogue) below for a short description of the 
> establishment of a new catalogue using prezmanifest.

### Library

Install as above and then, in your Python code, import the functions you want to use. Currently, these are the public functions:

```python
from prezmanifest.validator import validate
from prezmanifest.labeller import LabellerOutputTypes, label
from prezmanifest.documentor import table, catalogue
from prezmanifest.loader import load
```

### Command Line

All the functions of the library are made available as a command line application called `pm`. After installation, as above, you can inspect the command line tool by asking for "help" like this:

```bash
pm -h
```

Which will print something like this:

```
PrezManifest top-level Command Line Interface. Ask for help (-h) for each Command                        
                                                                                                          
╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version  -v                                                                                          │
│ --help     -h        Show this message and exit.                                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────╮
│ validate   Validate the structure and content of a Prez Manifest                                       │
│ label      Discover labels missing from data in a in a Prez Manifest and patch them                    │
│ document   Create documentation from a Prez Manifest                                                   │
│ load       Load a Prez Manifest's content into a file or DB                                            │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

To find out more about each Command, ask for helo like this - for load:

```bash
pm load -h
```

## Testing

Run `uv run pytest`, or Poetry etc. equivalents, to execute pytest. You must have Docker Desktop running to allow all loader tests to be executed as some use temporary test containers.

## License

This code is available for reuse according to the https://opensource.org/license/bsd-3-clause[BSD 3-Clause License].

&copy; 2024-2025 KurrawongAI

## Contact

For all matters, please contact:

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>  

## Background concepts & other resources

The amin documentation for Prez Manifests - what they are, how to make them etc., is online at <https://prez.dev>, however, here are also two concepts referred to above, summarised.

### Conformance Claims

A claim that some data conforms to a standard or a profile. In Prez Manifest, this is about indicating that a Resource should and is expected to conform to a standard.

See the various Manifest files in `tests/demo-vocabs/` for examples of them in use for individual resources or all resources, e.g. `tests/demo-vocabs/manifest-conformance.ttl`

### KurrawongAI Semantic Background

[KurrawongAI](https://kurrawong.ai) makes available labels for all the elements of about 100 well-known ontologies and vocabularies at <https://demo.dev.kurrawong.ai/catalogs/exm:demo-vocabs>. You can use this as a source (SPARQL Endpoint) of labels to patch content in Manifests that are missing labels with.

## Case Study - Indigenous Studies Unit Catalogue

The Indigenous Studies Unit Catalogue is a new catalogue of resources - books, articles, boxes of archived documents - 
produced by the [Indigenous Studies Unit](https://mspgh.unimelb.edu.au/centres-institutes/onemda/research-group/indigenous-studies-unit) 
at the [University of Melbourne](https://www.unimelb.edu.au).

The catalogue is available online via an instance of the [Prez](https://prez.dev) system at <https://data.idnau.org>
and the content is managed in the GitHub repository <https://github.com/idn-au/isu-catalogue>.

The catalogue container object is constructed as a `schema:DataCatalog` (and also a `dcat:Catalog`, for compatibility 
with legacy systems) containing multiple `schema:CreativeWork` instances with subtyping to indicate 'book', 'artwork' 
etc.

The source of the catalogue metadata is the static RDF file `_background/catalogue-metadata.ttl` that was handwritten.

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
    * using the [KurrawongAI Semantic Background](https://demo.dev.kurrawong.ai/catalogs/exm:demo-vocabs) as a source of labels
    * using the command `pm label rdf isu-catalogue/manifest.ttl http://demo.dev.kurrawong.ai/sparql > labels.ttl`
    * the file, `labels.ttl` was stored in the ISU Catalogue repo `_background/` folder and indicated in the manifest 
      file with the role of _Incomplete Catalogue And Resource Labels_ as it doesn't provide all missing labels
       * note that this storage could have been done automatically using the `pm label manifest` command
3. IRIs still missing labels were determined
    * using prezmanifest/labeller again with the command `pm label iris isu-catalogue/manifest.ttl > iris.txt`, all IRIs still missing labels were listed
4. Labels for remaining IRIs were manually created
    * there were only 7 important IRIs (as opposed to system objects that don't need labels) that still needed labels. These where manually created in the file `_background/labels-manual.ttl`
    * the manual labels file was added to the catalogue's manifest, also with a role of _Incomplete Catalogue And Resource Labels_
5. A final missing labels test was performed
    * running `pm label iris isu-catalogue/manifest.ttl > iris.txt` again indicated no important IRIs were still missing labels
6. The catalogue was enhanced
    * `pm document catalogue isu-catalogue/manifest.ttl` was run to add all the resources of the catalogue to the `catalogue.ttl` file
7. The manifest was documented
    * using prezmanifest/documentor, a Markdown table of the manifest's content was created using the command `pm document table isu-catalogue/manifest.ttl`
    * the output of this command - a Markdown table - is visible in the ISU Catalogue repo's README file.
8. The catalogue was prepared for upload
    * `pm load file isu-catalogue/manifest.ttl isu-catalogue.trig` was run
    * it produced a single _trig_ file `isu-catalogue.trig` containing RDF graphs which can easily be uploaded to the 
      database delivering the catalogue
    * `pm load sparql isu-catalogue/manifest.ttl http://a-sparql-endpoint.com/ds -u username -p password` could have been run to load the content directly into the ISU RDF DB, if it had been available
