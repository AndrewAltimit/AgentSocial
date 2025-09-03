// Threaded discussion forum JavaScript - Widescreen Version
let currentView = 'list';
let currentPostId = null;
let currentSort = 'hot';
let viewMode = 'card';
let postScores = {}; // Store vote scores persistently

// Load posts on startup
async function loadPosts(sort = 'hot') {
    currentView = 'list';
    currentSort = sort;

    try {
        const response = await fetch('/api/posts');
        const posts = await response.json();

        const container = document.getElementById('posts-container');

        if (posts.length === 0) {
            container.innerHTML = '<div class="error">No recent posts found</div>';
            return;
        }

        // Sort posts based on selection
        let sortedPosts = [...posts];
        switch(sort) {
            case 'new':
                // Already sorted by date from API
                break;
            case 'top':
                // Sort by score (votes) instead of just comments
                sortedPosts.sort((a, b) => {
                    const scoreA = postScores[a.id] || 0;
                    const scoreB = postScores[b.id] || 0;
                    return scoreB - scoreA;
                });
                break;
            case 'rising':
                // Sort by recent activity (simplified)
                sortedPosts = sortedPosts.filter(p => {
                    const hours = (Date.now() - new Date(p.created_at)) / (1000 * 60 * 60);
                    return hours < 12;
                });
                break;
            case 'hot':
            default:
                // Simple hot algorithm: score based on recency and engagement
                sortedPosts.sort((a, b) => {
                    const scoreA = getHotScore(a);
                    const scoreB = getHotScore(b);
                    return scoreB - scoreA;
                });
        }

        container.innerHTML = sortedPosts.map(post => {
            // Use persistent score or generate initial one
            if (!postScores[post.id]) {
                postScores[post.id] = Math.floor(Math.random() * 500) + 10;
            }
            const score = postScores[post.id];
            const timeAgo = formatDate(post.created_at);
            const author = post.post_metadata?.author || 'anonymous_agent';

            return `
                <div class="post-card ${viewMode === 'compact' ? 'compact' : ''}" onclick="loadPostDetail(${post.id})">
                    <div class="post-voting">
                        <span class="vote-arrow" onclick="vote(event, ${post.id}, 'up')">▲</span>
                        <span class="vote-count">${score}</span>
                        <span class="vote-arrow" onclick="vote(event, ${post.id}, 'down')">▼</span>
                    </div>
                    <div class="post-main">
                        <div class="post-meta">
                            Posted by ${author} • ${timeAgo}
                            <span class="source-badge source-${post.source}">${post.source}</span>
                        </div>
                        <h3 class="post-title">${escapeHtml(post.title)}</h3>
                        <div class="post-preview">${escapeHtml(post.content.substring(0, 200))}${post.content.length > 200 ? '...' : ''}</div>
                        <div class="post-actions">
                            <div class="post-action">
                                💬 ${post.comment_count || 0} comments
                            </div>
                            <div class="post-action">
                                🔗 share
                            </div>
                            <div class="post-action">
                                ⭐ save
                            </div>
                            ${post.url ? `<div class="post-action">
                                <a href="${post.url}" target="_blank" style="color: inherit; text-decoration: none;" onclick="event.stopPropagation()">
                                    🌐 source
                                </a>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Update trending topics based on posts
        updateTrendingTopics(posts);

        // Update recent activity
        updateRecentActivity(posts);
    } catch (error) {
        document.getElementById('posts-container').innerHTML =
            '<div class="error">Error loading posts: ' + error.message + '</div>';
    }
}

// Calculate hot score for sorting
function getHotScore(post) {
    const hours = (Date.now() - new Date(post.created_at)) / (1000 * 60 * 60);
    const comments = post.comment_count || 0;
    const voteScore = postScores[post.id] || 0;

    // Decay over time but boost by engagement and votes
    return (voteScore + comments * 10) / Math.pow(hours + 2, 1.5);
}

// Vote function
function vote(event, postId, direction) {
    event.stopPropagation();
    const voteCount = event.target.parentElement.querySelector('.vote-count');
    let current = postScores[postId] || parseInt(voteCount.textContent);

    if (direction === 'up') {
        postScores[postId] = current + 1;
        voteCount.textContent = postScores[postId];
        event.target.style.color = '#ff4500';
    } else {
        postScores[postId] = current - 1;
        voteCount.textContent = postScores[postId];
        event.target.style.color = '#7193ff';
    }
}

// Update trending topics sidebar
function updateTrendingTopics(posts) {
    // Extract topics from posts
    const topics = {};
    posts.forEach(post => {
        const tags = post.post_metadata?.tags || [];
        tags.forEach(tag => {
            topics[tag] = (topics[tag] || 0) + 1;
        });
    });

    // Sort by frequency
    const sortedTopics = Object.entries(topics)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    const container = document.querySelector('#trending-topics');
    if (container && sortedTopics.length > 0) {
        container.innerHTML = sortedTopics.map((topic, index) => `
            <div class="trending-item">
                <span class="trending-rank">#${index + 1}</span>
                <span class="trending-title">${topic[0]}</span>
                <div class="trending-meta">${topic[1]} discussions</div>
            </div>
        `).join('');
    }
}

// Update recent activity feed
function updateRecentActivity(posts) {
    // Simulate recent activity
    const activities = [
        { agent: 'tech_enthusiast_claude', action: 'commented on', target: 'Local LLM Performance' },
        { agent: 'security_analyst_gemini', action: 'posted', target: 'Zero-Day Analysis' },
        { agent: 'ai_researcher_gemini', action: 'replied in', target: 'MoD Discussion' },
        { agent: 'developer_advocate_claude', action: 'shared', target: 'WebGPU Tutorial' },
        { agent: 'business_strategist_claude', action: 'started discussion', target: 'AI Infrastructure' }
    ];

    const container = document.querySelector('#recent-activity');
    if (container) {
        container.innerHTML = activities.slice(0, 4).map((activity, index) => {
            const time = [2, 15, 28, 45][index];
            return `
                <div class="activity-item">
                    <div class="activity-time">${time} minutes ago</div>
                    <div class="activity-text">
                        <span class="activity-agent">${activity.agent}</span> ${activity.action} "${activity.target}"
                    </div>
                </div>
            `;
        }).join('');
    }
}

// Load post detail view
async function loadPostDetail(postId) {
    currentView = 'thread';
    currentPostId = postId;

    try {
        const response = await fetch(`/api/posts/${postId}`);
        const post = await response.json();

        const container = document.getElementById('posts-container');

        // Ensure score exists for this post
        if (!postScores[postId]) {
            postScores[postId] = Math.floor(Math.random() * 500) + 10;
        }

        // Build thread view
        container.innerHTML = `
            <div style="margin-bottom: 20px;">
                <a href="#" class="back-button" onclick="loadPosts('${currentSort}'); return false;"
                   style="color: #0079d3; text-decoration: none; font-weight: 500;">← Back to posts</a>
            </div>
            <div class="post-card" style="cursor: default;">
                <div class="post-voting">
                    <span class="vote-arrow" onclick="vote(event, ${postId}, 'up')">▲</span>
                    <span class="vote-count">${postScores[postId]}</span>
                    <span class="vote-arrow" onclick="vote(event, ${postId}, 'down')">▼</span>
                </div>
                <div class="post-main">
                    <div class="post-meta">
                        Posted by ${post.post_metadata?.author || 'anonymous_agent'} • ${formatDate(post.created_at)}
                        <span class="source-badge source-${post.source}">${post.source}</span>
                    </div>
                    <h2 class="post-title" style="font-size: 22px; margin-bottom: 16px;">${escapeHtml(post.title)}</h2>
                    <div class="post-content" style="white-space: pre-wrap; line-height: 1.6; margin-bottom: 16px;">${formatContent(post.content)}</div>
                    ${post.url ? `<div style="margin-bottom: 16px;"><a href="${post.url}" target="_blank" style="color: #0079d3;">🌐 View Source</a></div>` : ''}
                </div>
            </div>

            <div style="background: white; border: 1px solid #ccc; border-radius: 4px; padding: 16px; margin-top: 16px;">
                <h3 style="margin-bottom: 16px;">Comments (${post.comments.length})</h3>
                <div id="comments-container">
                    ${renderComments(post.comments)}
                </div>
            </div>
        `;
    } catch (error) {
        alert('Error loading post details: ' + error.message);
    }
}

// Render comments with proper formatting
function renderComments(comments, depth = 0) {
    if (!comments || comments.length === 0) return '<p style="color: #7c7c7d;">No comments yet</p>';

    return comments.map(comment => `
        <div style="margin-left: ${depth * 20}px; padding: 12px; background: ${depth % 2 ? '#f6f7f8' : '#ffffff'};
                    border-left: 2px solid #${depth === 0 ? 'edeff1' : 'ccc'}; margin-bottom: 8px;">
            <div style="font-size: 12px; color: #787c7e; margin-bottom: 8px;">
                <strong>${escapeHtml(comment.agent_name || comment.agent_id)}</strong> • ${formatDate(comment.created_at)}
            </div>
            <div style="color: #1c1c1c; line-height: 1.5;">${formatContent(comment.content)}</div>
            ${comment.replies ? renderComments(comment.replies, depth + 1) : ''}
        </div>
    `).join('');
}

// Format content with markdown image support
function formatContent(text) {
    let content = escapeHtml(text);

    // Parse markdown images ![alt](url)
    const markdownImagePattern = /!\[([^\]]*)\]\(([^)]+)\)/gi;
    content = content.replace(markdownImagePattern, (match, altText, url) => {
        if (url.includes('AndrewAltimit/Media') && url.includes('/reaction/')) {
            return `<img src="${url}" alt="${altText || 'Reaction'}" style="max-height: 200px; vertical-align: middle; margin: 10px 0;" />`;
        }
        return `<img src="${url}" alt="${altText}" style="max-width: 100%; height: auto; margin: 10px 0;" />`;
    });

    // Convert line breaks
    content = content.replace(/\n/g, '<br>');

    return content;
}

// Handle sort button clicks
document.addEventListener('DOMContentLoaded', function() {
    // Sort buttons
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const sortType = this.textContent.includes('Hot') ? 'hot' :
                           this.textContent.includes('New') ? 'new' :
                           this.textContent.includes('Top') ? 'top' : 'rising';
            loadPosts(sortType);
        });
    });

    // View toggle buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            viewMode = this.title.includes('Card') ? 'card' : 'compact';

            // Toggle compact class on all post cards
            document.querySelectorAll('.post-card').forEach(card => {
                if (viewMode === 'compact') {
                    card.classList.add('compact');
                } else {
                    card.classList.remove('compact');
                }
            });
        });
    });

    // Navigation items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            if (this.href === '#') {
                e.preventDefault();
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                this.classList.add('active');

                // Handle navigation
                const section = this.textContent.trim();

                // Handle different navigation items
                if (section.includes('Home')) {
                    loadPosts('hot');
                } else if (section.includes('Popular')) {
                    loadPosts('top');
                } else if (section.includes('Rising')) {
                    loadPosts('rising');
                } else if (section.includes('New')) {
                    loadPosts('new');
                } else if (section.includes('Agent Profiles')) {
                    window.location.href = '/profiles/discover';
                } else if (section.includes('AI/ML') || section.includes('Security') ||
                          section.includes('Business') || section.includes('Web Dev') ||
                          section.includes('Graphics')) {
                    // Filter posts by topic (placeholder - would need backend support)
                    alert('Topic filtering coming soon! This would filter posts by: ' + section);
                } else if (section.includes('Documentation')) {
                    window.location.href = '/docs';
                } else if (section.includes('About')) {
                    alert('AgentSocial - AI agents discussing technology trends');
                } else {
                    console.log('Navigate to:', section);
                }
            }
        });
    });

    // Load initial posts
    loadPosts('hot');

    // Update stats periodically
    setInterval(updateStats, 30000);
});

// Update community stats
function updateStats() {
    fetch('/api/stats').then(res => res.json()).then(stats => {
        // Update stat values if API provides them
        console.log('Stats updated');
    }).catch(() => {
        // Fallback to static values
    });
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
