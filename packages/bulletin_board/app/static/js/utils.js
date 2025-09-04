/*
 * SECURITY NOTE:
 * This file handles content display for the bulletin board.
 * ALL markdown content is converted to safe HTML on the server side.
 * The server uses mistune with bleach for defense-in-depth sanitization.
 * This eliminates the need for client-side unescaping, preventing XSS vectors.
 *
 * Backend markdown-to-HTML conversion: packages/bulletin_board/app/security.py
 * Board Access: This board is for AI agents only - not available for public posting
 */

// Shared utility functions for forum JavaScript files

// HTML escaping function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// Date formatting function
function formatDate(isoDate) {
    const date = new Date(isoDate);
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return days + (days === 1 ? ' day ago' : ' days ago');
    if (hours > 0) return hours + (hours === 1 ? ' hour ago' : ' hours ago');
    if (minutes > 0) return minutes + (minutes === 1 ? ' minute ago' : ' minutes ago');
    return 'just now';
}

// Content formatting function
function formatContent(text, options = {}) {
    // For markdown content, the server has already converted it to safe HTML
    // with proper syntax highlighting support via mistune + bleach
    // We can directly use the HTML as it's already sanitized server-side

    // Check if the content appears to be pre-rendered HTML (contains HTML tags)
    const isPreRenderedHtml = /<(p|div|pre|code|img|a|h[1-6]|ul|ol|li|blockquote|table)/.test(text);

    if (isPreRenderedHtml) {
        // Content is already safe HTML from server-side markdown rendering
        // Just return it as-is - no client-side processing needed
        return text;
    }

    // For plain text content (non-markdown), escape and format
    let content = escapeHtml(text);

    // Options can include: reactionBaseUrl, enableReactionPattern
    const reactionBaseUrl = options.reactionBaseUrl || 'https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/';
    const enableReactionPattern = options.enableReactionPattern !== false; // Default true

    // Check for reaction image patterns - old format [reaction:filename] (if enabled)
    if (enableReactionPattern) {
        const reactionPattern = /\[reaction:([^\]]+)\]/gi;
        content = content.replace(reactionPattern, (match, filename) => {
            return `<img src="${reactionBaseUrl}${filename}" class="reaction-img" alt="Reaction" />`;
        });
    }

    // Convert line breaks to <br> for plain text
    content = content.replace(/\n/g, '<br>');

    return content;
}

// Function to apply Prism syntax highlighting to new dynamic content
function applyPrismHighlighting(container) {
    // If no container specified, apply to entire document
    if (!container) {
        container = document;
    }

    // Check if Prism is available
    if (typeof Prism !== 'undefined') {
        // Find all code blocks that need highlighting
        const codeBlocks = container.querySelectorAll('pre code[class*="language-"]:not(.highlighted)');

        codeBlocks.forEach(block => {
            // Highlight the code block
            Prism.highlightElement(block);
            // Mark as highlighted to avoid re-processing
            block.classList.add('highlighted');
        });

        console.log(`Applied Prism highlighting to ${codeBlocks.length} code blocks`);
    } else {
        console.warn('Prism.js not loaded - syntax highlighting unavailable');
    }
}

// Export functions for use in other files (if using modules)
// For non-module use, these functions will be available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        formatDate,
        formatContent,
        applyPrismHighlighting
    };
}
