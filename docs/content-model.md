# Content model

This document explains how an MDN document becomes a page in this site.

## Where the content comes from

Each MDN page is a Markdown file called `index.md` in the [mdn/content](https://github.com/mdn/content) repository. For example, the page for [`Array.prototype.map()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map) comes from [this file](https://github.com/mdn/content/blob/main/files/en-us/web/javascript/reference/global_objects/array/map/index.md).

Each file has two parts:

- the **header** (front matter), between the two `---` lines at the top: data about the page, written as YAML;
- the **body**, everything after it: the text of the page, in Markdown.

This is the header of `map()`:

```yaml
---
title: Array.prototype.map()
short-title: map()
slug: Web/JavaScript/Reference/Global_Objects/Array/map
page-type: javascript-instance-method
browser-compat: javascript.builtins.Array.map
sidebar: jsref
---
```

The header is not shown as text on MDN. MDN uses it to build parts of the page: the title, the short name in the sidebar, the browser compatibility table.

The keys are defined in MDN's [front matter schema](https://github.com/mdn/content/blob/main/front-matter-config.json), and MDN's writing guidelines explain most of them one by one (linked in the table below).

## The page tree

Every `index.md` becomes a `DocPage`. The folders give the tree: `web/javascript/reference/global_objects/array/map` is a child of `.../array`, which is a child of `.../global_objects`, and so on up to the home page.

## The header

Each key in the header is stored in a field of `DocPage`. Each one uses a different way of storing data in Django, which gives the site a variety of cases to test.

| Key | Field | Stored as | Pages with it |
|---|---|---|---|
| [`title`](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Page_structures/Page_types) | `title` | Wagtail's page title | all |
| [`short-title`](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Page_structures/Sidebars) | `short_title` | text | 10,273 |
| [`page-type`](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Page_structures/Page_types/Page_type_key) | `page_type` | a `ForeignKey` to `PageType`, one row per type (95 types) | all |
| `status` (schema only) | `status` | a many-to-many to `Status` (`experimental`, `deprecated`, `non-standard`) | 2,196 |
| [`browser-compat`](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Page_structures/Compatibility_tables) | `browser_compat` | a list of strings in one column (`ArrayField`) | 11,877 |
| [`spec-urls`](https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Page_structures/Specification_tables) | `spec_urls` | a child model, `SpecURL`, one row per URL, in MDN's order | 607 |

Some keys hold one value in some pages and a list in others (`browser-compat`, `spec-urls`). They are always stored as a list, so every page has the same shape.

`status` and `spec_urls` use modelcluster's `ParentalManyToManyField` and `ParentalKey` instead of Django's plain fields, so that their values are kept in Wagtail's revisions and previews.

## The body

The Markdown body is converted into StreamField blocks:

- `heading`: section titles, levels 2 to 4;
- `paragraph`: rich text with bold, italic, inline code, links and lists;
- `code`: code samples, with their language;
- `callout`: MDN's note, warning and callout boxes;
- `table`: tables, with rich text cells.

## What is left out

- `slug`: Wagtail builds its own URL from the folder names, so MDN's slug is not stored.
- `sidebar`: which sidebar MDN shows. Not stored yet.
- The browser compatibility data. The header only holds a key; the data itself lives in another repository, [mdn/browser-compat-data](https://github.com/mdn/browser-compat-data), which is not downloaded. The key is stored, so the data could be added later.
- Parts of the body that the converter does not handle yet, such as images, tables written in HTML and MDN's macros (`{{...}}`).
