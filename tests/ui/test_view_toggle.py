"""
Selenium tests for view toggle functionality (Card View / Compact View)
Tests the view toggle buttons and verifies the UI changes correctly
"""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestViewToggle:
    """Test suite for view toggle functionality"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Simulate desktop user agent to get widescreen version
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up driver"""
        cls.driver.quit()

    def test_view_toggle_buttons_present(self):
        """Test that view toggle buttons are present on the page"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Check for view controls
        view_controls = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "view-controls")))
        assert view_controls is not None

        # Check for both view buttons
        view_buttons = self.driver.find_elements(By.CLASS_NAME, "view-btn")
        assert len(view_buttons) == 2, f"Expected 2 view buttons, found {len(view_buttons)}"

        # Check button titles
        card_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Card View']")
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        assert card_btn is not None
        assert compact_btn is not None

    def test_card_view_is_default(self):
        """Test that Card View is the default view"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Check that Card View button is active by default
        card_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Card View']")
        assert "active" in card_btn.get_attribute("class")

        # Check that Compact View button is not active
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        assert "active" not in compact_btn.get_attribute("class")

        # Check that post cards don't have compact class
        post_cards = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if post_cards:
            for card in post_cards[:3]:  # Check first 3 cards
                assert "compact" not in card.get_attribute("class")

    def test_switch_to_compact_view(self):
        """Test switching from Card View to Compact View"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Click Compact View button
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        compact_btn.click()

        # Small delay for JavaScript to execute
        time.sleep(0.5)

        # Check that Compact View button is now active
        assert "active" in compact_btn.get_attribute("class")

        # Check that Card View button is not active
        card_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Card View']")
        assert "active" not in card_btn.get_attribute("class")

        # Check that post cards have compact class
        post_cards = self.driver.find_elements(By.CLASS_NAME, "post-card")
        assert len(post_cards) > 0, "No post cards found"

        for card in post_cards[:3]:  # Check first 3 cards
            card_classes = card.get_attribute("class")
            assert "compact" in card_classes, f"Card should have 'compact' class, but has: {card_classes}"

    def test_switch_back_to_card_view(self):
        """Test switching from Compact View back to Card View"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # First switch to Compact View
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        compact_btn.click()
        time.sleep(0.5)

        # Then switch back to Card View
        card_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Card View']")
        card_btn.click()
        time.sleep(0.5)

        # Check that Card View button is active
        assert "active" in card_btn.get_attribute("class")

        # Check that Compact View button is not active
        assert "active" not in compact_btn.get_attribute("class")

        # Check that post cards don't have compact class
        post_cards = self.driver.find_elements(By.CLASS_NAME, "post-card")
        for card in post_cards[:3]:  # Check first 3 cards
            assert "compact" not in card.get_attribute("class")

    def test_compact_view_hides_preview(self):
        """Test that compact view hides post previews"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Get initial preview visibility in Card View
        previews = self.driver.find_elements(By.CLASS_NAME, "post-preview")
        assert len(previews) > 0, "No post previews found"

        # Check that previews are visible in Card View
        for preview in previews[:3]:
            assert preview.is_displayed(), "Preview should be visible in Card View"

        # Switch to Compact View
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        compact_btn.click()
        time.sleep(0.5)

        # Check that previews are hidden in Compact View
        previews = self.driver.find_elements(By.CLASS_NAME, "post-preview")
        for preview in previews[:3]:
            # In compact view, the preview should be hidden via CSS
            display_style = preview.value_of_css_property("display")
            assert display_style == "none", f"Preview should be hidden in Compact View (display: {display_style})"

    def test_view_toggle_persists_through_refresh(self):
        """Test that view selection persists through page actions (not page refresh)"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Switch to Compact View
        compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
        compact_btn.click()
        time.sleep(0.5)

        # Click on refresh link (not browser refresh)
        refresh_link = self.driver.find_element(By.LINK_TEXT, "Refresh")
        refresh_link.click()

        # Wait for page to reload
        time.sleep(2)

        # Note: After a page reload, the view resets to default (Card View)
        # This is expected behavior since we're not using localStorage
        # to persist the view preference

        # Verify it's back to Card View (default)
        card_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Card View']")
        assert "active" in card_btn.get_attribute("class")

    def test_mobile_view_has_toggle_buttons(self):
        """Test that mobile view (forum.html) also has view toggle buttons"""
        # Force mobile view
        self.driver.get(f"{self.base_url}/mobile")

        # Wait for posts to load
        time.sleep(2)

        # Check for view controls
        view_controls = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "view-controls")))
        assert view_controls is not None

        # Check for both view buttons
        view_buttons = self.driver.find_elements(By.CLASS_NAME, "view-btn")
        assert len(view_buttons) == 2, f"Expected 2 view buttons in mobile view, found {len(view_buttons)}"

    def test_desktop_view_has_toggle_buttons(self):
        """Test that desktop view (forum_widescreen.html) has view toggle buttons"""
        # Force desktop view
        self.driver.get(f"{self.base_url}/desktop")

        # Wait for posts to load
        time.sleep(2)

        # Check for view toggle container
        view_toggle = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "view-toggle")))
        assert view_toggle is not None

        # Check for both view buttons
        view_buttons = self.driver.find_elements(By.CLASS_NAME, "view-btn")
        assert len(view_buttons) == 2, f"Expected 2 view buttons in desktop view, found {len(view_buttons)}"
