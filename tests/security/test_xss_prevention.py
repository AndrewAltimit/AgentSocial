"""
Comprehensive XSS (Cross-Site Scripting) prevention tests
Tests that various XSS payloads are properly sanitized
"""

import time

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestXSSPrevention:
    """Test suite for XSS prevention across all user input fields"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = "http://localhost:8080"
        cls.api_base = "http://localhost:8080/api"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up after tests"""
        cls.driver.quit()

    # XSS Payloads to test
    XSS_PAYLOADS = [
        # Basic script injection
        "<script>alert('XSS')</script>",
        "<SCRIPT>alert('XSS')</SCRIPT>",
        "<script>alert(String.fromCharCode(88,83,83))</script>",
        # IMG tag attacks
        "<img src=x onerror=alert('XSS')>",
        "<IMG SRC=javascript:alert('XSS')>",
        "<img src='x' onerror='alert(1)'>",
        # IFRAME attacks
        "<iframe src=javascript:alert('XSS')></iframe>",
        "<IFRAME SRC='javascript:alert(\"XSS\")'></IFRAME>",
        # Event handler attacks
        "<div onclick='alert(1)'>Click me</div>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        # Link attacks
        "<a href='javascript:alert(1)'>Click</a>",
        "<a href='JAVAscript:alert(\"XSS\")'>Click</a>",
        # SVG attacks
        "<svg onload=alert('XSS')>",
        "<svg><script>alert('XSS')</script></svg>",
        # Style attacks
        "<style>body{background:url('javascript:alert(1)')}</style>",
        "<link rel='stylesheet' href='javascript:alert(1)'>",
        # Meta refresh
        "<meta http-equiv='refresh' content='0;javascript:alert(1)'>",
        # Data URI attacks
        "<object data='data:text/html,<script>alert(1)</script>'>",
        # HTML5 attacks
        "<video><source onerror='alert(1)'>",
        "<audio src=x onerror=alert('XSS')>",
        # Encoded attacks
        "&#60;script&#62;alert('XSS')&#60;/script&#62;",
        "%3Cscript%3Ealert('XSS')%3C/script%3E",
        # Embed tag (should be carefully handled for MySpace profiles)
        "<embed src='javascript:alert(1)'>",
        "<embed src='http://evil.com/malware.swf'>",
    ]

    def check_no_xss_execution(self):
        """Check that no XSS payload has executed"""
        try:
            # Check for unexpected alerts
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.dismiss()
            pytest.fail(f"XSS Alert detected: {alert_text}")
        except Exception:
            # No alert present, which is good
            pass

        # Check that no script tags are present in the DOM
        scripts = self.driver.find_elements(By.TAG_NAME, "script")
        for script in scripts:
            src = script.get_attribute("src") or ""
            content = script.get_attribute("innerHTML") or ""

            # Allow legitimate scripts (Prism.js, utils.js, etc.)
            if "evil" in src.lower() or "evil" in content.lower():
                pytest.fail(f"Malicious script found: {src or content[:100]}")
            if "alert" in content and "XSS" in content:
                pytest.fail(f"XSS script found: {content[:100]}")

    def test_comment_xss_prevention(self):
        """Test XSS prevention in comment fields"""
        # Navigate to a forum post
        self.driver.get(f"{self.base_url}/forum")
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on first post
        post = self.driver.find_element(By.CLASS_NAME, "post-card")
        post.click()

        time.sleep(2)

        # Try to inject XSS in comments
        for payload in self.XSS_PAYLOADS[:5]:  # Test first 5 payloads
            comment_field = self.driver.find_element(By.ID, "comment-input")
            comment_field.clear()
            comment_field.send_keys(payload)

            # Submit comment
            submit_btn = self.driver.find_element(By.ID, "submit-comment")
            submit_btn.click()

            time.sleep(1)

            # Check that XSS didn't execute
            self.check_no_xss_execution()

            # Verify the payload was sanitized in the displayed comment
            comments = self.driver.find_elements(By.CLASS_NAME, "comment-body")
            if comments:
                last_comment = comments[-1].get_attribute("innerHTML")
                assert "<script" not in last_comment.lower()
                assert "javascript:" not in last_comment.lower()
                assert "onerror" not in last_comment.lower()

    def test_profile_xss_prevention(self):
        """Test XSS prevention in profile customization"""
        # Test via API endpoint
        test_agent_id = "xss_test_agent"

        for payload in self.XSS_PAYLOADS[:5]:
            response = requests.post(
                f"{self.api_base}/profile/customize",
                json={
                    "agent_id": test_agent_id,
                    "about_me": payload,
                    "custom_html": payload,
                    "profile_title": payload,
                    "status_message": payload,
                },
            )

            if response.status_code == 200:
                # Check the profile page
                self.driver.get(f"{self.base_url}/profiles/{test_agent_id}")
                time.sleep(1)

                # Check that XSS didn't execute
                self.check_no_xss_execution()

                # Verify content is sanitized
                page_source = self.driver.page_source.lower()
                assert "<script" not in page_source or "prism" in page_source  # Allow Prism.js
                assert "javascript:alert" not in page_source
                assert "onerror=alert" not in page_source

    def test_post_title_xss_prevention(self):
        """Test XSS prevention in post titles"""
        # Test creating posts with XSS in titles
        for payload in self.XSS_PAYLOADS[:3]:
            response = requests.post(
                f"{self.api_base}/post", json={"agent_id": "test_agent", "title": payload, "content": "Test content"}
            )

            if response.status_code == 200:
                post_id = response.json().get("id")

                # Check the post
                self.driver.get(f"{self.base_url}/post/{post_id}")
                time.sleep(1)

                # Check that XSS didn't execute
                self.check_no_xss_execution()

                # Verify title is sanitized
                title_elem = self.driver.find_element(By.TAG_NAME, "h1")
                title_html = title_elem.get_attribute("innerHTML")
                assert "<script" not in title_html.lower()
                assert "javascript:" not in title_html.lower()

    def test_json_field_xss_prevention(self):
        """Test XSS prevention in JSON fields like interests"""
        test_agent_id = "json_xss_test"

        # Create profile with XSS in JSON fields
        response = requests.post(
            f"{self.api_base}/profile/customize",
            json={
                "agent_id": test_agent_id,
                "interests": ["<script>alert('XSS')</script>", "<img src=x onerror=alert(1)>"],
                "favorite_movies": ["<iframe src='javascript:alert(1)'></iframe>"],
            },
        )

        if response.status_code == 200:
            # Check the profile
            self.driver.get(f"{self.base_url}/profiles/{test_agent_id}")
            time.sleep(1)

            # Check that XSS didn't execute
            self.check_no_xss_execution()

            # Verify JSON data is displayed safely
            page_source = self.driver.page_source
            assert "&lt;script&gt;" in page_source or "<script" not in page_source.lower()

    def test_embed_tag_filtering(self):
        """Test that embed tags are filtered to only allow trusted sources"""
        test_agent_id = "embed_test"

        # Try various embed sources
        embed_tests = [
            # Should be blocked
            ("<embed src='javascript:alert(1)'>", False),
            ("<embed src='http://evil.com/bad.swf'>", False),
            ("<embed src='data:text/html,<script>alert(1)</script>'>", False),
            # Should be allowed (trusted sources)
            ("<embed src='https://www.youtube.com/embed/video'>", True),
            ("<embed src='https://player.vimeo.com/video/123'>", True),
            ("<embed src='https://w.soundcloud.com/player/track'>", True),
        ]

        for embed_html, should_allow in embed_tests:
            response = requests.post(
                f"{self.api_base}/profile/customize", json={"agent_id": test_agent_id, "custom_html": embed_html}
            )

            if response.status_code == 200:
                # Check the profile
                self.driver.get(f"{self.base_url}/profiles/{test_agent_id}")
                time.sleep(1)

                # Check presence of embed
                embeds = self.driver.find_elements(By.TAG_NAME, "embed")

                if should_allow:
                    assert len(embeds) > 0, f"Trusted embed was blocked: {embed_html}"
                else:
                    # Check that malicious embed was removed
                    for embed in embeds:
                        src = embed.get_attribute("src") or ""
                        assert "evil.com" not in src
                        assert "javascript:" not in src
                        assert "data:" not in src

    def test_persistent_xss_prevention(self):
        """Test that stored XSS payloads remain sanitized over time"""
        test_agent_id = "persistent_xss_test"

        # Store XSS payload
        requests.post(
            f"{self.api_base}/profile/customize",
            json={"agent_id": test_agent_id, "about_me": "<script>document.cookie='hacked=true'</script>"},
        )

        # Visit profile multiple times
        for _ in range(3):
            self.driver.get(f"{self.base_url}/profiles/{test_agent_id}")
            time.sleep(1)

            # Check that XSS didn't execute
            self.check_no_xss_execution()

            # Check cookies weren't modified
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                assert cookie["name"] != "hacked", "XSS payload executed and set cookie"

    def test_markdown_xss_prevention(self):
        """Test XSS prevention in markdown content"""
        # Create post with markdown containing XSS
        markdown_with_xss = """
# Title
<script>alert('XSS')</script>

[Click me](javascript:alert('XSS'))

![image](x" onerror="alert('XSS'))

<iframe src="javascript:alert('XSS')"></iframe>
        """

        response = requests.post(
            f"{self.api_base}/post",
            json={"agent_id": "test_agent", "title": "Markdown XSS Test", "content": markdown_with_xss},
        )

        if response.status_code == 200:
            post_id = response.json().get("id")

            # View the post
            self.driver.get(f"{self.base_url}/post/{post_id}")
            time.sleep(1)

            # Check that XSS didn't execute
            self.check_no_xss_execution()

            # Verify dangerous elements are removed
            content = self.driver.find_element(By.CLASS_NAME, "post-content")
            content_html = content.get_attribute("innerHTML").lower()

            assert "javascript:" not in content_html
            assert "<script" not in content_html or "prism" in content_html
            assert "<iframe" not in content_html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
