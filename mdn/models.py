from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


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


class DocPage(Page):
    """One MDN document: its title and its body as blocks."""

    body = StreamField(
        [
            ("heading", HeadingBlock()),
            ("paragraph", blocks.RichTextBlock(features=RICH)),
            ("code", CodeBlock()),
            ("callout", CalloutBlock()),
            ("table", TableBlock()),
        ],
        blank=True,
    )

    content_panels = Page.content_panels + [FieldPanel("body")]
