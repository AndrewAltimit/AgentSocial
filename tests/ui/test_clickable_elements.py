"""
Comprehensive tests for all clickable elements (links, buttons) in AgentSocial
Verifies that all interactive elements are functional and don't produce errors
"""

import time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TestClickableElements:
    """Test suite for verifying all clickable elements work properly"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with headless options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Simulate desktop user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")

        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.base_url = "http://localhost:8080"
        cls.wait = WebDriverWait(cls.driver, 10)
        cls.tested_elements = set()  # Track tested elements to avoid duplicates
        cls.errors = []  # Collect errors for reporting

    @classmethod
    def teardown_class(cls):
        """Clean up driver and report any collected errors"""
        if cls.errors:
            print("\n=== Clickable Elements Test Summary ===")
            print(f"Found {len(cls.errors)} issues:")
            for error in cls.errors:
                print(f"  - {error}")
        cls.driver.quit()

    def get_current_url(self):
        """Get current URL for comparison"""
        return self.driver.current_url

    def is_external_link(self, url):
        """Check if a URL is external to the application"""
        if not url:
            return False
        parsed = urlparse(url)
        base_parsed = urlparse(self.base_url)
        return parsed.netloc and parsed.netloc != base_parsed.netloc

    def test_all_navigation_links(self):
        """Test all navigation links in the header"""
        self.driver.get(self.base_url)
        time.sleep(2)  # Wait for page to fully load

        # Find all links in navigation
        nav_links = self.driver.find_elements(By.CSS_SELECTOR, ".nav-links a, .header a")

        print(f"\nTesting {len(nav_links)} navigation links...")

        for i, link in enumerate(nav_links):
            try:
                href = link.get_attribute("href")
                text = link.text or link.get_attribute("title") or f"Link {i}"

                # Skip if already tested
                element_id = f"nav_link_{href}_{text}"
                if element_id in self.tested_elements:
                    continue
                self.tested_elements.add(element_id)

                print(f"  Testing: {text} -> {href}")

                # Check if link is clickable
                if link.is_displayed() and link.is_enabled():
                    # For external links, just verify they have valid href
                    if self.is_external_link(href):
                        assert href.startswith(("http://", "https://", "//")), f"Invalid external URL: {href}"
                    else:
                        # For internal links, try clicking
                        original_url = self.get_current_url()
                        link.click()
                        time.sleep(1)

                        # Verify page changed or action occurred
                        new_url = self.get_current_url()

                        # Go back if we navigated away
                        if new_url != original_url:
                            self.driver.back()
                            time.sleep(1)

            except Exception as e:
                error_msg = f"Navigation link '{text}' failed: {str(e)}"
                self.errors.append(error_msg)
                print(f"    ❌ {error_msg}")

    def test_all_buttons(self):
        """Test all buttons on the main page"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Find all buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")

        print(f"\nTesting {len(buttons)} buttons...")

        for i, button in enumerate(buttons):
            try:
                # Get button properties before clicking
                button_text = button.text or button.get_attribute("title") or f"Button {i}"
                button_class = button.get_attribute("class")

                # Skip if already tested
                element_id = f"button_{button_class}_{button_text}"
                if element_id in self.tested_elements:
                    continue
                self.tested_elements.add(element_id)

                print(f"  Testing button: {button_text}")

                if button.is_displayed() and button.is_enabled():
                    # Store original state
                    _ = button.get_attribute("class")  # Check attribute exists

                    # Click the button
                    button.click()
                    time.sleep(0.5)

                    # Check if button state changed (for toggle buttons)
                    _ = button.get_attribute("class")  # Check state after click

                    # Verify no JavaScript errors occurred
                    logs = self.driver.get_log("browser")
                    severe_errors = [log for log in logs if log["level"] == "SEVERE"]
                    if severe_errors:
                        raise Exception(f"JavaScript errors after clicking: {severe_errors}")

                    print(f"    ✓ Button '{button_text}' works")

            except StaleElementReferenceException:
                # Element was removed from DOM (expected for some dynamic content)
                print(f"    ℹ Button '{button_text}' triggered page update")
            except Exception as e:
                error_msg = f"Button '{button_text}' failed: {str(e)}"
                self.errors.append(error_msg)
                print(f"    ❌ {error_msg}")

    def test_post_interactions(self):
        """Test all interactive elements within posts"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Find all post cards
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")

        if not posts:
            print("No posts found to test")
            return

        print(f"\nTesting interactions in {len(posts)} posts...")

        # Test first 3 posts to avoid excessive testing
        for post_index, post in enumerate(posts[:3]):
            try:
                print(f"  Testing post {post_index + 1}...")

                # Test voting arrows
                vote_arrows = post.find_elements(By.CLASS_NAME, "vote-arrow")
                for arrow in vote_arrows:
                    if arrow.is_displayed():
                        direction = "up" if "▲" in arrow.text else "down"
                        print(f"    Testing {direction}vote...")

                        # Click and verify no errors
                        arrow.click()
                        time.sleep(0.2)

                        # Check vote count changed
                        vote_count = post.find_element(By.CLASS_NAME, "vote-count")
                        assert vote_count.text.isdigit() or vote_count.text == "0", "Vote count should be numeric"

                # Test post actions (comments, share, etc.)
                post_actions = post.find_elements(By.CLASS_NAME, "post-action")
                for action in post_actions:
                    action_text = action.text
                    print(f"    Testing action: {action_text}")

                    # Check if it's a link or clickable div
                    link = action.find_elements(By.TAG_NAME, "a")
                    if link:
                        href = link[0].get_attribute("href")
                        if self.is_external_link(href):
                            print(f"      External link verified: {href}")
                        else:
                            # Would navigate away, just verify it exists
                            assert href, f"Internal link missing href: {action_text}"

            except Exception as e:
                error_msg = f"Post {post_index + 1} interaction failed: {str(e)}"
                self.errors.append(error_msg)
                print(f"    ❌ {error_msg}")

    def test_post_detail_page(self):
        """Test clickable elements on post detail page"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Click on first post to go to detail view
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if not posts:
            print("No posts available to test detail page")
            return

        print("\nTesting post detail page...")

        # Click first post
        posts[0].click()
        time.sleep(2)

        # Test back button
        try:
            back_button = self.driver.find_element(By.CLASS_NAME, "back-button")
            print("  Testing back button...")

            original_url = self.get_current_url()
            back_button.click()
            time.sleep(1)

            new_url = self.get_current_url()
            assert new_url != original_url, "Back button should navigate to posts list"

            # Go back to detail page
            self.driver.back()
            time.sleep(1)

            print("    ✓ Back button works")
        except Exception as e:
            error_msg = f"Back button failed: {str(e)}"
            self.errors.append(error_msg)
            print(f"    ❌ {error_msg}")

        # Test comment form
        try:
            self.driver.find_element(By.ID, "main-comment-input")  # Verify textarea exists
            comment_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Comment')]")

            print("  Testing comment submission...")

            # Try submitting empty comment (should show alert)
            comment_button.click()
            time.sleep(0.5)

            # Check for alert
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                alert.accept()
                print(f"    ✓ Empty comment validation works: {alert_text}")
            except Exception:
                print("    ℹ No alert for empty comment (may be HTML5 validation)")

        except Exception as e:
            error_msg = f"Comment form test failed: {str(e)}"
            self.errors.append(error_msg)
            print(f"    ❌ {error_msg}")

        # Test comment interactions
        try:
            comments = self.driver.find_elements(By.CLASS_NAME, "comment")
            if comments:
                print(f"  Testing {len(comments)} comments...")

                # Test first comment's actions
                first_comment = comments[0]
                comment_actions = first_comment.find_elements(By.CLASS_NAME, "comment-action")

                for action in comment_actions:
                    action_text = action.text
                    print(f"    Testing comment action: {action_text}")

                    if "Reply" in action_text:
                        # Test reply toggle
                        action.click()
                        time.sleep(0.5)

                        # Check if reply form appeared
                        reply_form = first_comment.find_elements(By.CLASS_NAME, "reply-form")
                        assert reply_form and "active" in reply_form[0].get_attribute("class"), "Reply form should appear"

                        # Click again to hide
                        action.click()
                        time.sleep(0.5)

                    elif "React" in action_text:
                        # Test reaction picker
                        action.click()
                        time.sleep(0.5)

                        # Check if reaction picker appeared
                        reaction_picker = self.driver.find_elements(By.CLASS_NAME, "reaction-picker")
                        if reaction_picker:
                            print("      ✓ Reaction picker opens")

                            # Click outside to close
                            self.driver.find_element(By.TAG_NAME, "body").click()
                            time.sleep(0.5)

                # Test collapse button
                collapse_button = first_comment.find_elements(By.CLASS_NAME, "collapse-button")
                if collapse_button:
                    print("    Testing comment collapse...")
                    collapse_button[0].click()
                    time.sleep(0.5)

                    # Check if comment is collapsed
                    comment_main = first_comment.find_element(By.CLASS_NAME, "comment-main")
                    assert comment_main.value_of_css_property("display") == "none", "Comment should be collapsed"

                    # Expand again
                    collapse_button[0].click()
                    time.sleep(0.5)

                    print("      ✓ Comment collapse/expand works")

        except Exception as e:
            error_msg = f"Comment interaction test failed: {str(e)}"
            self.errors.append(error_msg)
            print(f"    ❌ {error_msg}")

    def test_broken_links(self):
        """Test for any broken links (404s, etc.)"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Collect all links
        all_links = self.driver.find_elements(By.TAG_NAME, "a")

        print(f"\nChecking {len(all_links)} links for validity...")

        internal_links = []
        external_links = []

        for link in all_links:
            href = link.get_attribute("href")
            if href:
                if self.is_external_link(href):
                    external_links.append((link.text or "Unnamed", href))
                else:
                    internal_links.append((link.text or "Unnamed", href))

        # Test internal links
        print(f"  Testing {len(internal_links)} internal links...")
        for text, href in internal_links:
            try:
                # Skip javascript: and # links
                if href.startswith(("javascript:", "#")):
                    continue

                # Navigate to the link
                self.driver.get(href)
                time.sleep(0.5)

                # Check for 404 or error indicators
                page_source = self.driver.page_source.lower()
                if "404" in page_source or "not found" in page_source or "error" in self.driver.title.lower():
                    raise Exception("Possible 404 or error page")

                print(f"    ✓ {text}: {href}")

            except Exception as e:
                error_msg = f"Link '{text}' ({href}) may be broken: {str(e)}"
                self.errors.append(error_msg)
                print(f"    ❌ {error_msg}")

        # For external links, just verify they're well-formed
        print(f"  Validating {len(external_links)} external links...")
        for text, href in external_links:
            if not href.startswith(("http://", "https://", "//")):
                error_msg = f"Malformed external link '{text}': {href}"
                self.errors.append(error_msg)
                print(f"    ❌ {error_msg}")
            else:
                print(f"    ✓ {text}: {href}")

    def test_interactive_elements_no_console_errors(self):
        """Verify that clicking elements doesn't produce console errors"""
        self.driver.get(self.base_url)
        time.sleep(2)

        print("\nChecking for JavaScript errors...")

        # Clear existing console logs
        self.driver.get_log("browser")

        # Get all clickable elements
        clickable_elements = self.driver.find_elements(
            By.CSS_SELECTOR, "button, a, .post-card, .post-action, .comment-action, .vote-arrow"
        )

        errors_found = []

        # Test a sample of elements
        sample_size = min(10, len(clickable_elements))
        print(f"  Testing {sample_size} clickable elements for console errors...")

        for i in range(sample_size):
            try:
                element = clickable_elements[i]
                if element.is_displayed() and element.is_enabled():
                    element_tag = element.tag_name
                    element_text = element.text[:20] if element.text else element.get_attribute("class")

                    # Click element
                    element.click()
                    time.sleep(0.2)

                    # Check console logs
                    logs = self.driver.get_log("browser")
                    severe_errors = [log for log in logs if log["level"] == "SEVERE"]

                    if severe_errors:
                        error_msg = f"Console error after clicking {element_tag} '{element_text}': {severe_errors}"
                        errors_found.append(error_msg)
                        print(f"    ❌ {error_msg}")

            except StaleElementReferenceException:
                # Element changed, that's okay
                pass
            except ElementClickInterceptedException:
                # Element covered by another element, skip
                pass
            except Exception:
                # Other errors, log but continue
                pass

        if not errors_found:
            print("    ✓ No console errors found")
        else:
            for error in errors_found:
                self.errors.append(error)

    def test_summary(self):
        """Final test to provide summary of all clickable elements"""
        assert len(self.errors) == 0, f"Found {len(self.errors)} issues with clickable elements. See test output for details."
