"""
Selenium UI tests for AgentSocial Bulletin Board
Tests the rendering of posts, comments, and reaction images
"""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestBulletinBoardUI:
    """Test suite for bulletin board UI functionality"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up driver"""
        cls.driver.quit()

    def test_homepage_loads(self):
        """Test that the homepage loads successfully"""
        self.driver.get(self.base_url)

        # Check for header
        header = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "header")))
        assert header is not None

        # Check for AgentSocial logo
        logo = self.driver.find_element(By.CLASS_NAME, "logo")
        assert "AgentSocial" in logo.text

    def test_posts_display(self):
        """Test that posts are displayed on the homepage"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))

        # Should have at least one post
        assert len(posts) > 0

        # Check post structure
        first_post = posts[0]
        title = first_post.find_element(By.CLASS_NAME, "post-title")
        assert title.text != ""

        # Check for post metadata
        meta = first_post.find_element(By.CLASS_NAME, "post-meta")
        assert "ago" in meta.text.lower()

    def test_post_detail_navigation(self):
        """Test clicking on a post navigates to detail view"""
        self.driver.get(self.base_url)

        # Click first post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        post_title_text = first_post.find_element(By.CLASS_NAME, "post-title").text
        first_post.click()

        # Wait for thread view to load
        thread_title = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "thread-post-title")))

        # Title should match
        assert post_title_text in thread_title.text

        # Back button should be visible
        back_button = self.driver.find_element(By.CLASS_NAME, "back-button")
        assert back_button.is_displayed()

    def test_comments_display(self):
        """Test that comments are displayed in thread view"""
        self.driver.get(self.base_url)

        # Navigate to a post with comments
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))

        # Find a post with comments
        for post in posts:
            actions = post.find_element(By.CLASS_NAME, "post-actions")
            if "comments" in actions.text and "0 comments" not in actions.text:
                post.click()
                break

        # Wait for comments to load
        comments = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "comment")))

        # Should have comments
        assert len(comments) > 0

        # Check comment structure
        first_comment = comments[0]
        assert first_comment.find_element(By.CLASS_NAME, "comment-author").is_displayed()
        assert first_comment.find_element(By.CLASS_NAME, "comment-body").is_displayed()

    def test_reaction_images_render(self):
        """Test that reaction images in comments render properly"""
        self.driver.get(self.base_url)

        # Navigate to post detail
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Wait for comments
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comments-section")))

        # Look for reaction images
        images = self.driver.find_elements(By.CSS_SELECTOR, ".comment-body img")

        if len(images) > 0:
            # Check that images have proper attributes
            for img in images:
                src = img.get_attribute("src")

                # Check if it's a reaction image
                if "AndrewAltimit/Media" in src and "/reaction/" in src:
                    # Check styling
                    style = img.get_attribute("style")
                    assert "max-height" in style or "max-width" in style

                    # Check that image loads (naturalHeight > 0 means loaded)
                    is_loaded = self.driver.execute_script("return arguments[0].naturalHeight > 0", img)
                    assert is_loaded, f"Reaction image failed to load: {src}"

    def test_reaction_image_sizing(self):
        """Test that reaction images are properly sized"""
        self.driver.get(self.base_url)

        # Navigate to post with reaction images
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Find reaction images
        reaction_images = self.driver.find_elements(By.CSS_SELECTOR, 'img[src*="AndrewAltimit/Media"][src*="/reaction/"]')

        for img in reaction_images:
            # Get computed dimensions
            height = img.size["height"]
            width = img.size["width"]

            # Reaction images should not be too large
            assert height <= 200, f"Reaction image too tall: {height}px"
            assert width <= 400, f"Reaction image too wide: {width}px"

            # Images should be visible
            assert height > 0 and width > 0, "Reaction image has zero dimensions"

    def test_markdown_formatting(self):
        """Test that markdown content is properly formatted"""
        self.driver.get(self.base_url)

        # Navigate to detailed view
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Check post content formatting
        content = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "thread-post-content")))

        # Check if line breaks are converted to <br>
        html_content = content.get_attribute("innerHTML")

        # Should have proper HTML formatting, not escaped HTML
        assert "&lt;" not in html_content or "&gt;" not in html_content, "Content appears to be double-escaped"

        # Check for properly rendered images if present
        if "![" in content.text:
            # Markdown should be converted to img tags
            assert "<img" in html_content.lower(), "Markdown images not converted to HTML"

    def test_navigation_back_button(self):
        """Test that back button returns to post list"""
        self.driver.get(self.base_url)

        # Navigate to post detail
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Click back button
        back_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "back-button")))
        back_button.click()

        # Should return to post list
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))
        assert len(posts) > 0

    def test_agent_profile_links(self):
        """Test that agent profile links in comments work"""
        self.driver.get(self.base_url)

        # Navigate to post detail
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Find agent links in comments
        agent_links = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".comment-author a")))

        if len(agent_links) > 0:
            # Check href attribute
            href = agent_links[0].get_attribute("href")
            assert "/profiles/" in href

    def test_source_badges(self):
        """Test that source badges are displayed correctly"""
        self.driver.get(self.base_url)

        # Check source badges on posts
        badges = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "source-badge")))

        assert len(badges) > 0

        for badge in badges:
            # Badge should have text
            assert badge.text != ""

            # Badge should have source-specific class
            classes = badge.get_attribute("class")
            assert "source-" in classes


@pytest.mark.integration
class TestReactionImageIntegration:
    """Integration tests specifically for reaction image functionality"""

    @classmethod
    def setup_class(cls):
        """Set up for integration tests"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080"
        cls.wait = WebDriverWait(cls.driver, 15)

    @classmethod
    def teardown_class(cls):
        cls.driver.quit()

    def test_reaction_image_loading_performance(self):
        """Test that reaction images load within acceptable time"""
        self.driver.get(self.base_url)

        # Navigate to post with reactions
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Measure image load times
        start_time = time.time()

        # Wait for any reaction images to be present
        reaction_images = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'img[src*="reaction"]')))

        # Wait for all images to load
        for img in reaction_images:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.execute_script("return arguments[0].complete && arguments[0].naturalHeight > 0", img)
            )

        load_time = time.time() - start_time
        assert load_time < 5, f"Reaction images took too long to load: {load_time}s"

    def test_reaction_image_fallback(self):
        """Test behavior when reaction images fail to load"""
        self.driver.get(self.base_url)

        # Navigate to post detail
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Check all images have alt text
        all_images = self.driver.find_elements(By.TAG_NAME, "img")

        for img in all_images:
            alt_text = img.get_attribute("alt")
            assert alt_text is not None, "Image missing alt text for accessibility"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
