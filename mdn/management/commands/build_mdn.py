"""Build the site's MDN content in one go: download MDN, load the page tree,
fill the bodies. With --translations, also MDN's translations, created the way
wagtail-localize creates them. Run it on a freshly migrated database."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Download MDN and load it into the site: fetch_mdn, import_mdn, "
        "import_translations (with --translations), fill_bodies."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Use MDN's latest content instead of the pinned commits.",
        )
        parser.add_argument(
            "--prefix",
            default="",
            help="Only load this section, e.g. web/css. Default: all of MDN.",
        )
        parser.add_argument(
            "--translations",
            action="store_true",
            help="Also load MDN's translations, with wagtail-localize.",
        )

    def handle(self, *args, latest, prefix, translations, **options):
        call_command("fetch_mdn", latest=latest, translations=translations)
        call_command("import_mdn", prefix=prefix)
        if translations:
            call_command("import_translations", prefix=prefix)
        call_command("fill_bodies", prefix=prefix)
