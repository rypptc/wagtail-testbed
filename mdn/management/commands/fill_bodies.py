"""Fill DocPage.body from each page's MDN markdown, after import_mdn.

Every DocPage with an mdn_path gets the body converted from its index.md (see
mdn/converter.py). The body is replaced, not merged: running this again
rebuilds every body from MDN's files, and edits made in the admin are lost.
"""

import frontmatter
from django.core.management.base import BaseCommand
from django.db.models import Q

from mdn.converter import Converter
from mdn.management.commands.import_mdn import FILES_DIR
from mdn.models import DocPage


BATCH = 500


class Command(BaseCommand):
    help = "Fill DocPage.body from MDN's markdown."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="", help="Only this section, e.g. web/css.")

    def handle(self, *args, prefix, **options):
        prefix = prefix.strip("/").lower()

        # Every English MDN path, imported or not: macros only link to pages
        # that exist on MDN.
        english_paths = {
            index.parent.relative_to(FILES_DIR).as_posix()
            for index in FILES_DIR.rglob("index.md")
        }
        # MDN path -> page id, for the links between pages of this site.
        page_ids = dict(DocPage.objects.exclude(mdn_path=None).values_list("mdn_path", "id"))
        converter = Converter(english_paths, page_ids.get)

        pages = DocPage.objects.exclude(mdn_path=None).only("id", "mdn_path")
        if prefix:
            pages = pages.filter(Q(mdn_path=prefix) | Q(mdn_path__startswith=prefix + "/"))

        batch, filled, missing = [], 0, 0
        for page in pages.iterator():
            index = FILES_DIR / page.mdn_path / "index.md"
            if not index.exists():
                missing += 1
                continue
            page.body = converter.convert(frontmatter.load(index).content)
            batch.append(page)
            if len(batch) >= BATCH:
                DocPage.objects.bulk_update(batch, ["body"])
                filled += len(batch)
                batch = []
                self.stdout.write(f"  {filled}")
        if batch:
            DocPage.objects.bulk_update(batch, ["body"])
            filled += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f"Filled {filled} pages, {missing} without their MDN file, "
            f"{converter.dropped_comments} HTML comments dropped"
        ))
