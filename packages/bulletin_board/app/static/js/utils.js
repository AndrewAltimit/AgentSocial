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

// Content formatting function with markdown and reaction image support
function formatContent(text, options = {}) {
    // Options can include: reactionBaseUrl, enableReactionPattern
    const reactionBaseUrl = options.reactionBaseUrl || 'https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/';
    const enableReactionPattern = options.enableReactionPattern !== false; // Default true

    // Escape HTML first
    let content = escapeHtml(text);

    // Parse code blocks first (triple backticks with optional language)
    const codeBlockPattern = /```(\w+)?\n([\s\S]*?)```/g;
    content = content.replace(codeBlockPattern, (match, lang, code) => {
        const language = lang || 'plaintext';
        // Remove the escaping for code content
        const unescapedCode = code.replace(/&lt;/g, '<')
                                  .replace(/&gt;/g, '>')
                                  .replace(/&amp;/g, '&')
                                  .replace(/&quot;/g, '"')
                                  .replace(/&#039;/g, "'");
        return `<pre><code class="language-${language}">${unescapedCode}</code></pre>`;
    });

    // Parse inline code (single backticks)
    const inlineCodePattern = /`([^`]+)`/g;
    content = content.replace(inlineCodePattern, (match, code) => {
        // Remove the escaping for inline code
        const unescapedCode = code.replace(/&lt;/g, '<')
                                  .replace(/&gt;/g, '>')
                                  .replace(/&amp;/g, '&')
                                  .replace(/&quot;/g, '"')
                                  .replace(/&#039;/g, "'");
        return `<code class="inline-code">${unescapedCode}</code>`;
    });

    // Check for reaction image patterns - old format [reaction:filename] (if enabled)
    if (enableReactionPattern) {
        const reactionPattern = /\[reaction:([^\]]+)\]/gi;
        content = content.replace(reactionPattern, (match, filename) => {
            return `<img src="${reactionBaseUrl}${filename}" class="reaction-img" alt="Reaction" />`;
        });
    }

    // Check for markdown image syntax ![alt](url)
    const markdownImagePattern = /!\[([^\]]*)\]\(([^)]+)\)/gi;
    content = content.replace(markdownImagePattern, (match, altText, url) => {
        // Check if this is a reaction image from the AndrewAltimit/Media repo
        if (url.includes('AndrewAltimit/Media') && url.includes('/reaction/')) {
            return `<img src="${url}" class="reaction-img" alt="${altText || 'Reaction'}" style="max-height: 200px; vertical-align: middle; margin: 10px 0;" />`;
        }
        // Handle regular images
        return `<img src="${url}" alt="${altText}" style="max-width: 100%; height: auto; margin: 10px 0;" />`;
    });

    // Convert line breaks to <br> for better formatting (but not inside pre tags)
    content = content.replace(/\n/g, '<br>');
    // Fix line breaks inside pre tags (they shouldn't be converted to <br>)
    content = content.replace(/<pre>([\s\S]*?)<\/pre>/g, (match, preContent) => {
        return '<pre>' + preContent.replace(/<br>/g, '\n') + '</pre>';
    });

    return content;
}

// Export functions for use in other files (if using modules)
// For non-module use, these functions will be available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        formatDate,
        formatContent
    };
}
