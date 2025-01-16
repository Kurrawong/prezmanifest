# Prez Manifest

_A Prez Manifest is an RDF file that describes and links to a set of resources that can be loaded into an RDF database for the [Prez graph database publication system](http://prez.dev) to provide access to. The Prez Manifest specification is online at: <https://prez.dev/manifest/>._

This repository contains the `prezmanifest` Python package that provides a series of functions to work with Prez Manifests. The functions provided are:

* **documentation**: 
    * `create_table` creates an ASCIIDOC or Markdown table of Manifest content from a Manifest file
    * `create_catalgue`: creates an RDF file from catalogue metadata and with `hasPart` relations to all resources indicated in the Manifest 
* `validate`: validates that a Manifest file conforms to the specification and that all linked-to assets are available
* `load`: loads a Manifest file, and all the content it specifies, into either an n-quads file or a Fuseki database
* `labeller`: lists IRIs for which no labels are present in any Manifest resource or outputs an RDF file of labels for IRIs missing them if additional context (files or folders of RDF or a SPARQL Endpoint) are supplied. Can also create a new resource within a Manifest containing newly generated labels 


## Installation & Use

This Python package is intended to be used on the command line on Linux/UNIX-like systems and/or as a Python library, called directly from other Python code.

It is available on [PyPI](https://pypi.org) at <https://pypi.org/project/prezmanifest/> so can be installed using [Poetry](https://python-poetry.org) or PIP.

You can also install the latest, unstable, release from its version control repository: <https://github.com/Kurrawong/prez-manifest/>.

Please see the `documentor.py`, `loader.py`, & `validator.py` files in the `prezmanifest` folder and the test files in `test` for documentation text and examples of use.

> [!TIP]
> See the [Case Study](#case-study---indigenous-studies-unit-catalogue) below for a short description of the 
> establishment of a new catalogue using prezmanifest.


## Testing

Run `python -m pytest` or `poetry run pytest` r similar - to execute pytest - in the top-level folder to test. You must have Docker Desktop running to allow all loader tests to be executed.


## License

This code is available for reuse according to the https://opensource.org/license/bsd-3-clause[BSD 3-Clause License].

&copy; 2024-2025 KurrawongAI


## Contact

For all matters, please contact:

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>  


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
    * based on the example in this repository in `tests/demo-vocabs/manifet.ttl`
    * the example was copy 'n pasted with only minor changes, see `manifest.ttl` in the ISU catalogue repo
    * the initial manifest file was validated with prezmanifest/validator: `python prezmanifest/validator.py isu-catalogue/manifest.ttl`
2. A labels file was automatically generated using prezmanifest/labeller
    * using the [KurrawongAI Semantic Background](https://demo.dev.kurrawong.ai) as a source of labels
    * using the command `python prezmanifest/labeller.py -o rdf -a http://demo.dev.kurrawong.ai/sparql isu-catalogue/manifest.ttl > labels.ttl`
    * the file, `labels.ttl` was stored in the ISU Catalogue repo `_background/` folder and indicated in the manifest 
      file with the role of _Incomplete Catalogue And Resource Labels_ as it doesn't provide all missing labels
3. IRIs still missing labels were determined
    * using prezmanifest/labeller again with the command `python prezmanifest/labeller.py -o iris -a http://localhost:3030/ds/query isu-catalogue/manifest.ttl > iris.txt`, 
      all IRIs still missing labels were listed
4. Labels for remaining IRIs were manually created
    * there were only 7 important IRIs (as opposed to system objects that don't need labels) that still needed labels. 
      These where manually created in the file `_background/labels-manual.ttl`
    * the manual labels file was added to the catalogue's manifest, also with a role of _Incomplete Catalogue And 
      Resource Labels_
5. A final missing labels test was performed
    * running `python prezmanifest/labeller.py -o iris -a http://localhost:3030/ds/query isu-catalogue/manifest.ttl > iris.txt`
      again indicated no important IRIs were still missing labels
6. The catalogue was enhanced
    * using prezmanifest/documentor, the command `python prezmanifest/documentor.py catalogue ~/work/idn/isu-catalogue/manifest.ttl`
      was run to add all the resources of the catalogue to the `catalogue.ttl` file
7. The manifest was documented
    * using prezmanifest/documentor, a Markdown table of the manifest's content was created using the command 
      `python prezmanifest/documentor.py table ~/work/idn/isu-catalogue/manifest.ttl`
    * the output of this command - a Markdown table - is visible in the ISU Catalogue repo's README file.
8. The catalogue was prepared for upload
    * using prezmanifest/loader the command `python prezmanifest/loader.py -d isu-catalogue.trig ~/work/idn/isu-catalogue/manifest.ttl`
      was run
    * it produced a single _trig_ file `isu-catalogue.trig` containing RDF graphs which can easily be uploaded to the 
      database delivering the catalogue

