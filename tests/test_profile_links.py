"""
Test that usernames in comments and posts link to profile pages
"""

import pytest
import requests


class TestProfileLinks:
    """Test suite for profile link functionality"""

    @pytest.fixture
    def base_url(self):
        """Base URL for the bulletin board"""
        import os

        # Use container name when running in Docker
        if os.path.exists("/.dockerenv"):
            return "http://bulletin-web:8080"
        return "http://localhost:8080"

    def test_comment_usernames_have_profile_links(self, base_url):
        """Test that comment usernames contain profile links in HTML"""
        # Get a post with comments
        posts_response = requests.get(f"{base_url}/api/posts")
        posts = posts_response.json()

        for post in posts:
            if post.get("comment_count", 0) > 0:
                # Get the HTML page for the post
                html_response = requests.get(f"{base_url}/")
                html = html_response.text

                # Check that profile links are present in the JavaScript
                assert "/profiles/" in html, "No profile links found in HTML"

                # Verify the link structure in the JavaScript
                assert 'href="/profiles/' in html or "href='/profiles/" in html, "Profile link structure not found"

                # Check for hover effects
                assert "onmouseover" in html and "textDecoration" in html, "Hover effects for profile links not found"

                break

    def test_profile_route_exists(self, base_url):
        """Test that profile routes are accessible"""
        # Try to access the discover page
        response = requests.get(f"{base_url}/profiles/discover")
        assert response.status_code == 200, "Profile discover page not accessible"

    def test_javascript_contains_profile_links(self, base_url):
        """Test that the JavaScript files contain profile link code"""
        # Check forum.js
        js_response = requests.get(f"{base_url}/static/js/forum.js")
        assert js_response.status_code == 200
        js_content = js_response.text

        # Check for profile links in comments
        assert "/profiles/" in js_content, "Profile links not found in forum.js"
        assert "comment-author" in js_content, "Comment author section not found"

        # Check for the updated styling
        assert "color: #0079d3" in js_content, "Profile link color not set"
        assert "onmouseover" in js_content, "Hover effect not found"

        # Check forum_widescreen.js if available
        widescreen_response = requests.get(f"{base_url}/static/js/forum_widescreen.js")
        if widescreen_response.status_code == 200:
            widescreen_content = widescreen_response.text

            # Check for profile links in widescreen version
            assert "/profiles/" in widescreen_content, "Profile links not found in forum_widescreen.js"

            # Check both comment and post author links
            assert (
                "Posted by <a href" in widescreen_content or "Posted by<a href" in widescreen_content
            ), "Post author links not found in widescreen version"

    def test_profile_links_in_post_metadata(self, base_url):
        """Test that post authors have profile links"""
        # Check the main page HTML
        response = requests.get(base_url)
        response.text  # Access but don't store since we check JS instead

        # The JavaScript should contain profile links in post metadata
        js_response = requests.get(f"{base_url}/static/js/forum.js")
        js_content = js_response.text

        # Check for "Posted by" with links
        assert "Posted by" in js_content, "Posted by text not found"
        assert (
            "post.agent_id" in js_content or "comment.agent_id" in js_content
        ), "Agent ID reference not found for profile links"

    def test_profile_api_endpoint(self, base_url):
        """Test that profile API endpoints are available"""
        # Get posts to find an agent_id
        posts_response = requests.get(f"{base_url}/api/posts")
        posts = posts_response.json()

        if posts:
            # Get the first post's details
            post_id = posts[0]["id"]
            post_detail = requests.get(f"{base_url}/api/posts/{post_id}")
            post_data = post_detail.json()

            # Check if we have an agent_id to test with
            if post_data.get("agent_id"):
                agent_id = post_data["agent_id"]

                # Try to access the profile page (it should exist or return appropriate error)
                profile_response = requests.get(f"{base_url}/profiles/{agent_id}")

                # Profile page should either exist (200) or return 404 if agent not found
                assert profile_response.status_code in [
                    200,
                    404,
                ], f"Unexpected status code for profile page: {profile_response.status_code}"

                # Try the API endpoint
                api_response = requests.get(f"{base_url}/profiles/api/{agent_id}")
                assert api_response.status_code in [
                    200,
                    404,
                ], f"Unexpected status code for profile API: {api_response.status_code}"

    def test_discover_page_accessible(self, base_url):
        """Test that the discover profiles page is accessible"""
        response = requests.get(f"{base_url}/profiles/discover")
        assert response.status_code == 200, "Discover page not accessible"

        # Check that the page contains expected content
        html = response.text
        assert "Discover" in html or "Profile" in html or "Agent" in html, "Discover page doesn't contain expected content"
