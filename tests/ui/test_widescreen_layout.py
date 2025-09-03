"""
Selenium UI tests for AgentSocial Widescreen Desktop Layout
Tests the 3-column layout, navigation, and all interactive elements
"""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestWidescreenLayout:
    """Test suite for widescreen desktop layout functionality"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with desktop viewport"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080/desktop"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up driver"""
        cls.driver.quit()

    def test_three_column_layout(self):
        """Test that three-column layout is present on desktop"""
        self.driver.get(self.base_url)

        # Check for all three columns
        left_sidebar = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "left-sidebar")))
        main_content = self.driver.find_element(By.CLASS_NAME, "main-content")
        right_sidebar = self.driver.find_element(By.CLASS_NAME, "right-sidebar")

        assert left_sidebar.is_displayed()
        assert main_content.is_displayed()
        assert right_sidebar.is_displayed()

        # Check that columns are properly positioned
        left_x = left_sidebar.location["x"]
        main_x = main_content.location["x"]
        right_x = right_sidebar.location["x"]

        assert left_x < main_x < right_x, "Columns not in correct order"

    def test_left_sidebar_navigation_links(self):
        """Test that left sidebar navigation links work"""
        self.driver.get(self.base_url)

        # Test feed navigation links
        nav_links = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".left-sidebar .nav-item")))

        # Test Home link
        home_link = None
        for link in nav_links:
            if "Home" in link.text:
                home_link = link
                break

        assert home_link is not None, "Home link not found"
        assert "active" in home_link.get_attribute("class")

        # Test Popular link
        popular_link = None
        for link in nav_links:
            if "Popular" in link.text:
                popular_link = link
                break

        if popular_link:
            popular_link.click()
            time.sleep(1)  # Wait for content to load

            # Check that Popular is now active
            assert "active" in popular_link.get_attribute("class")

            # Check that posts are loaded
            posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
            assert len(posts) > 0, "No posts loaded after clicking Popular"

    def test_post_click_navigation(self):
        """Test that clicking a post loads the detail view"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        posts = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "post-card")))
        assert len(posts) > 0, "No posts found"

        # Get first post title
        first_post = posts[0]
        post_title = first_post.find_element(By.CLASS_NAME, "post-title").text

        # Click the post
        first_post.click()

        # Wait for detail view to load
        time.sleep(1)

        # Check for back button
        back_button = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "back-button")))
        assert back_button.is_displayed()

        # Check that post title is displayed in detail view
        detail_title = self.driver.find_element(By.CSS_SELECTOR, ".post-main h2")
        assert post_title in detail_title.text

        # Check that comments section is visible
        comments_container = self.driver.find_element(By.ID, "comments-container")
        assert comments_container is not None

    def test_back_button_functionality(self):
        """Test that back button returns to post list"""
        self.driver.get(self.base_url)

        # Navigate to a post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Click back button
        back_button = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "back-button")))
        back_button.click()

        time.sleep(1)

        # Should see post list again
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        assert len(posts) > 0, "Post list not restored after back button"

    def test_sort_buttons(self):
        """Test that sort buttons change post order"""
        self.driver.get(self.base_url)

        # Get sort buttons
        sort_buttons = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "sort-btn")))

        # Test New sort
        new_btn = None
        for btn in sort_buttons:
            if "New" in btn.text:
                new_btn = btn
                break

        if new_btn:
            new_btn.click()
            time.sleep(1)

            # Check that New button is active
            assert "active" in new_btn.get_attribute("class")

            # Posts should still be loaded
            posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
            assert len(posts) > 0

    def test_voting_buttons(self):
        """Test that voting buttons work on posts"""
        self.driver.get(self.base_url)

        # Get first post
        first_post = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Find vote count and upvote button
        vote_count = first_post.find_element(By.CLASS_NAME, "vote-count")
        initial_count = int(vote_count.text)

        upvote = first_post.find_element(By.CSS_SELECTOR, ".vote-arrow:first-child")

        # Click upvote
        upvote.click()
        time.sleep(0.5)

        # Check that count increased
        new_count = int(vote_count.text)
        assert new_count == initial_count + 1, "Vote count did not increase"

    def test_right_sidebar_widgets(self):
        """Test that right sidebar widgets are present"""
        self.driver.get(self.base_url)

        right_sidebar = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "right-sidebar")))

        # Check for trending topics
        trending = right_sidebar.find_element(By.ID, "trending-topics")
        assert trending is not None

        # Check for top agents
        top_agents = right_sidebar.find_element(By.ID, "top-agents")
        assert top_agents is not None

        # Check for recent activity
        activity = right_sidebar.find_element(By.ID, "recent-activity")
        assert activity is not None

        # Check for stats
        stats = right_sidebar.find_element(By.CLASS_NAME, "stats-grid")
        assert stats is not None

    def test_create_post_button(self):
        """Test create post button is visible and clickable"""
        self.driver.get(self.base_url)

        create_btn = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "create-post-btn")))
        assert create_btn.is_displayed()
        assert create_btn.is_enabled()

        # Check button text
        assert "Create New Post" in create_btn.text

    def test_reaction_images_in_comments(self):
        """Test that reaction images render in comment detail view"""
        self.driver.get(self.base_url)

        # Navigate to first post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(1)

        # Look for any images in comments
        comment_images = self.driver.find_elements(By.CSS_SELECTOR, "#comments-container img")

        if len(comment_images) > 0:
            for img in comment_images:
                # Check that images have proper src
                src = img.get_attribute("src")
                assert src is not None and src != "", "Image has no source"

                # Check sizing for reaction images
                if "reaction" in src:
                    style = img.get_attribute("style")
                    assert "max-height" in style, "Reaction image missing max-height"

    def test_responsive_viewport_1400px(self):
        """Test that layout is correct at 1400px viewport"""
        self.driver.set_window_size(1400, 900)
        self.driver.get(self.base_url)

        # All three columns should be visible
        left_sidebar = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "left-sidebar")))
        right_sidebar = self.driver.find_element(By.CLASS_NAME, "right-sidebar")

        assert left_sidebar.is_displayed()
        assert right_sidebar.is_displayed()


class TestMobileLayout:
    """Test suite for mobile layout"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with mobile viewport"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=375,667")  # iPhone SE size

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080/mobile"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        cls.driver.quit()

    def test_mobile_single_column(self):
        """Test that mobile view has single column layout"""
        self.driver.get(self.base_url)

        # Main container should exist
        container = self.wait.until(EC.presence_of_element_located((By.ID, "main-container")))
        assert container is not None

        # Check that posts are stacked vertically
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if len(posts) >= 2:
            post1_y = posts[0].location["y"]
            post2_y = posts[1].location["y"]
            assert post2_y > post1_y, "Posts not stacked vertically"

    def test_mobile_post_navigation(self):
        """Test post navigation works on mobile"""
        self.driver.get(self.base_url)

        # Click first post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Should show post detail
        thread_container = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "thread-container")))
        assert thread_container is not None


@pytest.mark.integration
class TestCrossBrowserCompatibility:
    """Test cross-browser compatibility"""

    def test_layout_detection(self):
        """Test that layout detection works correctly"""
        # This would test with different user agents
        # Implementation depends on browser driver availability
        pass

    def test_navigation_consistency(self):
        """Test that navigation works consistently across layouts"""
        # Test that same content is accessible from both layouts
        pass
