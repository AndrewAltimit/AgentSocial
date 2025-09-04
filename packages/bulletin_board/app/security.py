"""
Security module for sanitizing user input and preventing XSS attacks
All user-provided content MUST be sanitized through this module before storage
"""

import logging
import re

import bleach
from markupsafe import Markup

logger = logging.getLogger(__name__)

# Define allowed HTML tags for different contexts
ALLOWED_TAGS_BASIC = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "span",
    "div",
]

ALLOWED_TAGS_MYSPACE = ALLOWED_TAGS_BASIC + [
    "table",
    "tr",
    "td",
    "th",
    "tbody",
    "thead",
    "tfoot",
    "img",
    "font",
    "marquee",
    "blink",
    "center",
    "embed",
]

# Define allowed attributes for different contexts
ALLOWED_ATTRS_BASIC = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],  # For syntax highlighting
    "pre": ["class"],  # For syntax highlighting
    "span": ["class", "style"],  # Limited style support
    "div": ["class", "id", "style"],
}

ALLOWED_ATTRS_MYSPACE = {
    **ALLOWED_ATTRS_BASIC,
    "table": ["border", "cellpadding", "cellspacing", "width", "bgcolor"],
    "td": ["colspan", "rowspan", "bgcolor", "align", "valign", "width"],
    "th": ["colspan", "rowspan", "bgcolor", "align", "valign"],
    "tr": ["bgcolor", "align"],
    "font": ["size", "color", "face"],
    "marquee": ["behavior", "direction", "scrollamount"],
    "embed": ["src", "autostart", "hidden", "width", "height"],
}

# Define allowed protocols
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# CSS properties that are safe to allow
SAFE_CSS_PROPERTIES = [
    "color",
    "background-color",
    "font-family",
    "font-size",
    "font-weight",
    "text-align",
    "text-decoration",
    "margin",
    "padding",
    "border",
    "width",
    "height",
    "display",
    "float",
    "clear",
]


def sanitize_basic_html(content: str) -> str:
    """
    Sanitize basic HTML content (comments, posts, etc.)
    Removes all potentially dangerous elements while preserving basic formatting
    """
    if not content:
        return ""

    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS_BASIC,
        attributes=ALLOWED_ATTRS_BASIC,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )

    logger.debug(f"Sanitized basic HTML: {len(content)} -> {len(cleaned)} chars")
    return str(cleaned)


def sanitize_myspace_html(content: str) -> str:
    """
    Sanitize MySpace-style HTML content (profiles)
    Allows more tags for retro aesthetic but still prevents XSS
    """
    if not content:
        return ""

    cleaned = bleach.clean(
        content,
        tags=ALLOWED_TAGS_MYSPACE,
        attributes=ALLOWED_ATTRS_MYSPACE,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )

    # Additional sanitization for embed tags
    if "<embed" in cleaned:
        # Only allow specific trusted domains for embeds
        cleaned = sanitize_embed_tags(cleaned)

    logger.debug(f"Sanitized MySpace HTML: {len(content)} -> {len(cleaned)} chars")
    return str(cleaned)


def sanitize_embed_tags(html: str) -> str:
    """
    Additional sanitization for embed tags
    Only allows embeds from trusted sources
    """
    TRUSTED_EMBED_DOMAINS = [
        "youtube.com",
        "www.youtube.com",
        "vimeo.com",
        "player.vimeo.com",
        "soundcloud.com",
        "w.soundcloud.com",
    ]

    # Pattern to find embed tags
    embed_pattern = re.compile(r"<embed\s+([^>]*?)>", re.IGNORECASE)

    def check_embed(match):
        attrs = match.group(1)
        src_match = re.search(r'src=[\'"](.*?)[\'"]', attrs, re.IGNORECASE)

        if src_match:
            src = src_match.group(1)
            # Check if the source is from a trusted domain
            from urllib.parse import urlparse

            try:
                parsed = urlparse(src)
                if parsed.hostname and any(domain in parsed.hostname for domain in TRUSTED_EMBED_DOMAINS):
                    return match.group(0)  # Keep the embed
            except Exception:
                pass

        # Remove untrusted embed
        logger.warning(f"Removed untrusted embed tag: {match.group(0)[:100]}")
        return ""

    return embed_pattern.sub(check_embed, html)


def sanitize_markdown(content: str) -> str:
    """
    Sanitize markdown content before rendering
    Prevents injection of raw HTML in markdown
    """
    if not content:
        return ""

    # Remove any raw HTML tags from markdown
    # This is a simple approach - for production, consider using a markdown parser
    # that has built-in XSS protection
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"<iframe[^>]*>.*?</iframe>", "", content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)
    content = re.sub(r"on\w+\s*=", "", content, flags=re.IGNORECASE)  # Remove event handlers

    # Important: Don't escape markdown syntax like backticks
    # The content will be escaped when rendered, not during storage
    return content


def sanitize_json_data(data: dict) -> dict:
    """
    Sanitize JSON data (like profile interests, favorites, etc.)
    Ensures no XSS in JSON fields that will be displayed
    """
    if not data:
        return {}

    def clean_value(value):
        if isinstance(value, str):
            # Remove any HTML tags from strings in JSON
            return bleach.clean(value, tags=[], strip=True)
        elif isinstance(value, list):
            return [clean_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: clean_value(v) for k, v in value.items()}
        else:
            return value

    return dict(clean_value(data))


def sanitize_for_storage(content: str, content_type: str = "basic") -> str:
    """
    Main sanitization function that should be called before storing any user content

    Args:
        content: The content to sanitize
        content_type: Type of content - "basic", "myspace", "markdown", etc.

    Returns:
        Sanitized content safe for storage and rendering
    """
    if not content:
        return ""

    # Log the sanitization for security auditing
    logger.info(f"Sanitizing {content_type} content of length {len(content)}")

    if content_type == "myspace":
        return sanitize_myspace_html(content)
    elif content_type == "markdown":
        # First sanitize the markdown, then it can be converted to HTML later
        return sanitize_markdown(content)
    else:
        # Default to basic sanitization
        return sanitize_basic_html(content)


def create_safe_markup(content: str, already_sanitized: bool = False) -> Markup:
    """
    Create a Markup object for template rendering

    Args:
        content: The content to wrap
        already_sanitized: If True, content is assumed to be pre-sanitized

    Returns:
        Markup object safe for template rendering
    """
    if not already_sanitized:
        content = sanitize_basic_html(content)

    return Markup(content)


# Warning comment for client-side code
CLIENT_SIDE_WARNING = """
/*
 * SECURITY WARNING:
 * This file contains client-side HTML manipulation.
 * ALL user content MUST be sanitized on the backend before storage.
 * Client-side unescaping is ONLY safe because we enforce backend sanitization.
 * Never trust client-side sanitization alone - it can be bypassed.
 *
 * Backend sanitization is enforced in packages/bulletin_board/app/security.py
 */
"""
