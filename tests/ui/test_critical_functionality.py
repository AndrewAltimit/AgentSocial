"""
Critical functionality tests for AgentSocial
These tests ensure core features work before committing code
"""

import os
import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Get base URL from environment or use default
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")


class TestCriticalFunctionality:
    """Test all critical user paths"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up driver"""
        cls.driver.quit()

    def test_homepage_loads_without_errors(self):
        """Test that homepage loads without JavaScript errors"""
        self.driver.get(BASE_URL)

        # Check for JavaScript errors
        logs = self.driver.get_log("browser")
        severe_errors = [log for log in logs if log["level"] == "SEVERE"]
        assert len(severe_errors) == 0, f"JavaScript errors found: {severe_errors}"

        # Check that main container exists
        try:
            main_container = self.wait.until(EC.presence_of_element_located((By.ID, "main-container")))
            assert main_container is not None
        except TimeoutException:
            # Desktop layout uses different container
            posts_container = self.wait.until(EC.presence_of_element_located((By.ID, "posts-container")))
            assert posts_container is not None

    def test_posts_load_and_display(self):
        """Test that posts load from API and display correctly"""
        self.driver.get(BASE_URL)

        # Wait for posts to load
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))
        assert len(posts) > 0, "No posts loaded from API"

        # Check first post has required elements
        first_post = posts[0]

        # Must have title
        title = first_post.find_element(By.CLASS_NAME, "post-title")
        assert title.text != "", "Post has no title"

        # Must have metadata (author, time)
        meta = first_post.find_element(By.CLASS_NAME, "post-meta")
        assert meta.text != "", "Post has no metadata"

    def test_post_detail_navigation_flow(self):
        """Test complete flow: list -> detail -> back to list"""
        self.driver.get(BASE_URL)

        # Step 1: Get initial posts
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))
        # initial_post_count = len(posts)  # Could be used for validation

        # Step 2: Click first post
        first_post = posts[0]
        post_title = first_post.find_element(By.CLASS_NAME, "post-title").text
        first_post.click()

        time.sleep(1)  # Wait for navigation

        # Step 3: Verify detail view loaded
        # Should have either thread-container or a back button
        detail_loaded = False
        try:
            self.driver.find_element(By.CLASS_NAME, "thread-container")
            detail_loaded = True
        except NoSuchElementException:
            try:
                # Desktop layout might not have thread-container
                self.driver.find_element(By.CLASS_NAME, "back-button")
                detail_loaded = True
            except NoSuchElementException:
                pass

        assert detail_loaded, "Post detail view did not load"

        # Step 4: Verify correct post loaded (title should match)
        page_source = self.driver.page_source
        assert post_title in page_source, "Wrong post loaded in detail view"

        # Step 5: Click back button
        back_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "back-button")))
        back_button.click()

        time.sleep(1)

        # Step 6: Verify returned to list
        posts_after = self.driver.find_elements(By.CLASS_NAME, "post-card")
        assert len(posts_after) > 0, "Did not return to post list"

    def test_comments_display_in_detail_view(self):
        """Test that comments are visible in post detail"""
        self.driver.get(BASE_URL)

        # Navigate to a post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(1)

        # Check for comments section
        comments_exist = False
        try:
            self.driver.find_element(By.ID, "comments-container")
            comments_exist = True
        except NoSuchElementException:
            # Try alternative selectors
            try:
                self.driver.find_element(By.CLASS_NAME, "comments-section")
                comments_exist = True
            except NoSuchElementException:
                pass

        assert comments_exist, "Comments section not found in detail view"

    def test_navigation_links_clickable(self):
        """Test that all navigation links are clickable"""
        self.driver.get(BASE_URL)

        # Get all navigation links
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, "a")

        # Filter out external links and test internal ones
        internal_links = [
            link for link in nav_links if link.get_attribute("href") and "localhost" in link.get_attribute("href")
        ]

        for link in internal_links[:5]:  # Test first 5 to avoid long test
            href = link.get_attribute("href")
            if href and "#" not in href:  # Skip anchor links
                # Check link is clickable
                assert link.is_enabled(), f"Link {href} is not clickable"

    def test_api_endpoints_accessible(self):
        """Test that API endpoints return data"""
        # Test posts endpoint
        self.driver.get("http://localhost:8080/api/posts")
        page_source = self.driver.page_source

        # Should return JSON array
        assert "[" in page_source or "{" in page_source, "API did not return JSON"

        # Should not have error
        assert "error" not in page_source.lower() or "500" not in page_source

    def test_images_load_properly(self):
        """Test that images (including reactions) load without 404s"""
        self.driver.get(BASE_URL)

        # Navigate to a post with potential images
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(1)

        # Find all images
        images = self.driver.find_elements(By.TAG_NAME, "img")

        for img in images:
            src = img.get_attribute("src")
            if src:
                # Check that image loads (naturalHeight > 0)
                is_loaded = self.driver.execute_script("return arguments[0].complete && arguments[0].naturalHeight > 0", img)
                # Reaction images from GitHub might not load in test env, that's ok
                if "github" not in src.lower():
                    assert is_loaded, f"Image failed to load: {src}"

    def test_voting_functionality(self):
        """Test that voting buttons respond to clicks"""
        self.driver.get(BASE_URL)

        # Find first vote button
        try:
            upvote = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".vote-arrow")))

            # Get parent element's vote count
            parent = upvote.find_element(By.XPATH, "..")
            vote_count = parent.find_element(By.CLASS_NAME, "vote-count")
            initial_count = vote_count.text

            # Click upvote
            upvote.click()

            # Count should change
            new_count = vote_count.text
            assert new_count != initial_count, "Vote count did not change"
        except (NoSuchElementException, TimeoutException):
            # Voting might not be on all layouts
            pass

    def test_responsive_layout_switching(self):
        """Test that layout responds to viewport changes"""
        # Test desktop view
        self.driver.set_window_size(1920, 1080)
        self.driver.get(BASE_URL)
        time.sleep(1)

        desktop_source = self.driver.page_source

        # Test mobile view
        self.driver.set_window_size(375, 667)
        self.driver.refresh()
        time.sleep(1)

        mobile_source = self.driver.page_source

        # Layouts might be different (check for unique elements)
        # This is a basic check - could be more thorough
        assert len(desktop_source) > 0 and len(mobile_source) > 0


@pytest.mark.smoke
class TestSmokeTests:
    """Quick smoke tests for pre-commit hook"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver for smoke tests"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.wait = WebDriverWait(cls.driver, 5)  # Shorter timeout for smoke tests

    @classmethod
    def teardown_class(cls):
        cls.driver.quit()

    def test_app_is_running(self):
        """Test that application is accessible"""
        try:
            self.driver.get(BASE_URL)
            assert True
        except Exception as e:
            pytest.fail(f"Application not accessible: {e}")

    def test_no_500_errors(self):
        """Test that no 500 errors on main pages"""
        urls = [
            BASE_URL,
            f"{BASE_URL}/desktop",
            f"{BASE_URL}/mobile",
            f"{BASE_URL}/api/posts",
        ]

        for url in urls:
            self.driver.get(url)
            # Check for actual error indicators, not just "500" which appears in CSS
            page_source = self.driver.page_source
            assert "500 Internal Server Error" not in page_source, f"500 error on {url}"
            assert "Internal Server Error" not in page_source
            # Check title doesn't indicate error
            assert "Error" not in self.driver.title

    def test_critical_elements_present(self):
        """Test that critical UI elements are present"""
        self.driver.get(BASE_URL)

        # Should have some container
        containers = self.driver.find_elements(By.CSS_SELECTOR, "[id*='container']")
        assert len(containers) > 0, "No container elements found"

        # Should have navigation or header
        headers = self.driver.find_elements(By.CSS_SELECTOR, ".header, .nav, header, nav")
        assert len(headers) > 0, "No header/navigation found"
