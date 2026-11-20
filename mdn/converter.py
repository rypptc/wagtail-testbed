"""Convert one MDN markdown document into DocPage body blocks.

The result is the raw StreamField data (a list of {"type", "value", "id"}),
ready to store. What each MDN element becomes:

- "## Heading"               -> heading
- paragraphs and lists       -> paragraph (rich text; consecutive ones merged)
- fenced code                -> code
- "> [!NOTE]" and friends    -> callout
- markdown tables            -> table
- raw HTML blocks            -> raw_html
- HTML comments              -> dropped (counted); they are notes for MDN's tools
- link macros ({{jsxref}}…)  -> links to the page they name, when it exists
- every other macro          -> dropped

Links to other MDN documents become Wagtail page links (linktype="page"), so
the site has real internal links between pages.
"""

import html
import re
import uuid

from markdown_it import MarkdownIt

from mdn.models import CODE_LANGUAGES


md = MarkdownIt("commonmark").enable("table")

LANGUAGE_ALIASES = {"javascript": "js", "plaintext": "plain", "text": "plain", "shell": "sh"}

# Macro name -> (candidate MDN paths, display as code?). "{0}" is the first
# argument. The first candidate that exists in English wins.
XREF = {
    "jsxref": (
        ["web/javascript/reference/global_objects/{0}", "web/javascript/reference/{0}"],
        True,
    ),
    "domxref": (["web/api/{0}"], True),
    "cssxref": (
        [
            "web/css/reference/properties/{0}",
            "web/css/reference/values/{0}",
            "web/css/reference/selectors/{0}",
            "web/css/reference/at-rules/{0}",
            "web/css/{0}",
        ],
        True,
    ),
    "htmlelement": (["web/html/reference/elements/{0}"], True),
    "svgelement": (["web/svg/reference/element/{0}"], True),
    "svgattr": (["web/svg/reference/attribute/{0}"], True),
    "httpheader": (["web/http/reference/headers/{0}"], True),
    "httpmethod": (["web/http/reference/methods/{0}"], True),
    "httpstatus": (["web/http/reference/status/{0}"], True),
    "webextapiref": (["mozilla/add-ons/webextensions/api/{0}"], True),
    "glossary": (["glossary/{0}"], False),
}

MACRO = re.compile(r"\{\{\s*([\w-]+)\s*(?:\((.*?)\))?\s*\}\}", re.S)
ARG = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'')
CALLOUT = re.compile(r"^\s*(?:\[!(NOTE|WARNING|CALLOUT)\]|\*\*(Note|Warning|Callout):\*\*)\s*", re.I)
DOC_HREF = re.compile(r'href="/([\w-]+)/docs/([^"#?]*)[^"]*"')
ALLOWED_TAGS = {"p", "b", "i", "code", "a", "ul", "ol", "li", "br"}
TAG = re.compile(r"</?([a-zA-Z0-9]+)\b[^>]*>")


def new_id():
    return str(uuid.uuid4())


def item(value):
    return {"type": "item", "value": value, "id": new_id()}


class Converter:
    """`english_paths` is the set of English MDN paths ("web/api/element"),
    used to decide where a macro points. `resolve(path)` returns the page id to
    link to for an MDN path, or None."""

    def __init__(self, english_paths, resolve):
        self.english_paths = english_paths
        self.resolve = resolve
        self.dropped_comments = 0

    # Macros -------------------------------------------------------------

    def expand_macros(self, text):
        def replace(match):
            name = match.group(1).lower()
            if name not in XREF:
                return ""
            args = [a if a is not None else b for a, b in ARG.findall(match.group(2) or "")]
            if not args:
                return ""
            target = args[0]
            label = args[1] if len(args) > 1 and args[1] else target
            candidates, as_code = XREF[name]
            if name == "jsxref":
                target = target.replace("()", "").replace(".prototype.", "/").replace(".", "/")
            if name == "domxref" or name == "webextapiref":
                target = target.replace("()", "").replace(".", "/")
            if name == "glossary":
                target = target.replace(" ", "_")
            if name in ("htmlelement", "svgelement"):
                label = f"<{label}>" if len(args) < 2 else label
            path = None
            for candidate in candidates:
                guess = candidate.format(target).lower().strip("/")
                if guess in self.english_paths:
                    path = guess
                    break
            text = f"`{label}`" if as_code else label
            return f"[{text}](/en-US/docs/{path})" if path else text

        return MACRO.sub(replace, text)

    # Rich text ------------------------------------------------------------

    def clean_html(self, rendered):
        rendered = rendered.replace("<strong>", "<b>").replace("</strong>", "</b>")
        rendered = rendered.replace("<em>", "<i>").replace("</em>", "</i>")

        def link(match):
            page_id = self.resolve(match.group(2).lower().strip("/"))
            if page_id is None:
                return f'href="https://developer.mozilla.org/{match.group(1)}/docs/{match.group(2)}"'
            return f'linktype="page" id="{page_id}"'

        rendered = DOC_HREF.sub(link, rendered)
        rendered = TAG.sub(
            lambda m: m.group(0) if m.group(1).lower() in ALLOWED_TAGS else "", rendered
        )
        # Lists: no paragraphs inside items, and MDN's definition lists
        # ("- term" / "  - : definition") lose their ": " marker.
        rendered = re.sub(r"<li>\s*<p>", "<li>", rendered)
        rendered = re.sub(r"</p>\s*</li>", "</li>", rendered)
        rendered = re.sub(r"</p>\s*<(ul|ol)>", r"<\1>", rendered)
        rendered = re.sub(r"<li>\s*:\s*", "<li>", rendered)
        return rendered.strip()

    def inline_html(self, token):
        return self.clean_html(md.renderer.renderInline(token.children, md.options, {}))

    # Blocks -----------------------------------------------------------

    def convert(self, markdown):
        tokens = md.parse(self.expand_macros(markdown))
        blocks = []
        rich = []

        def flush():
            text = "".join(rich).strip()
            if text:
                blocks.append({"type": "paragraph", "value": text, "id": new_id()})
            rich.clear()

        i = 0
        while i < len(tokens):
            token = tokens[i]
            end = self.closing(tokens, i)

            if token.type == "heading_open":
                flush()
                level = min(max(int(token.tag[1]), 2), 4)
                text = "".join(
                    child.content for child in tokens[i + 1].children
                    if child.type in ("text", "code_inline")
                ).strip()
                if text:
                    blocks.append({
                        "type": "heading",
                        "value": {"level": str(level), "text": text},
                        "id": new_id(),
                    })
            elif token.type in ("paragraph_open", "bullet_list_open", "ordered_list_open"):
                html_ = self.clean_html(md.renderer.render(tokens[i:end + 1], md.options, {}))
                if TAG.sub("", html_).strip():
                    rich.append(html_)
            elif token.type in ("fence", "code_block"):
                flush()
                blocks.append({
                    "type": "code",
                    "value": {"language": self.language(token.info), "code": token.content.rstrip("\n")},
                    "id": new_id(),
                })
            elif token.type == "blockquote_open":
                flush()
                blocks.append(self.callout(tokens[i + 1:end]))
            elif token.type == "table_open":
                flush()
                blocks.append(self.table(tokens[i:end + 1]))
            elif token.type == "html_block":
                if token.content.lstrip().startswith("<!--"):
                    self.dropped_comments += 1
                else:
                    flush()
                    blocks.append({"type": "raw_html", "value": token.content.strip(), "id": new_id()})
            i = end + 1

        flush()
        return blocks

    @staticmethod
    def closing(tokens, start):
        """Index of the token that closes tokens[start] (itself if it is not
        an opening token)."""
        if tokens[start].nesting != 1:
            return start
        depth = 0
        for j in range(start, len(tokens)):
            depth += tokens[j].nesting
            if depth == 0:
                return j
        return len(tokens) - 1

    @staticmethod
    def language(info):
        word = (info.split() or ["plain"])[0].lower().removesuffix("-nolint")
        word = LANGUAGE_ALIASES.get(word, word)
        return word if word in dict(CODE_LANGUAGES) else "plain"

    def callout(self, inner):
        rendered = self.clean_html(md.renderer.render(inner, md.options, {}))
        kind = "callout"
        plain_start = re.sub(r"^(<p>)", "", rendered)
        match = CALLOUT.match(plain_start)
        if match:
            kind = (match.group(1) or match.group(2)).lower()
            rendered = "<p>" + plain_start[match.end():] if rendered.startswith("<p>") else plain_start[match.end():]
            rendered = rendered.replace("<p></p>", "", 1)
        return {"type": "callout", "value": {"kind": kind, "text": rendered.strip()}, "id": new_id()}

    def table(self, tokens):
        header, rows, row, in_head = [], [], None, False
        for token in tokens:
            if token.type == "thead_open":
                in_head = True
            elif token.type == "thead_close":
                in_head = False
            elif token.type == "tr_open":
                row = []
            elif token.type == "inline" and row is not None:
                row.append(item(self.inline_html(token)))
            elif token.type == "tr_close":
                if in_head:
                    header = row
                else:
                    rows.append(item(row))
                row = None
        return {"type": "table", "value": {"header": header, "rows": rows}, "id": new_id()}


def plain_text(value):
    return html.unescape(TAG.sub("", value))
