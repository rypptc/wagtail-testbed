"""Download MDN's content into data/: mdn/content, and with --translations
mdn/translated-content too.

By default it downloads the pinned commits, so every build gets the same site.
With --latest it downloads the current state of each repository's main branch.
Only that one commit is downloaded, not the repository's history.
"""

import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand


# Folder in data/ -> (repository, pinned commit).
REPOSITORIES = {
    "content": (
        "https://github.com/mdn/content.git",
        "c37d4a5c0a0e464242d54ee7378d8adb2c9c5a4f",
    ),
    "translated-content": (
        "https://github.com/mdn/translated-content.git",
        "4a9a14f88e353f89deb5130c3a0efd3c6ba1befd",
    ),
}


class Command(BaseCommand):
    help = "Download MDN's content into data/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--latest",
            action="store_true",
            help="Download MDN's latest content instead of the pinned commits.",
        )
        parser.add_argument(
            "--translations",
            action="store_true",
            help="Also download mdn/translated-content.",
        )

    def handle(self, *args, latest, translations, **options):
        folders = ["content", "translated-content"] if translations else ["content"]
        for folder in folders:
            repository, pinned = REPOSITORIES[folder]
            self.fetch(settings.BASE_DIR / "data" / folder, repository, "main" if latest else pinned)

    def fetch(self, target, repository, ref):
        # Already at the pinned commit: nothing to download.
        if (target / ".git").exists() and git(target, "rev-parse", "HEAD", capture=True) == ref:
            self.stdout.write(f"{target.name} is already at {ref}")
            return

        # First run: an empty repository that points at MDN.
        if not (target / ".git").exists():
            target.mkdir(parents=True, exist_ok=True)
            git(target, "init", "--quiet")
            git(target, "remote", "add", "origin", repository)

        self.stdout.write(f"Downloading {repository} at {ref}...")
        git(target, "fetch", "--depth", "1", "origin", ref)
        git(target, "checkout", "--quiet", "--detach", "FETCH_HEAD")

        commit = git(target, "rev-parse", "HEAD", capture=True)
        self.stdout.write(self.style.SUCCESS(f"{target.name} is at {commit}"))


def git(directory, *args, capture=False):
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else None
