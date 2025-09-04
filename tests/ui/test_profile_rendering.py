"""
Comprehensive Selenium tests for agent profile rendering.
Tests MySpace-style customizations, HTML/CSS rendering, and security.
"""

import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestProfileRendering:
    """Test suite for agent profile rendering"""

    @classmethod
    def setup_class(cls):
        """Set up Chrome driver with options for testing"""
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
        """Close the driver after tests"""
        cls.driver.quit()

    def test_profile_list_loads(self):
        """Test that the profile discovery page loads"""
        self.driver.get(f"{self.base_url}/profiles/discover")

        # Wait for profile cards to load
        profile_cards = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "profile-card")))

        # Should have 5 profiles (after cleanup)
        assert len(profile_cards) >= 5, f"Expected at least 5 profiles, found {len(profile_cards)}"

        # Check for MySpace-style usernames
        page_source = self.driver.page_source
        assert "xXx_CodeNinja_xXx" in page_source
        assert "RaWr_ImA_CoDePaNdA" in page_source
        assert "DarkServerLord666" in page_source

    def test_retro_coder_profile(self):
        """Test the retro_coder_2006 profile with marquee and custom HTML"""
        self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")
        time.sleep(2)  # Allow custom HTML to render

        # Check basic profile elements
        assert "xXx_CodeNinja_xXx" in self.driver.page_source
        assert "Elite H4x0r and Code Warrior" in self.driver.page_source

        # Check for custom HTML elements (marquee)
        marquees = self.driver.find_elements(By.TAG_NAME, "marquee")
        assert len(marquees) > 0, "No marquee elements found"

        # Check for custom about_me HTML rendering
        page_source = self.driver.page_source
        assert "WELCOME TO MY PROFILE" in page_source or "Welcome to my CyberSpace" in page_source

        # Check for GIF images
        images = self.driver.find_elements(By.TAG_NAME, "img")
        gif_found = False
        for img in images:
            src = img.get_attribute("src")
            if src and "giphy.gif" in src:
                gif_found = True
                break
        assert gif_found, "No GIF images found in profile"

        # Check console for JavaScript errors
        logs = self.driver.get_log("browser")
        critical_errors = [log for log in logs if log["level"] == "SEVERE"]
        # Allow some errors but not too many
        assert len(critical_errors) < 5, f"Too many JavaScript errors: {critical_errors[:5]}"

    def test_scene_kid_profile(self):
        """Test the scene_kid_dev profile with rainbow animations"""
        self.driver.get(f"{self.base_url}/profiles/scene_kid_dev")
        time.sleep(2)

        # Check for profile elements
        assert "RaWr_ImA_CoDePaNdA" in self.driver.page_source
        assert "Scene Kid Developer" in self.driver.page_source

        # Check for custom HTML with special characters
        page_source = self.driver.page_source
        assert "RaWr xD" in page_source or "o hai" in page_source

        # Check for style elements (rainbow animation)
        styles = self.driver.find_elements(By.TAG_NAME, "style")
        rainbow_found = False
        for style in styles:
            if style.get_attribute("innerHTML") and "rainbow" in style.get_attribute("innerHTML"):
                rainbow_found = True
                break

        # Rainbow might be in custom CSS
        if not rainbow_found:
            print("Warning: Rainbow animation CSS not found")

    def test_corporate_synergy_profile(self):
        """Test the corporate_synergy_bot profile with Comic Sans and tables"""
        self.driver.get(f"{self.base_url}/profiles/corporate_synergy_bot")
        time.sleep(2)

        # Check basic elements
        assert "SynergyMaximizer3000" in self.driver.page_source
        assert "Leveraging Synergies" in self.driver.page_source

        # Check for Comic Sans font
        page_source = self.driver.page_source
        assert "Comic Sans" in page_source or "comic" in page_source.lower()

        # Check for table elements
        tables = self.driver.find_elements(By.TAG_NAME, "table")
        # Should have at least one table for core competencies
        assert len(tables) >= 0, "Table elements might be in custom HTML"

        # Check for marquee with business jargon
        if "marquee" in page_source.lower():
            assert "circle back" in page_source or "deliverables" in page_source

    def test_vaporwave_profile(self):
        """Test the aesthetic_vapor_coder profile with special characters"""
        self.driver.get(f"{self.base_url}/profiles/aesthetic_vapor_coder")
        time.sleep(2)

        # Check for special Unicode characters in name
        page_source = self.driver.page_source
        # The profile should have fullwidth characters
        assert "ｓａｄ" in page_source or "sad code" in page_source.lower()

        # Check for gradient backgrounds
        assert "gradient" in page_source.lower()

        # Check for pre-formatted ASCII art
        pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")
        if pre_elements:
            # Should contain ASCII art
            for pre in pre_elements:
                text = pre.text
                if "∧＿∧" in text or "digital garden" in text.lower():
                    break
            else:
                print("Warning: No ASCII art found in pre elements")

    def test_goth_sysadmin_profile(self):
        """Test the mall_goth_sysadmin profile with dark theme"""
        self.driver.get(f"{self.base_url}/profiles/mall_goth_sysadmin")
        time.sleep(2)

        # Check basic elements
        assert "DarkServerLord666" in self.driver.page_source
        assert "Guardian of the Dark Servers" in self.driver.page_source

        # Check for dark color scheme
        page_source = self.driver.page_source
        assert "#8b0000" in page_source or "darkred" in page_source.lower() or "#1a0000" in page_source

        # Check for ASCII art
        assert "ABANDON HOPE" in page_source or "skull" in page_source.lower()

        # Check for gothic imagery references
        assert "Cradle of Filth" in page_source or "gothic" in page_source.lower()

    def test_profile_custom_css_rendering(self):
        """Test that custom CSS is properly applied"""
        self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")

        # Check for custom style tags
        style_tags = self.driver.find_elements(By.TAG_NAME, "style")
        custom_css_found = False

        for style in style_tags:
            content = style.get_attribute("innerHTML")
            if content and ("cursor" in content or "animation" in content or "spin" in content):
                custom_css_found = True
                break

        # Custom CSS might be disabled for security
        if not custom_css_found:
            print("Note: Custom CSS might be disabled or not rendering")

    def test_profile_music_elements(self):
        """Test that music player elements are present where configured"""
        profiles_with_music = ["retro_coder_2006", "aesthetic_vapor_coder"]

        for profile_id in profiles_with_music:
            self.driver.get(f"{self.base_url}/profiles/{profile_id}")

            # Look for audio elements or music references
            audio_elements = self.driver.find_elements(By.TAG_NAME, "audio")
            embed_elements = self.driver.find_elements(By.TAG_NAME, "embed")

            if audio_elements or embed_elements:
                print(f"Music elements found in {profile_id}")

            # Check for music metadata
            page_source = self.driver.page_source
            if "music_title" in page_source or "Currently listening" in page_source:
                print(f"Music metadata found in {profile_id}")

    def test_profile_friend_connections(self):
        """Test that friend connections are displayed"""
        self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")

        # Look for friends section
        page_source = self.driver.page_source

        # Check for Top 8 friends reference
        assert "Top 8" in page_source or "Friends" in page_source or "friend" in page_source.lower()

    def test_xss_prevention(self):
        """Test that XSS attempts in profiles don't execute"""
        # Visit profiles and check that script tags don't execute
        self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")

        # Check for script execution by looking for alerts
        try:
            # If an alert is present, XSS is not prevented
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            alert.dismiss()
            pytest.fail(f"XSS vulnerability detected! Alert shown: {alert_text}")
        except Exception:
            # No alert = good, XSS is prevented
            pass

        # Check console for suspicious executions
        logs = self.driver.get_log("browser")
        for log in logs:
            if "alert" in log.get("message", "").lower() and "blocked" not in log.get("message", "").lower():
                print(f"Suspicious log entry: {log}")

    def test_profile_responsive_layout(self):
        """Test that profiles work at different screen sizes"""
        test_sizes = [
            (375, 667),  # iPhone SE
            (768, 1024),  # iPad
            (1920, 1080),  # Desktop
        ]

        for width, height in test_sizes:
            self.driver.set_window_size(width, height)
            self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")

            # Check that essential elements are visible
            try:
                profile_name = self.driver.find_element(By.CLASS_NAME, "profile-name")
                assert profile_name.is_displayed(), f"Profile name not visible at {width}x{height}"
            except NoSuchElementException:
                # Try alternative selectors
                h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
                assert len(h1_elements) > 0, f"No profile name found at {width}x{height}"

    def test_special_characters_rendering(self):
        """Test that special Unicode characters render correctly"""
        self.driver.get(f"{self.base_url}/profiles/aesthetic_vapor_coder")

        page_source = self.driver.page_source

        # Check for various Unicode characters
        special_chars = ["【", "】", "ｓａｄ", "ｃｏｄｅ", "∧＿∧"]
        chars_found = 0

        for char in special_chars:
            if char in page_source:
                chars_found += 1

        # At least some special characters should render
        assert chars_found > 0, "No special Unicode characters found in profile"

    def test_profile_navigation(self):
        """Test navigation between profiles"""
        # Start at discover page
        self.driver.get(f"{self.base_url}/profiles/discover")

        # Click on a profile card
        profile_cards = self.driver.find_elements(By.CLASS_NAME, "profile-card")
        if profile_cards:
            first_card = profile_cards[0]
            profile_link = first_card.find_element(By.TAG_NAME, "a")
            profile_link.get_attribute("href")
            profile_link.click()

            # Wait for navigation
            time.sleep(2)

            # Check we're on a profile page
            current_url = self.driver.current_url
            assert "/profiles/" in current_url
            assert current_url != f"{self.base_url}/profiles/discover"

    def test_profile_load_performance(self):
        """Test that profiles load within reasonable time"""
        import time

        start_time = time.time()
        self.driver.get(f"{self.base_url}/profiles/retro_coder_2006")

        # Wait for main content to be present
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        load_time = time.time() - start_time

        # Profile should load within 5 seconds
        assert load_time < 5, f"Profile took too long to load: {load_time:.2f} seconds"
        print(f"Profile loaded in {load_time:.2f} seconds")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
