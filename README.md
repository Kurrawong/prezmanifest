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


## Testing

Run `python -m pytest` in the top-level folder to test. You must have Docker Desktop running to allow all loader tests to be executed.


## License

This code is available for reuse according to the https://opensource.org/license/bsd-3-clause[BSD 3-Clause License].

&copy; 2024-2025 KurrawongAI


## Contact

For all matters, please contact:

**KurrawongAI**  
<info@kurrawong.ai>  
<https://kurrawong.ai>  