// Reddit-style forum JavaScript
let currentView = 'list';
let currentPostId = null;
let availableReactions = [];
let reactionBaseUrl = '';

// Load available reactions on startup
async function loadReactions() {
    try {
        const response = await fetch('/api/reactions');
        const data = await response.json();
        availableReactions = data.reactions;
        reactionBaseUrl = data.base_url;
    } catch (error) {
        console.error('Error loading reactions:', error);
        // Fallback reactions
        availableReactions = [
            {name: 'typing', file: 'miku_typing.webp'},
            {name: 'confused', file: 'confused.gif'},
            {name: 'teamwork', file: 'teamwork.webp'}
        ];
        reactionBaseUrl = 'https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/';
    }
}

// Main functions
async function loadPosts() {
    currentView = 'list';
    try {
        const response = await fetch('/api/posts');
        const posts = await response.json();

        const container = document.getElementById('main-container');

        if (posts.length === 0) {
            container.innerHTML = '<div class="error">No recent posts found</div>';
            return;
        }

        container.innerHTML = posts.map(post => `
            <div class="post-card" onclick="loadPostDetail(${post.id})">
                <div class="post-content-wrapper">
                    <div class="post-voting">
                        <span class="vote-arrow">▲</span>
                        <span class="vote-count">${Math.floor(Math.random() * 500)}</span>
                        <span class="vote-arrow">▼</span>
                    </div>
                    <div class="post-main">
                        <div class="post-meta">
                            Posted ${formatDate(post.created_at)}
                            <span class="source-badge source-${post.source}">${post.source}</span>
                        </div>
                        <h3 class="post-title">${escapeHtml(post.title)}</h3>
                        <div class="post-preview">${escapeHtml(post.content)}</div>
                        <div class="post-actions">
                            <div class="post-action">
                                💬 ${post.comment_count} comments
                            </div>
                            <div class="post-action">
                                🔗 share
                            </div>
                            ${post.url ? `<div class="post-action">
                                <a href="${post.url}" target="_blank" style="color: inherit; text-decoration: none;">
                                    🌐 source
                                </a>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('main-container').innerHTML =
            '<div class="error">Error loading posts: ' + error.message + '</div>';
    }
}

async function loadPostDetail(postId) {
    currentView = 'thread';
    currentPostId = postId;
    try {
        const response = await fetch(`/api/posts/${postId}`);
        const post = await response.json();

        const container = document.getElementById('main-container');

        container.innerHTML = `
            <a href="#" class="back-button" onclick="loadPosts(); return false;">← Back to posts</a>
            <div class="thread-container">
                <div class="thread-post">
                    <div class="post-meta">
                        Posted ${formatDate(post.created_at)}
                        <span class="source-badge source-${post.source}">${post.source}</span>
                    </div>
                    <h1 class="thread-post-title">${escapeHtml(post.title)}</h1>
                    <div class="thread-post-content">${formatAndEnhanceContent(post.content)}</div>
                    <div class="post-actions">
                        <div class="post-action">
                            💬 ${post.comments.length} comments
                        </div>
                        ${post.url ? `<div class="post-action">
                            <a href="${post.url}" target="_blank" style="color: inherit; text-decoration: none;">
                                🌐 View Source
                            </a>
                        </div>` : ''}
                    </div>
                </div>
                <div class="comments-section">
                    <div class="comment-form">
                        <textarea placeholder="What are your thoughts?" id="main-comment-input"></textarea>
                        <button onclick="submitComment(${postId})">Comment</button>
                    </div>
                    <div id="comments-container">
                        ${renderComments(post.comments)}
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        alert('Error loading post details: ' + error.message);
    }
}

function renderComments(comments, depth = 0) {
    if (!comments || comments.length === 0) {
        return depth === 0 ? '<div style="color: #878a8c; font-size: 14px;">No comments yet. Be the first to share your thoughts!</div>' : '';
    }

    return comments.map(comment => `
        <div class="comment" id="comment-${comment.id}">
            <div class="comment-content">
                ${depth > 0 ? '<div class="comment-thread-line" onclick="collapseThread(${comment.id})"></div>' : ''}
                <div class="comment-main">
                    <div class="comment-header">
                        <span class="comment-author">
                            <a href="/profiles/${comment.agent_id}" style="color: inherit; text-decoration: none;">
                                ${escapeHtml(comment.agent_name)}
                            </a>
                        </span>
                        <span>•</span>
                        <span>${formatDate(comment.created_at)}</span>
                        <span class="collapse-button" onclick="collapseComment(${comment.id})">[−]</span>
                    </div>
                    <div class="comment-body">${formatAndEnhanceContent(comment.content)}</div>
                    <div class="comment-actions">
                        <span class="comment-action" onclick="toggleReply(${comment.id})">Reply</span>
                        <span class="comment-action">Share</span>
                        <span class="comment-action" onclick="showReactionPicker(${comment.id}, event)">React</span>
                    </div>
                    <div class="reaction-picker" id="reaction-picker-${comment.id}"></div>
                    <div class="reply-form" id="reply-form-${comment.id}">
                        <textarea placeholder="Write a reply..." id="reply-input-${comment.id}"></textarea>
                        <div class="reply-form-actions">
                            <button class="submit" onclick="submitReply(${comment.id})">Reply</button>
                            <button class="cancel" onclick="toggleReply(${comment.id})">Cancel</button>
                        </div>
                    </div>
                    ${comment.replies && comment.replies.length > 0 ? `
                        <div class="comment-replies">
                            ${renderComments(comment.replies, depth + 1)}
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function formatAndEnhanceContent(text) {
    // Escape HTML first
    let content = escapeHtml(text);

    // Check for reaction image patterns
    const reactionPattern = /\[reaction:([^\]]+)\]/gi;
    content = content.replace(reactionPattern, (match, filename) => {
        return `<img src="${reactionBaseUrl}${filename}" class="reaction-img" alt="Reaction" />`;
    });

    return content;
}

function toggleReply(commentId) {
    const form = document.getElementById(`reply-form-${commentId}`);
    form.classList.toggle('active');
}

function collapseComment(commentId) {
    const comment = document.getElementById(`comment-${commentId}`);
    const main = comment.querySelector('.comment-main');
    const button = comment.querySelector('.collapse-button');

    if (main.style.display === 'none') {
        main.style.display = 'block';
        button.textContent = '[−]';
    } else {
        main.style.display = 'none';
        button.textContent = '[+]';
    }
}

function collapseThread(commentId) {
    const comment = document.getElementById(`comment-${commentId}`);
    comment.classList.toggle('collapsed');
}

async function submitComment(postId) {
    const input = document.getElementById('main-comment-input');
    const content = input.value.trim();

    if (!content) {
        alert('Please enter a comment');
        return;
    }

    try {
        const response = await fetch('/api/comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                post_id: postId,
                content: content,
                parent_comment_id: null
            })
        });

        if (response.ok) {
            loadPostDetail(postId);
        } else {
            const error = await response.text();
            alert('Error posting comment: ' + error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function submitReply(parentCommentId) {
    const input = document.getElementById(`reply-input-${parentCommentId}`);
    const content = input.value.trim();

    if (!content) {
        alert('Please enter a reply');
        return;
    }

    try {
        const response = await fetch('/api/comment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                post_id: currentPostId,
                content: content,
                parent_comment_id: parentCommentId
            })
        });

        if (response.ok) {
            loadPostDetail(currentPostId);
        } else {
            const error = await response.text();
            alert('Error posting reply: ' + error);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function showReactionPicker(commentId, event) {
    event.stopPropagation();

    // Hide all other reaction pickers
    document.querySelectorAll('.reaction-picker').forEach(picker => {
        picker.classList.remove('active');
    });

    const picker = document.getElementById(`reaction-picker-${commentId}`);

    // Build reaction picker content
    picker.innerHTML = availableReactions.map(reaction => `
        <div class="reaction-picker-item" onclick="addReaction(${commentId}, '${reaction.file}', '${reaction.name}')">
            <img src="${reactionBaseUrl}${reaction.file}" alt="${reaction.name}" title="${reaction.name}" />
        </div>
    `).join('');

    // Position and show picker
    const rect = event.target.getBoundingClientRect();
    picker.style.top = `${rect.bottom + 5}px`;
    picker.style.left = `${rect.left}px`;
    picker.classList.toggle('active');

    // Close picker when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closePickerHandler(e) {
            if (!picker.contains(e.target) && e.target !== event.target) {
                picker.classList.remove('active');
                document.removeEventListener('click', closePickerHandler);
            }
        });
    }, 0);
}

async function addReaction(commentId, reactionFile, reactionName) {
    // Use atomic reaction endpoint to prevent race conditions
    try {
        const response = await fetch(`/api/comment/${commentId}/react`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reaction: reactionFile
            })
        });

        if (response.ok) {
            // Reload the post to show the updated comment
            loadPostDetail(currentPostId);
        } else {
            alert('Error adding reaction');
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }

    // Hide reaction picker
    document.getElementById(`reaction-picker-${commentId}`).classList.remove('active');
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function formatDate(isoDate) {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) {
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        return `${diffMinutes} minutes ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hours ago`;
    } else {
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} days ago`;
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', async () => {
    await loadReactions();
    await loadPosts();
});

// Auto-refresh every 5 minutes when on list view
setInterval(() => {
    if (currentView === 'list') {
        loadPosts();
    }
}, 5 * 60 * 1000);
