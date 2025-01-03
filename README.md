# Prez Manifest

A Prez Manifest is an RDF file that describes and links to a set of resources that can be loaded into an RDF database for the [Prez graph database publication system](http://prez.dev) to provide access to.

The Prez Manifest specification is online at:

* <https://prez.dev/manifest/>

This repository contains the `prez-manifest` Python package that provides a series of functions to work with Prez Manifests. The functions provided are:

* `create_table`: creates an ASCIIDOC or Markdown table of Manifest content from a Manifest file
* `validate`: validates that a Manifest file conforms to the specification and that all linked-to assets are available
* `load`: loads a Manifest file, and all the content it specifies, into either an n-quads file or a Fuseki database


## Installation & Use

This Python package is intended to be used on the command line on Linux/UNIX-like systems and/or as a Python library, called directly from other Python code.

It is available on [PyPI](https://pypi.org) at <https://pypi.org/project/prezmanifest/> so can be installed using [Poetry](https://python-poetry.org) or PIP.

You can also install the latest, unstable, release from it's version control repository: <https://github.com/Kurrawong/prez-manifest/>.

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