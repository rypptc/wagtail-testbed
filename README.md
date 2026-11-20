# wagtail-testbed

A Wagtail project for testing that needs a realistic site with a large number of pages. It was originally created to test the wagtail-localize package, but it can be useful for other tests. The aim is to make it easy to adapt to other purposes.

To fill the site we used content from [MDN Web Docs](https://developer.mozilla.org) (the `mdn/content` repository), about 14,700 English pages at the pinned version, organized the way a Wagtail site would be:

- the pages form a page tree that follows MDN's own structure;
- each page body is converted from Markdown into StreamField blocks (headings, paragraphs, code, callouts, tables);
- the metadata in each document's header is modelled as fields and relations: page type, status, spec URLs and browser-compat keys.

This repository holds only the site's code. By default, the build script downloads MDN's content at a fixed version, so everyone gets the same site. You can also build it from MDN's latest content, though the build may then fail if MDN has changed in ways the importer does not expect yet.

## Getting started

Setup instructions will be added once the build scripts are in place.

## Credits and licence

MDN content is © Mozilla Contributors, licensed under [CC-BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/). This project is not affiliated with or endorsed by Mozilla.

The code in this repository is licensed under the MIT License (see `LICENSE`).
