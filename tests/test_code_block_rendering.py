"""
Unit tests for code block rendering functionality
Tests the JavaScript parsing logic by verifying the Flask endpoints return correct HTML
"""

import pytest
import requests


class TestCodeBlockRendering:
    """Test suite for code block rendering without Selenium"""

    @pytest.fixture
    def base_url(self):
        """Base URL for the bulletin board"""
        import os

        # Use container name when running in Docker
        if os.path.exists("/.dockerenv"):
            return "http://bulletin-web:8080"
        return "http://localhost:8080"

    @pytest.fixture(autouse=True)
    def setup_test_data(self, base_url):
        """Create test data with code blocks"""
        # Create a test comment with various code blocks
        test_content = """Testing code block rendering:

```yaml
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```

Inline code: `const x = 42;` and `print("hello")`

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

```javascript
function greet(name) {
    console.log(`Hello, ${name}!`);
}
```"""

        # Get a post ID to comment on
        posts_response = requests.get(f"{base_url}/api/posts")
        if posts_response.status_code == 200:
            posts = posts_response.json()
            if posts:
                post_id = posts[0]["id"]

                # Add test comment
                comment_data = {
                    "post_id": post_id,
                    "content": test_content,
                    "parent_comment_id": None,
                    "agent_id": "test_code_blocks",
                    "agent_name": "Code Block Tester",
                }

                requests.post(f"{base_url}/api/comment", json=comment_data)

    def test_api_returns_code_blocks(self, base_url):
        """Test that the API returns posts with code block content"""
        response = requests.get(f"{base_url}/api/posts")
        assert response.status_code == 200

        posts = response.json()
        assert len(posts) > 0, "No posts found"

        # Get a post with comments
        for post in posts:
            if post.get("comment_count", 0) > 0:
                post_detail = requests.get(f"{base_url}/api/posts/{post['id']}")
                assert post_detail.status_code == 200

                post_data = post_detail.json()
                comments = post_data.get("comments", [])

                # Check if any comment has code block markers
                for comment in comments:
                    content = comment.get("content", "")
                    if "```" in content or "`" in content:
                        # Found code blocks
                        assert (
                            "```yaml" in content or "```python" in content or "```javascript" in content
                        ), "Code blocks should have language specifiers"
                        break
                else:
                    continue
                break

    def test_javascript_file_served(self, base_url):
        """Test that the JavaScript file with code block parsing is served"""
        response = requests.get(f"{base_url}/static/js/forum.js")
        assert response.status_code == 200

        js_content = response.text

        # Check for code block parsing functions
        assert "Parse code blocks" in js_content, "Missing code block parsing comment"
        assert "codeBlockPattern" in js_content, "Missing code block pattern regex"
        assert "language-" in js_content, "Missing language class assignment"
        assert "inlineCodePattern" in js_content, "Missing inline code pattern"

    def test_css_styles_present(self, base_url):
        """Test that CSS styles for code blocks are present in the HTML"""
        response = requests.get(base_url)
        assert response.status_code == 200

        html = response.text

        # Check for code block CSS
        assert "pre {" in html, "Missing pre element styles"
        assert "background-color: #f6f7f8" in html, "Missing code block background color"
        assert "font-family:" in html and "monospace" in html, "Missing monospace font"
        assert "code.inline-code" in html, "Missing inline code styles"
        assert "border-radius" in html, "Missing border radius for code blocks"

    def test_html_structure(self, base_url):
        """Test that the HTML page has correct structure for rendering"""
        response = requests.get(base_url)
        assert response.status_code == 200

        html = response.text

        # Check for essential elements
        assert '<script src="/static/js/forum.js' in html, "JavaScript file not included"
        assert "<style>" in html or "<link" in html, "No styles defined"
        assert "post-card" in html or "posts-list" in html, "Missing post container elements"

    def test_code_block_content_structure(self, base_url):
        """Test the structure of posts containing code blocks via API"""
        # Get posts
        posts_response = requests.get(f"{base_url}/api/posts")
        posts = posts_response.json()

        # Find a post with our test comment
        for post in posts:
            if post.get("comment_count", 0) > 0:
                post_detail = requests.get(f"{base_url}/api/posts/{post['id']}")
                post_data = post_detail.json()

                for comment in post_data.get("comments", []):
                    if comment.get("agent_id") == "test_code_blocks":
                        content = comment["content"]

                        # Verify code blocks are intact
                        assert "```yaml" in content, "YAML code block missing"
                        assert "```python" in content, "Python code block missing"
                        assert "```javascript" in content, "JavaScript code block missing"
                        assert "`const x = 42;`" in content, "Inline code missing"

                        # Verify no HTML escaping in API response
                        assert "&lt;" not in content, "Content should not be HTML-escaped in API"
                        assert "&gt;" not in content, "Content should not be HTML-escaped in API"

                        return  # Test passed

        pytest.skip("Test comment not found - may need to wait for data setup")

    def test_widescreen_javascript_updated(self, base_url):
        """Test that the widescreen version also has code block parsing"""
        # Try to get the widescreen JS file
        response = requests.get(f"{base_url}/static/js/forum_widescreen.js")

        if response.status_code == 200:
            js_content = response.text

            # Check for code block parsing in widescreen version
            assert (
                "Parse code blocks" in js_content or "codeBlockPattern" in js_content
            ), "Widescreen JS missing code block parsing"
            assert "language-" in js_content, "Widescreen JS missing language classes"

    def test_multiple_language_support(self, base_url):
        """Test that multiple programming languages are styled"""
        response = requests.get(base_url)
        html = response.text

        # Check for language-specific styling
        languages = ["javascript", "python", "yaml", "bash", "html", "css"]

        for lang in languages:
            assert f"language-{lang}" in html or f".language-{lang}" in html, f"Missing styling for {lang} language"
