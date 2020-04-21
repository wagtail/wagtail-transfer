# Welcome to the Wagtail Transfer Documentation

<img alt="Wagtail Transfer logo with two facing wagtails" src="img/wagtail_transfer_logo.svg" height="25%" width="25%">

[Wagtail Transfer](https://github.com/wagtail/wagtail-transfer) is an extension for the [Wagtail CMS](https://github.com/wagtail/wagtail) which allows content to be transferred between multiple instances of a
Wagtail project: for example, from a staging site to a production site.

## Features
* Imports Page trees from other Wagtail instances
* Identifies previously imported content and updates it instead
* Imports referenced models such as images, documents, and snippets
* Configurable: can define non-importable models, and models to update
* Import entire models (registered as Snippets) and individual Snippet objects
