"""Fill DocPage.body from each page's MDN markdown, after import_mdn (and
import_translations, for the other locales).

Every DocPage with an mdn_path gets the body converted from its own MDN
document: English pages from mdn/content, translations from
mdn/translated-content (see mdn/converter.py). Links between MDN documents
point to the page in the same locale when it exists, otherwise to the English
one. Aliases keep showing their source page's body.

The body is replaced, not merged: running this again rebuilds every body from
MDN's files, and edits made in the admin are lost.
"""

import frontmatter
from django.core.management.base import BaseCommand
from django.db.models import Q

from mdn.converter import Converter
from mdn.management.commands.import_mdn import FILES_DIR
from mdn.management.commands.import_translations import TRANSLATIONS_DIR
from mdn.models import DocPage


BATCH = 500


def files_dir(code):
    return FILES_DIR if code == "en" else TRANSLATIONS_DIR / code


class Command(BaseCommand):
    help = "Fill DocPage.body from MDN's markdown."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="", help="Only this section, e.g. web/css.")
        parser.add_argument(
            "--locale", action="append",
            help="Only this locale (repeatable). Default: every locale in the site.",
        )

    def handle(self, *args, prefix, locale, **options):
        prefix = prefix.strip("/").lower()

        # Every English MDN path, imported or not: macros only link to pages
        # that exist on MDN.
        english_paths = {
            index.parent.relative_to(FILES_DIR).as_posix()
            for index in FILES_DIR.rglob("index.md")
        }
        # Locale -> MDN path -> page id, aliases included: a link may point at
        # an alias, which shows the English content in that locale's tree.
        page_ids = {}
        for page in DocPage.objects.exclude(mdn_path=None).values("id", "mdn_path", "locale__language_code"):
            page_ids.setdefault(page["locale__language_code"], {})[page["mdn_path"]] = page["id"]

        for code in locale or page_ids:
            def resolve(path, code=code):
                return page_ids.get(code, {}).get(path) or page_ids.get("en", {}).get(path)

            converter = Converter(english_paths, resolve)
            pages = (
                DocPage.objects.filter(locale__language_code=code, alias_of__isnull=True)
                .exclude(mdn_path=None)
                .only("id", "mdn_path")
            )
            if prefix:
                pages = pages.filter(Q(mdn_path=prefix) | Q(mdn_path__startswith=prefix + "/"))

            batch, filled, missing = [], 0, 0
            for page in pages.iterator():
                index = files_dir(code) / page.mdn_path / "index.md"
                if not index.exists():
                    missing += 1
                    continue
                page.body = converter.convert(frontmatter.load(index).content)
                batch.append(page)
                if len(batch) >= BATCH:
                    DocPage.objects.bulk_update(batch, ["body"])
                    filled += len(batch)
                    batch = []
                    self.stdout.write(f"  {code} {filled}")
            if batch:
                DocPage.objects.bulk_update(batch, ["body"])
                filled += len(batch)

            # Aliases show their source page's body, as Wagtail keeps them.
            aliases = list(
                DocPage.objects.filter(locale__language_code=code, alias_of__isnull=False)
                .only("id", "alias_of_id")
            )
            sources = DocPage.objects.in_bulk([alias.alias_of_id for alias in aliases])
            for alias in aliases:
                alias.body = sources[alias.alias_of_id].body
            DocPage.objects.bulk_update(aliases, ["body"])

            self.stdout.write(self.style.SUCCESS(
                f"{code}: filled {filled} pages, {missing} without their MDN file, "
                f"{len(aliases)} aliases synced, {converter.dropped_comments} HTML comments dropped"
            ))
