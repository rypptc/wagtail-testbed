"""Download MDN's content (mdn/content) into data/content.

By default it downloads the pinned commit, so every build gets the same site.
With --latest it downloads the current state of MDN's main branch. Only that
one commit is downloaded, not the repository's history.
"""

import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand


REPOSITORY = "https://github.com/mdn/content.git"
PINNED_COMMIT = "c37d4a5c0a0e464242d54ee7378d8adb2c9c5a4f"


class Command(BaseCommand):
    help = "Download MDN's content into data/content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Download MDN's latest content instead of the pinned commit.",
        )

    def handle(self, *args, latest, **options):
        target = settings.BASE_DIR / "data" / "content"
        ref = "main" if latest else PINNED_COMMIT

        # First run: an empty repository that points at MDN.
        if not (target / ".git").exists():
            target.mkdir(parents=True, exist_ok=True)
            git(target, "init", "--quiet")
            git(target, "remote", "add", "origin", REPOSITORY)

        self.stdout.write(f"Downloading mdn/content at {ref}...")
        git(target, "fetch", "--depth", "1", "origin", ref)
        git(target, "checkout", "--quiet", "--detach", "FETCH_HEAD")

        commit = git(target, "rev-parse", "HEAD", capture=True)
        self.stdout.write(self.style.SUCCESS(f"mdn/content is at {commit}"))


def git(directory, *args, capture=False):
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else None
