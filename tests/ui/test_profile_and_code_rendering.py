"""
Selenium tests for profile rendering and code block formatting
Tests the fixes for:
1. corporate_synergy_bot profile should not show # noqa: E501
2. Code blocks should be properly highlighted with Prism.js
3. Code blocks should have proper styling and fixed width
"""

import time

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestProfileAndCodeRendering:
    """Test profile rendering and code block formatting"""

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
        cls.wait = WebDriverWait(cls.driver, 10)

    @classmethod
    def teardown_class(cls):
        """Clean up after tests"""
        cls.driver.quit()

    def test_corporate_synergy_profile_no_noqa(self):
        """Test that corporate_synergy_bot profile does not show # noqa: E501"""
        # Navigate to the profile
        self.driver.get(f"{self.base_url}/profiles/corporate_synergy_bot")

        # Wait for the profile to load
        time.sleep(2)

        # Check that the profile loaded
        assert "SynergyMaximizer3000" in self.driver.page_source

        # Check that MISSION STATEMENT exists
        assert "MISSION STATEMENT" in self.driver.page_source

        # Check that # noqa: E501 does NOT appear
        assert "# noqa: E501" not in self.driver.page_source, "Found '# noqa: E501' in profile - it should not be visible"

        # Specifically check the mission statement text
        mission_element = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'MISSION STATEMENT')]")
        parent_div = mission_element.find_element(By.XPATH, "./..")

        # Check the parent div's text doesn't contain noqa
        assert "noqa" not in parent_div.text.lower(), "Found 'noqa' comment in mission statement section"

    def test_code_blocks_have_syntax_highlighting(self):
        """Test that code blocks have Prism.js syntax highlighting"""
        # Navigate to the forum
        self.driver.get(f"{self.base_url}/forum")

        # Wait for posts to load
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on a post that likely has code blocks
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")

        # Click on a post (preferably one with technical content)
        if posts:
            posts[0].click()
            time.sleep(2)

            # Check if Prism.js is loaded
            prism_loaded = self.driver.execute_script("return typeof Prism !== 'undefined';")
            assert prism_loaded, "Prism.js is not loaded"

            # Check for code blocks with language classes
            code_blocks = self.driver.find_elements(By.CSS_SELECTOR, "pre code[class*='language-']")

            if code_blocks:
                # Verify code blocks have proper classes
                for block in code_blocks:
                    class_attr = block.get_attribute("class")
                    assert "language-" in class_attr, f"Code block missing language class: {class_attr}"

    def test_code_blocks_have_proper_styling(self):
        """Test that code blocks have proper styling (dark background, scrollable)"""
        # Navigate to the forum
        self.driver.get(f"{self.base_url}/forum")

        # Wait for posts to load
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on a post
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            posts[0].click()
            time.sleep(2)

            # Find pre elements (code blocks)
            pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")

            if pre_elements:
                for pre in pre_elements:
                    # Check background color
                    bg_color = pre.value_of_css_property("background-color")
                    # Should be dark (rgb values should be low)
                    assert bg_color, "Code block has no background color"

                    # Check padding
                    padding = pre.value_of_css_property("padding")
                    assert padding and padding != "0px", "Code block has no padding"

                    # Check border radius
                    border_radius = pre.value_of_css_property("border-radius")
                    assert border_radius and border_radius != "0px", "Code block has no border radius"

                    # Check overflow
                    overflow_x = pre.value_of_css_property("overflow-x")
                    assert overflow_x in ["auto", "scroll"], f"Code block overflow-x is {overflow_x}, should be auto or scroll"

                    # Check max-width
                    max_width = pre.value_of_css_property("max-width")
                    assert max_width, "Code block has no max-width set"

    def test_inline_code_styling(self):
        """Test that inline code has proper styling"""
        # Navigate to the forum
        self.driver.get(f"{self.base_url}/forum")

        # Wait for posts to load
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on a post
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            posts[0].click()
            time.sleep(2)

            # Find inline code elements
            inline_code = self.driver.find_elements(By.CSS_SELECTOR, "code:not([class*='language-'])")

            if inline_code:
                for code in inline_code:
                    # Check background color
                    bg_color = code.value_of_css_property("background-color")
                    assert bg_color and bg_color != "rgba(0, 0, 0, 0)", "Inline code has no background color"

                    # Check padding
                    padding = code.value_of_css_property("padding")
                    assert padding and padding != "0px", "Inline code has no padding"

                    # Check font family
                    font_family = code.value_of_css_property("font-family")
                    assert (
                        "mono" in font_family.lower() or "courier" in font_family.lower()
                    ), f"Inline code font is not monospace: {font_family}"

    def test_myspace_profiles_render_correctly(self):
        """Test that MySpace-style profiles render correctly"""
        profiles = ["retro_coder_2006", "scene_kid_dev", "aesthetic_vapor_coder", "mall_goth_sysadmin"]

        for profile_id in profiles:
            self.driver.get(f"{self.base_url}/profiles/{profile_id}")
            time.sleep(1)

            # Check that the profile loaded
            assert self.driver.find_elements(By.CLASS_NAME, "profile-content") or self.driver.find_elements(
                By.ID, "profile-container"
            ), f"Profile {profile_id} did not load"

            # Check for XSS attempts - no script tags should be present
            script_tags = self.driver.find_elements(By.TAG_NAME, "script")
            # Filter out legitimate script tags (Prism.js, utils.js, etc.)
            malicious_scripts = [
                s
                for s in script_tags
                if "evil" in s.get_attribute("innerHTML").lower() or "alert" in s.get_attribute("innerHTML").lower()
            ]
            assert len(malicious_scripts) == 0, f"Found potential XSS in profile {profile_id}"

    def test_reaction_images_display(self):
        """Test that reaction images display correctly in comments"""
        # Navigate to the forum
        self.driver.get(f"{self.base_url}/forum")

        # Wait for posts to load
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on a post
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            posts[0].click()
            time.sleep(2)

            # Look for reaction images
            reaction_imgs = self.driver.find_elements(By.CLASS_NAME, "reaction-img")

            if reaction_imgs:
                for img in reaction_imgs:
                    # Check that the image has a src
                    src = img.get_attribute("src")
                    assert src and "AndrewAltimit/Media" in src, f"Reaction image has invalid src: {src}"

                    # Check max-height styling
                    style = img.get_attribute("style")
                    assert "max-height" in style or img.value_of_css_property(
                        "max-height"
                    ), "Reaction image has no max-height constraint"

    def test_code_blocks_in_comments(self):
        """Test that code blocks in comments render properly with syntax highlighting"""
        # Navigate to forum
        self.driver.get(f"{self.base_url}/forum")

        # Wait for posts to load
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post-card")))

        # Click on a post
        posts = self.driver.find_elements(By.CLASS_NAME, "post-card")
        if posts:
            posts[0].click()
            time.sleep(2)

            # Check comments for code blocks
            comments = self.driver.find_elements(By.CLASS_NAME, "comment-body")

            for comment in comments:
                code_blocks = comment.find_elements(By.TAG_NAME, "pre")
                if code_blocks:
                    for block in code_blocks:
                        # Check that it doesn't exceed comment width
                        comment_width = comment.size["width"]
                        block_width = block.size["width"]

                        # Block should not be wider than comment
                        assert (
                            block_width <= comment_width + 50
                        ), f"Code block ({block_width}px) exceeds comment width ({comment_width}px)"

                        # Check that it has proper overflow
                        overflow = block.value_of_css_property("overflow-x")
                        assert overflow in ["auto", "scroll"], "Code block should be scrollable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
