"""Build the site's MDN content in one go: download MDN, load the page tree,
fill the bodies. Run it on a freshly migrated database."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Download MDN and load it into the site: fetch_mdn, import_mdn, fill_bodies."

    def add_arguments(self, parser):
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Use MDN's latest content instead of the pinned commit.",
        )
        parser.add_argument(
            "--prefix",
            default="",
            help="Only load this section, e.g. web/css. Default: all of MDN.",
        )

    def handle(self, *args, latest, prefix, **options):
        call_command("fetch_mdn", latest=latest)
        call_command("import_mdn", prefix=prefix)
        call_command("fill_bodies", prefix=prefix)
