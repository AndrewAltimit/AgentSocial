"""
Tests for responsive behavior and breakpoints in AgentSocial
Verifies that the UI adapts correctly to different screen sizes
"""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TestResponsiveBehavior:
    """Test suite for responsive design and breakpoint behavior"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080"
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up driver"""
        cls.driver.quit()

    def set_viewport_size(self, width, height, user_agent=None):
        """Set browser viewport to specific dimensions"""
        self.driver.set_window_size(width, height)

        if user_agent:
            # For user agent changes, we need to reload with new agent
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})

        time.sleep(0.5)  # Allow time for viewport change

    def test_mobile_breakpoint(self):
        """Test mobile layout (typically < 768px)"""
        print("\nTesting mobile breakpoint...")

        # Set mobile viewport
        self.set_viewport_size(375, 812)  # iPhone X dimensions

        # Use mobile user agent to ensure correct template
        mobile_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": mobile_agent})

        self.driver.get(self.base_url)
        time.sleep(2)

        # Check mobile-specific elements
        self.driver.find_element(By.TAG_NAME, "body")

        # Verify mobile layout characteristics
        container = self.driver.find_element(By.CLASS_NAME, "container")
        container_width = container.size["width"]

        # Mobile should have full-width container (minus padding)
        viewport_width = self.driver.execute_script("return window.innerWidth")
        assert container_width <= viewport_width, f"Container too wide for mobile: {container_width}px > {viewport_width}px"

        # Check that posts stack vertically
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if len(posts) >= 2:
            post1_rect = posts[0].rect
            post2_rect = posts[1].rect

            # Posts should be stacked (second post below first)
            assert post2_rect["y"] > post1_rect["y"], "Posts should stack vertically on mobile"

            # Posts should have similar widths
            width_diff = abs(post1_rect["width"] - post2_rect["width"])
            assert width_diff < 10, f"Posts should have similar widths on mobile (diff: {width_diff}px)"

        print("  ✓ Mobile layout correct")

    def test_tablet_breakpoint(self):
        """Test tablet layout (typically 768px - 1024px)"""
        print("\nTesting tablet breakpoint...")

        # Set tablet viewport
        self.set_viewport_size(768, 1024)  # iPad dimensions

        self.driver.get(self.base_url)
        time.sleep(2)

        # Check tablet-specific behavior
        container = self.driver.find_element(By.CLASS_NAME, "container")
        container_width = container.size["width"]

        # Tablet should have constrained container width
        viewport_width = self.driver.execute_script("return window.innerWidth")
        assert container_width < viewport_width, "Container should be constrained on tablet"

        # Check for appropriate spacing
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            # Posts should have reasonable width for tablet
            post_width = posts[0].size["width"]
            assert 600 <= post_width <= 800, f"Post width should be appropriate for tablet: {post_width}px"

        print("  ✓ Tablet layout correct")

    def test_desktop_breakpoint(self):
        """Test desktop layout (> 1024px)"""
        print("\nTesting desktop breakpoint...")

        # Set desktop viewport
        self.set_viewport_size(1920, 1080)

        # Use desktop user agent to ensure widescreen template
        desktop_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": desktop_agent})

        self.driver.get(self.base_url)
        time.sleep(2)

        # Check for desktop-specific elements
        # Desktop might have sidebar or wider layout
        self.driver.execute_script("return window.innerWidth")

        # Look for widescreen-specific elements
        main_content = self.driver.find_elements(By.ID, "posts-container")
        if not main_content:
            main_content = self.driver.find_elements(By.ID, "posts-list")

        if main_content:
            content_width = main_content[0].size["width"]

            # Desktop should have maximum content width
            assert content_width <= 1200, f"Content too wide for desktop: {content_width}px"

            # Should be centered with margins
            content_x = main_content[0].location["x"]
            assert content_x > 0, "Content should have left margin on desktop"

        # Check for desktop-specific controls
        view_toggle = self.driver.find_elements(By.CLASS_NAME, "view-toggle")
        assert view_toggle, "Desktop should have view toggle controls"

        print("  ✓ Desktop layout correct")

    def test_responsive_navigation(self):
        """Test navigation responsiveness across breakpoints"""
        print("\nTesting responsive navigation...")

        breakpoints = [(375, 812, "mobile"), (768, 1024, "tablet"), (1920, 1080, "desktop")]

        for width, height, device in breakpoints:
            print(f"  Testing {device} navigation ({width}x{height})...")

            self.set_viewport_size(width, height)
            self.driver.get(self.base_url)
            time.sleep(1)

            # Check header exists and is visible
            header = self.driver.find_element(By.CLASS_NAME, "header")
            assert header.is_displayed(), f"Header should be visible on {device}"

            # Check logo is accessible
            logo = self.driver.find_element(By.CLASS_NAME, "logo")
            assert logo.is_displayed(), f"Logo should be visible on {device}"

            # Check navigation links
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, ".nav-links a")

            if width < 768:
                # Mobile might have hamburger menu or simplified nav
                # Currently the app shows full nav, but we check it fits
                if nav_links:
                    nav_container = self.driver.find_element(By.CLASS_NAME, "nav-links")
                    nav_width = nav_container.size["width"]
                    assert nav_width < width, f"Navigation too wide for {device}"
            else:
                # Tablet and desktop should show full navigation
                assert len(nav_links) >= 2, f"Should have navigation links on {device}"
                for link in nav_links:
                    assert link.is_displayed(), f"Nav links should be visible on {device}"

            print(f"    ✓ {device} navigation works")

    def test_responsive_images(self):
        """Test that images scale appropriately across breakpoints"""
        print("\nTesting responsive images...")

        # Navigate to a post detail page first
        self.set_viewport_size(1920, 1080)
        self.driver.get(self.base_url)
        time.sleep(2)

        # Click first post
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            posts[0].click()
            time.sleep(2)

            breakpoints = [(375, 812, "mobile"), (768, 1024, "tablet"), (1920, 1080, "desktop")]

            for width, height, device in breakpoints:
                print(f"  Testing {device} images ({width}x{height})...")

                self.set_viewport_size(width, height)
                time.sleep(0.5)

                # Check reaction images if present
                reaction_images = self.driver.find_elements(By.CLASS_NAME, "reaction-img")

                for img in reaction_images:
                    if img.is_displayed():
                        img_width = img.size["width"]
                        img_height = img.size["height"]

                        # Images should not exceed viewport width
                        assert img_width <= width - 40, f"Image too wide for {device}: {img_width}px"

                        # Images should maintain reasonable height
                        assert img_height <= 400, f"Image too tall: {img_height}px"

                        print(f"    ✓ Reaction image sized correctly for {device}")

    def test_responsive_forms(self):
        """Test that forms adapt to different screen sizes"""
        print("\nTesting responsive forms...")

        breakpoints = [(375, 812, "mobile"), (768, 1024, "tablet"), (1920, 1080, "desktop")]

        for width, height, device in breakpoints:
            print(f"  Testing {device} forms ({width}x{height})...")

            self.set_viewport_size(width, height)

            # Go to a post detail page to test comment form
            self.driver.get(self.base_url)
            time.sleep(1)

            posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
            if posts:
                posts[0].click()
                time.sleep(1)

                # Check comment form
                comment_form = self.driver.find_elements(By.CLASS_NAME, "comment-form")
                if comment_form:
                    form_width = comment_form[0].size["width"]

                    # Form should fit within viewport
                    assert form_width <= width - 20, f"Comment form too wide for {device}"

                    # Check textarea
                    textarea = comment_form[0].find_element(By.TAG_NAME, "textarea")
                    textarea_width = textarea.size["width"]

                    # Textarea should be appropriately sized
                    if width < 768:
                        # Mobile: full width
                        assert textarea_width >= form_width * 0.9, "Textarea should be full width on mobile"
                    else:
                        # Tablet/Desktop: can have padding
                        assert textarea_width >= form_width * 0.85, "Textarea should use most of form width"

                    print(f"    ✓ Comment form responsive on {device}")

    def test_responsive_text_readability(self):
        """Test that text remains readable across different screen sizes"""
        print("\nTesting text readability...")

        breakpoints = [
            (375, 812, "mobile", 14),  # Minimum font size for mobile
            (768, 1024, "tablet", 14),
            (1920, 1080, "desktop", 14),
        ]

        for width, height, device, min_font_size in breakpoints:
            print(f"  Testing {device} text readability...")

            self.set_viewport_size(width, height)
            self.driver.get(self.base_url)
            time.sleep(1)

            # Check post titles
            titles = self.driver.find_elements(By.CLASS_NAME, "post-title")
            if titles:
                for title in titles[:3]:
                    if title.is_displayed():
                        font_size = int(title.value_of_css_property("font-size").replace("px", ""))
                        line_height = title.value_of_css_property("line-height")

                        # Font size should be readable
                        assert font_size >= min_font_size, f"Title font too small on {device}: {font_size}px"

                        # Line height should provide good readability
                        if "px" in line_height:
                            line_height_px = int(line_height.replace("px", ""))
                            assert line_height_px >= font_size * 1.2, "Line height should be at least 1.2x font size"

            # Check body text
            previews = self.driver.find_elements(By.CLASS_NAME, "post-preview")
            if previews:
                for preview in previews[:3]:
                    if preview.is_displayed():
                        font_size = int(preview.value_of_css_property("font-size").replace("px", ""))

                        # Body text should be readable
                        assert font_size >= 12, f"Body text too small on {device}: {font_size}px"

            print(f"    ✓ Text readable on {device}")

    def test_touch_target_sizes(self):
        """Test that clickable elements are appropriately sized for touch on mobile"""
        print("\nTesting touch target sizes...")

        # Set mobile viewport
        self.set_viewport_size(375, 812)
        mobile_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": mobile_agent})

        self.driver.get(self.base_url)
        time.sleep(2)

        # Minimum touch target size (44x44 pixels for iOS, 48x48 for Android)
        min_touch_size = 44

        # Check buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            if button.is_displayed():
                width = button.size["width"]
                height = button.size["height"]

                # At least one dimension should meet minimum
                assert width >= min_touch_size or height >= min_touch_size, f"Button too small for touch: {width}x{height}px"

        # Check links
        links = self.driver.find_elements(By.CSS_SELECTOR, ".nav-links a, .post-action")
        for link in links:
            if link.is_displayed():
                width = link.size["width"]
                height = link.size["height"]

                # Links should have adequate touch area
                assert width >= 30 or height >= 30, f"Link touch target too small: {width}x{height}px"

        print("  ✓ Touch targets appropriately sized")

    def test_responsive_performance(self):
        """Test that responsive changes don't break functionality"""
        print("\nTesting responsive performance...")

        # Start at desktop size
        self.set_viewport_size(1920, 1080)
        self.driver.get(self.base_url)
        time.sleep(1)

        # Get initial post count
        posts_before = len(self.driver.find_elements(By.CLASS_NAME, "post-card"))

        # Resize to mobile
        self.set_viewport_size(375, 812)
        time.sleep(1)

        # Posts should still be present
        posts_after = len(self.driver.find_elements(By.CLASS_NAME, "post-card"))
        assert posts_after == posts_before, "Content should not disappear on resize"

        # Test that view toggle still works after resize
        view_buttons = self.driver.find_elements(By.CLASS_NAME, "view-btn")
        if view_buttons and view_buttons[0].is_displayed():
            # Try clicking compact view
            compact_btn = self.driver.find_element(By.CSS_SELECTOR, "[title='Compact View']")
            compact_btn.click()
            time.sleep(0.5)

            # Verify it worked
            assert "active" in compact_btn.get_attribute("class"), "View toggle should work after resize"

        # Resize back to desktop
        self.set_viewport_size(1920, 1080)
        time.sleep(1)

        # Content should still be intact
        posts_final = len(self.driver.find_elements(By.CLASS_NAME, "post-card"))
        assert posts_final == posts_before, "Content should persist through multiple resizes"

        print("  ✓ Responsive changes maintain functionality")
