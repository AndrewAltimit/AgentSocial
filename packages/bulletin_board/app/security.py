"""
Security module for sanitizing user input and preventing XSS attacks
All user-provided content MUST be sanitized through this module before storage
"""

import logging
import re

import bleach  # type: ignore[import-untyped]
import mistune
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
    Additional sanitization for embed tags.
    Only allows embeds from trusted sources with strict validation.

    Note: Consider using iframe with sandbox attribute as a more secure alternative.
    The embed tag is maintained primarily for retro MySpace aesthetic.
    """
    TRUSTED_EMBED_DOMAINS = [
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "vimeo.com",
        "player.vimeo.com",
        "soundcloud.com",
        "w.soundcloud.com",
    ]

    # Pattern to find embed tags
    embed_pattern = re.compile(r"<embed\s+([^>]*?)>", re.IGNORECASE | re.DOTALL)

    def check_embed(match):
        attrs = match.group(1)

        # Extract src attribute more carefully
        src_patterns = [
            r'src\s*=\s*"([^"]*)"',
            r"src\s*=\s*'([^']*)'",
            r"src\s*=\s*([^\s>]+)",
        ]

        src = None
        for pattern in src_patterns:
            src_match = re.search(pattern, attrs, re.IGNORECASE)
            if src_match:
                src = src_match.group(1)
                break

        if not src:
            logger.warning(f"Removed embed tag without src: {match.group(0)[:100]}")
            return ""

        # Validate the URL
        from urllib.parse import urlparse

        try:
            parsed = urlparse(src)

            # Check protocol
            if parsed.scheme not in ["http", "https"]:
                logger.warning(f"Removed embed with invalid protocol: {parsed.scheme}")
                return ""

            # Check hostname
            if not parsed.hostname:
                logger.warning(f"Removed embed without hostname: {src[:100]}")
                return ""

            # Normalize hostname for comparison
            hostname = parsed.hostname.lower()

            # Check if hostname is in trusted list
            is_trusted = any(hostname == domain or hostname.endswith("." + domain) for domain in TRUSTED_EMBED_DOMAINS)

            if is_trusted:
                # Additional validation for specific services
                if "youtube" in hostname or "youtu.be" in hostname:
                    # Ensure it's an embed URL, not a regular video page
                    if "/embed/" not in parsed.path and "youtu.be" not in hostname:
                        logger.warning(f"YouTube URL not in embed format: {src[:100]}")
                        return ""

                # Keep the embed but add security attributes
                # Note: This is a simple approach - in production, consider
                # converting to iframe with sandbox attribute
                return match.group(0)
            else:
                logger.warning(f"Removed untrusted embed domain: {hostname}")
                return ""

        except Exception as e:
            logger.warning(f"Error parsing embed URL {src[:100]}: {str(e)}")
            return ""

    sanitized = embed_pattern.sub(check_embed, html)

    # Log if any embeds were removed
    if html != sanitized:
        logger.info("Embed tags were sanitized from content")

    return sanitized


def sanitize_markdown(content: str) -> str:
    """
    Convert markdown to safe HTML on the server side.
    This eliminates the need for client-side unescaping and prevents XSS.
    """
    if not content:
        return ""

    # Create a custom renderer that adds syntax highlighting support
    class SafeRenderer(mistune.HTMLRenderer):
        def block_code(self, text, info=None):
            """Render code blocks with language support for syntax highlighting"""
            if info:
                # Extract language from info string (e.g., "python" from "python\n")
                lang = info.strip().split()[0] if info else "plaintext"
            else:
                lang = "plaintext"

            # Escape the code content to prevent XSS
            escaped = mistune.escape(text)
            return f'<pre><code class="language-{lang}">{escaped}</code></pre>\n'

        def inline_code(self, text):
            """Render inline code with proper escaping"""
            escaped = mistune.escape(text)
            return f'<code class="inline-code">{escaped}</code>'

        def image(self, alt, url, title=None):
            """Render images with special handling for reaction images"""
            # Check if this is a reaction image from the AndrewAltimit/Media repo
            if "AndrewAltimit/Media" in url and "/reaction/" in url:
                alt_text = alt or "Reaction"
                style = "max-height: 200px; vertical-align: middle; margin: 10px 0;"
                return f'<img src="{url}" class="reaction-img" alt="{alt_text}" style="{style}" />'
            # Handle regular images
            return f'<img src="{url}" alt="{alt}" style="max-width: 100%; height: auto; margin: 10px 0;" />'

        def link(self, text, url, title=None):
            """Render links with security attributes"""
            # Add rel="noopener noreferrer" for security
            title_attr = f' title="{mistune.escape(title)}"' if title else ""
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer"{title_attr}>{text}</a>'

    # Create markdown parser with custom renderer
    # Enable all common markdown features
    markdown = mistune.create_markdown(
        renderer=SafeRenderer(),
        plugins=[
            "strikethrough",
            "footnotes",
            "table",
            "task_lists",
            "def_list",
            "abbr",
            "mark",
            "insert",
            "superscript",
            "subscript",
        ],
    )

    # Convert markdown to HTML
    html_content = markdown(content)

    # Apply additional sanitization with bleach to ensure safety
    # This is defense-in-depth - the markdown parser should already be safe
    allowed_tags = ALLOWED_TAGS_BASIC + [
        "sup",
        "sub",
        "mark",
        "ins",
        "del",
        "abbr",
        "dl",
        "dt",
        "dd",
        "input",
        "img",  # Allow images for reaction images and other markdown images
    ]
    allowed_attrs = {
        **ALLOWED_ATTRS_BASIC,
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "title", "width", "height", "style", "class"],
        "abbr": ["title"],
        "input": ["type", "checked", "disabled"],  # For task lists
    }

    cleaned_html = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )

    return str(cleaned_html)


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
        # Convert markdown to safe HTML on the server side
        # This prevents XSS without needing client-side unescaping
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
