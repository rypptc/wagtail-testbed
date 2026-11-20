# wagtail-testbed

A Wagtail project for testing that needs a realistic site with a large number of pages. It was originally created to test the wagtail-localize package, but it can be useful for other tests. The aim is to make it easy to adapt to other purposes.

To fill the site we used content from [MDN Web Docs](https://developer.mozilla.org) (the [mdn/content](https://github.com/mdn/content) repository), about 14,700 English pages at the pinned version, organized the way a Wagtail site would be:

- the pages form a page tree that follows MDN's own structure;
- each page body is converted from Markdown into StreamField blocks (headings, paragraphs, code, callouts, tables);
- the metadata in each document's header is modelled as fields and relations: page type, status, spec URLs and browser-compat keys.

See [docs/content-model.md](docs/content-model.md) for how each MDN document is stored.

With `--translations`, the site also gets MDN's translations from [mdn/translated-content](https://github.com/mdn/translated-content): about 37,300 pages in eight languages (es, fr, ja, ko, pt-br, ru, zh-cn, zh-tw). They are created with Wagtail's `copy_for_translation`, which makes a copy of each English page in the other language, linked to it. They are not registered in wagtail-localize. A smaller set of pages will be translated through wagtail-localize itself; that part is not built yet. See [docs/content-model.md](docs/content-model.md#translations).

This repository holds only the site's code. By default, the build script downloads MDN's content at a fixed version, so everyone gets the same site. You can also build it from MDN's latest content, though the build may then fail if MDN has changed in ways the importer does not expect yet.

## Getting started

You need Python 3.13, [uv](https://docs.astral.sh/uv/), git and PostgreSQL.

```sh
git clone https://github.com/rypptc/wagtail-testbed.git
cd wagtail-testbed
uv sync
createdb wagtail_testbed
uv run python manage.py migrate
uv run python manage.py build_mdn
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

`build_mdn` downloads MDN's content into `data/`, loads the page tree and fills each page's body. The full site takes a while; to try it on one section first, use `--prefix`, e.g. `build_mdn --prefix web/css`. To use MDN's latest content instead of the pinned version, add `--latest`.

To add MDN's translations, run `build_mdn --translations` instead. It also downloads mdn/translated-content and creates the translated pages before filling the bodies. This takes much longer than the English build; on a laptop, `caffeinate -i` (macOS) keeps it from stopping when the computer sleeps. Each language is served under its own prefix, e.g. `/en/…` and `/es/…`.

The database is `wagtail_testbed` on the local PostgreSQL server, with your system user. To use another database or server, set `TESTBED_DB_NAME`, `TESTBED_DB_USER`, `TESTBED_DB_PASSWORD`, `TESTBED_DB_HOST` and `TESTBED_DB_PORT`.

`build_mdn` is meant for an empty database. Running `fill_bodies` again rebuilds every body from MDN's files, so changes made to the bodies in the admin are lost.

## Credits and licence

MDN content is © Mozilla Contributors, licensed under [CC-BY-SA 2.5](https://creativecommons.org/licenses/by-sa/2.5/). This project is not affiliated with or endorsed by Mozilla.

The code in this repository is licensed under the MIT License (see [LICENSE](LICENSE)).
