"""Create MDN's translations of the English pages, the way a translator using
wagtail-localize would: page.copy_for_translation(locale, copy_parents=True),
then the translation gets its own MDN title and short title.

Run it after import_mdn, with mdn/translated-content downloaded
(fetch_mdn --translations). Bodies are filled afterwards by fill_bodies.

A translation whose parent is not translated hangs from an alias that Wagtail
creates for the parent, so every locale has a complete tree.
"""

import frontmatter
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Locale, Page

from mdn.management.commands.import_mdn import by_depth
from mdn.models import DocPage


TRANSLATIONS_DIR = settings.BASE_DIR / "data" / "translated-content" / "files"
LOCALES = ["es", "fr", "ja", "ko", "pt-br", "ru", "zh-cn", "zh-tw"]


class Command(BaseCommand):
    help = "Create MDN's translations of the English pages."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="", help="Only this section, e.g. web/css.")
        parser.add_argument(
            "--locale", action="append", choices=LOCALES,
            help="Only this locale (repeatable). Default: all of them.",
        )

    def handle(self, *args, prefix, locale, **options):
        prefix = prefix.strip("/").lower()
        if not TRANSLATIONS_DIR.exists():
            raise CommandError("No MDN translations found. Run fetch_mdn --translations first.")

        # MDN path -> English page id.
        english = dict(
            DocPage.objects.filter(locale__language_code="en")
            .exclude(mdn_path=None)
            .values_list("mdn_path", "id")
        )
        if not english:
            raise CommandError("No English MDN pages. Run import_mdn first.")

        for code in locale or LOCALES:
            target = Locale.objects.get_or_create(language_code=code)[0]
            if DocPage.objects.filter(locale=target, alias_of__isnull=True).exists():
                raise CommandError(f"{code} already has translations. Import into a fresh database.")

            # MDN path -> header, for the documents of this locale.
            documents, errors = {}, []
            root = TRANSLATIONS_DIR / code
            for index in root.rglob("index.md"):
                path = index.parent.relative_to(root).as_posix()
                if prefix and not (path == prefix or path.startswith(prefix + "/")):
                    continue
                try:
                    documents[path] = frontmatter.load(index).metadata
                except Exception as error:
                    errors.append(f"{code}/{path}: {error}")

            # Only documents with an English page; parents first.
            pairs = by_depth(set(documents) & set(english))
            for count, path in enumerate(pairs, 1):
                source = DocPage.objects.get(id=english[path])
                translation = source.copy_for_translation(target, copy_parents=True)
                header = documents[path]
                translation.title = str(header.get("title") or "").strip() or translation.title
                translation.draft_title = translation.title
                # Keep the English short title unless this locale's header has one.
                if "short-title" in header:
                    translation.short_title = str(header["short-title"] or "")
                translation.save(update_fields=["title", "draft_title", "short_title"])
                if count % 1000 == 0:
                    self.stdout.write(f"  {code} {count}/{len(pairs)}")

            # copy_for_translation leaves each translation as a draft. On a real
            # site they would be published, so publish them all at once.
            published = (
                Page.objects.filter(locale=target, alias_of__isnull=True, depth__gt=2)
                .update(live=True, has_unpublished_changes=False)
            )
            aliases = Page.objects.filter(locale=target, alias_of__isnull=False).count()

            for error in errors:
                self.stderr.write(f"Header not read: {error}")
            self.stdout.write(self.style.SUCCESS(
                f"{code}: {published} translations, {aliases} aliases, "
                f"{len(set(documents) - set(english))} documents without an English page"
            ))
