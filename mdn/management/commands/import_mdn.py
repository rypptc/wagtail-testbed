"""Load MDN's English pages into Wagtail as a page tree.

Each index.md under data/content/files/en-us becomes a DocPage under the page
of its parent folder, with the metadata in its header (see
docs/content-model.md). Bodies are filled afterwards by another command.
"""

import frontmatter
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from wagtail.models import Site

from mdn.models import DocPage, PageType, SpecURL, Status


FILES_DIR = settings.BASE_DIR / "data" / "content" / "files" / "en-us"


def as_list(value, where):
    """A header value as a list: absent -> [], "x" -> ["x"], a list of strings
    as it is. Anything else is a header we do not understand."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise CommandError(f"{where}: unexpected header value {value!r}")


def read_header(index, errors):
    try:
        return dict(frontmatter.load(index).metadata)
    except Exception as error:
        errors.append(f"{index.relative_to(FILES_DIR)}: {error}")
        return {}


def read_tree(prefix, errors):
    """{path: header} for every document under `prefix`, plus the prefix's
    ancestors, so the section hangs from the home page as it does on MDN.

    A path is the folder relative to en-us, e.g. "web/javascript/reference".
    "title" is always set.
    """
    tree = {}
    for index in FILES_DIR.rglob("index.md"):
        path = index.parent.relative_to(FILES_DIR).as_posix()
        if prefix and not (path == prefix or path.startswith(prefix + "/")):
            continue
        header = read_header(index, errors)
        header["title"] = str(header.get("title") or "").strip() or path.rsplit("/", 1)[-1]
        tree[path] = header

    if prefix:
        parts = prefix.split("/")
        for depth in range(1, len(parts)):
            ancestor = "/".join(parts[:depth])
            if ancestor not in tree:
                index = FILES_DIR / ancestor / "index.md"
                header = read_header(index, errors) if index.exists() else {}
                header["title"] = str(header.get("title") or ancestor)
                tree[ancestor] = header
    return tree


def by_depth(paths):
    """Parents before children."""
    return sorted(paths, key=lambda path: (path.count("/"), path))


def parent_of(path):
    return path.rsplit("/", 1)[0] if "/" in path else None


class Command(BaseCommand):
    help = "Load MDN's English pages into the site, as a page tree."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            default="",
            help="Only load this section, e.g. web/css. Default: all of MDN.",
        )

    def handle(self, *args, prefix, **options):
        prefix = prefix.strip("/").lower()
        if not FILES_DIR.exists():
            raise CommandError("No MDN content found. Run fetch_mdn first.")
        if DocPage.objects.exists():
            raise CommandError("The site already holds MDN pages. Import into a fresh database.")

        errors = []
        documents = read_tree(prefix, errors)
        self.stdout.write(f"{len(documents)} documents")

        # Rows shared by many pages, created once.
        page_types = {
            name: PageType.objects.create(name=name)
            for name in sorted(
                {str(header["page-type"]) for header in documents.values() if header.get("page-type")}
            )
        }
        statuses = {
            name: Status.objects.create(name=name)
            for name in sorted(
                {
                    status
                    for path, header in documents.items()
                    for status in as_list(header.get("status"), path)
                }
            )
        }

        # MDN's top sections hang from the site's home page.
        home = Site.objects.get(is_default_site=True).root_page
        pages = {}
        used_slugs = {}
        for count, path in enumerate(by_depth(documents), 1):
            parent_path = parent_of(path)
            parent = home if parent_path is None else pages[parent_path]

            # Two folders can give the same slug ("1.5" and "15" both give "15").
            base = slugify(path.rsplit("/", 1)[-1], allow_unicode=True) or "page"
            siblings = used_slugs.setdefault(parent_path, set())
            slug, n = base, 1
            while slug in siblings:
                n += 1
                slug = f"{base}-{n}"
            siblings.add(slug)

            header = documents[path]
            page = DocPage(
                title=header["title"],
                slug=slug,
                locale=home.locale,
                short_title=str(header.get("short-title") or ""),
                page_type=page_types.get(header.get("page-type")),
                browser_compat=as_list(header.get("browser-compat"), path),
            )
            # Saved by add_child: modelcluster saves the page, then these.
            page.status = [statuses[name] for name in as_list(header.get("status"), path)]
            # Assigning the list does not number the children.
            page.spec_urls = [
                SpecURL(url=url, sort_order=i)
                for i, url in enumerate(as_list(header.get("spec-urls"), path))
            ]
            pages[path] = parent.add_child(instance=page)
            if count % 1000 == 0:
                self.stdout.write(f"  {count}/{len(documents)}")

        for error in errors:
            self.stderr.write(f"Header not read: {error}")
        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(documents)} pages, {len(page_types)} page types, "
            f"{len(statuses)} statuses"
        ))
