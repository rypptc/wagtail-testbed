from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Orderable, Page


# Rich text features: INLINE inside table cells, RICH everywhere else.
# Wagtail's feature names, under "Limiting features in a rich text field":
# https://docs.wagtail.org/en/stable/advanced_topics/customization/page_editing_interface.html
INLINE = ["bold", "italic", "code", "link"]
RICH = [*INLINE, "ol", "ul"]

# Languages MDN uses in its code blocks. Anything else is imported as "plain".
# MDN's list of accepted languages:
# https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Howto/Markdown_in_MDN#example_code_blocks
CODE_LANGUAGES = [
    (code, code)
    for code in [
        "plain", "js", "ts", "json", "html", "css", "svg", "xml", "http",
        "bash", "sh", "python", "wasm", "wat", "webidl", "sql", "md", "diff",
        "regex", "jsx", "yaml", "glsl", "apacheconf",
    ]
]


class HeadingBlock(blocks.StructBlock):
    level = blocks.ChoiceBlock(choices=[("2", "H2"), ("3", "H3"), ("4", "H4")])
    text = blocks.CharBlock()


class CodeBlock(blocks.StructBlock):
    # A choice, not free text: the language is a setting, not content.
    language = blocks.ChoiceBlock(choices=CODE_LANGUAGES, default="plain")
    code = blocks.TextBlock()


class CalloutBlock(blocks.StructBlock):
    """MDN's note, warning and callout boxes."""

    kind = blocks.ChoiceBlock(
        choices=[("note", "Note"), ("warning", "Warning"), ("callout", "Callout")]
    )
    text = blocks.RichTextBlock(features=RICH)


class TableBlock(blocks.StructBlock):
    # Not wagtail.contrib.table_block: here every cell is rich text, so links
    # and code inside cells are kept.
    header = blocks.ListBlock(blocks.RichTextBlock(features=INLINE))
    rows = blocks.ListBlock(blocks.ListBlock(blocks.RichTextBlock(features=INLINE)))


class PageType(models.Model):
    """MDN's page-type, e.g. "css-property". One row per type, shared by
    every page of that type."""

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Status(models.Model):
    """experimental, deprecated or non-standard. A page can have several."""

    name = models.CharField(max_length=30, unique=True)

    class Meta:
        verbose_name_plural = "statuses"

    def __str__(self):
        return self.name


class DocPage(Page):
    """One MDN document: its title, the metadata in its header and its body
    as blocks."""

    # The MDN folder this page comes from, e.g. "web/css/reference/properties/color".
    # Empty for pages created in the admin. Not unique: a translation has the
    # same path as its English page, in another locale.
    mdn_path = models.CharField(max_length=255, null=True, editable=False, db_index=True)
    short_title = models.CharField(max_length=255, blank=True)
    page_type = models.ForeignKey(
        PageType, null=True, blank=True, on_delete=models.PROTECT, related_name="pages"
    )
    status = ParentalManyToManyField(Status, blank=True, related_name="pages")
    browser_compat = ArrayField(
        models.CharField(max_length=255), default=list, blank=True
    )

    body = StreamField(
        [
            ("heading", HeadingBlock()),
            ("paragraph", blocks.RichTextBlock(features=RICH)),
            ("code", CodeBlock()),
            ("callout", CalloutBlock()),
            ("table", TableBlock()),
            ("raw_html", blocks.RawHTMLBlock()),
        ],
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("short_title"),
        MultiFieldPanel(
            [
                FieldPanel("page_type"),
                FieldPanel("status", widget=forms.CheckboxSelectMultiple),
                FieldPanel("browser_compat"),
                InlinePanel("spec_urls", label="Spec URLs"),
            ],
            heading="MDN metadata",
        ),
        FieldPanel("body"),
    ]


class SpecURL(Orderable):
    """One of the specifications a document cites, in MDN's order."""

    page = ParentalKey(DocPage, on_delete=models.CASCADE, related_name="spec_urls")
    url = models.URLField(max_length=500)

    panels = [FieldPanel("url")]
