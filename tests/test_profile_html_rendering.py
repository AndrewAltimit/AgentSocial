"""
Test profile HTML rendering using requests (no Selenium needed).
Verifies that custom HTML/CSS from profiles is properly rendered in the template.
"""

import pytest
import requests
from bs4 import BeautifulSoup


class TestProfileHTMLRendering:
    """Test profile HTML rendering without Selenium"""

    base_url = "http://localhost:8080"

    def test_profile_list_accessible(self):
        """Test that profile discovery page loads"""
        response = requests.get(f"{self.base_url}/profiles/discover")
        assert response.status_code == 200

        # Check for profile cards
        soup = BeautifulSoup(response.text, "html.parser")
        profile_cards = soup.find_all(class_="profile-card")
        assert len(profile_cards) >= 5, f"Expected at least 5 profiles, found {len(profile_cards)}"

        # Check for MySpace usernames
        assert "xXx_CodeNinja_xXx" in response.text
        assert "RaWr_ImA_CoDePaNdA" in response.text
        assert "DarkServerLord666" in response.text

    def test_retro_coder_profile_html(self):
        """Test retro_coder_2006 profile renders custom HTML"""
        response = requests.get(f"{self.base_url}/profiles/retro_coder_2006")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, "html.parser")
        html_content = response.text

        # Check basic profile info
        assert "xXx_CodeNinja_xXx" in html_content
        assert "Elite H4x0r and Code Warrior" in html_content

        # Check for marquee elements (custom HTML)
        marquees = soup.find_all("marquee")
        assert len(marquees) > 0, "No marquee elements found - custom HTML not rendering"

        # Check for custom HTML content
        assert "WELCOME TO MY PROFILE" in html_content or "Welcome to my CyberSpace" in html_content

        # Check for GIF images
        images = soup.find_all("img")
        gif_found = any("giphy.gif" in img.get("src", "") for img in images)
        assert gif_found, "No GIF images found in profile"

        # Verify no custom CSS from database (custom_css field removed)
        # All styling should come from template CSS, not database
        style_tags = soup.find_all("style")

        # Check that we have template styles
        assert len(style_tags) > 0, "No style tags found - template CSS missing"

        # Verify template animations are present (from template, not database)
        css_found = any("cursor" in str(style) or "spin" in str(style) or "@keyframes" in str(style) for style in style_tags)
        assert css_found, "Template animations not found in profile"

    def test_scene_kid_profile_html(self):
        """Test scene_kid_dev profile renders with animations"""
        response = requests.get(f"{self.base_url}/profiles/scene_kid_dev")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(response.text, "html.parser")

        # Check profile elements
        assert "RaWr_ImA_CoDePaNdA" in html_content
        assert "Scene Kid Developer" in html_content

        # Check for scene kid text
        assert "RaWr xD" in html_content or "o hai" in html_content

        # Check for rainbow CSS (from template, not database)
        style_tags = soup.find_all("style")
        rainbow_found = any("rainbow" in str(style) or "@keyframes" in str(style) for style in style_tags)
        assert rainbow_found, "Rainbow animation CSS not found in template"

    def test_corporate_synergy_profile_html(self):
        """Test corporate_synergy_bot profile with Comic Sans"""
        response = requests.get(f"{self.base_url}/profiles/corporate_synergy_bot")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(response.text, "html.parser")

        # Check basic elements
        assert "SynergyMaximizer3000" in html_content
        assert "Leveraging Synergies" in html_content

        # Check for Comic Sans
        assert "Comic Sans" in html_content or "comic" in html_content.lower()

        # Check for business jargon
        assert "synergy" in html_content.lower()
        assert "deliverables" in html_content or "circle back" in html_content

        # Check for table elements
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables in corporate profile")

    def test_vaporwave_profile_html(self):
        """Test aesthetic_vapor_coder profile with special characters"""
        response = requests.get(f"{self.base_url}/profiles/aesthetic_vapor_coder")
        assert response.status_code == 200

        html_content = response.text
        soup = BeautifulSoup(response.text, "html.parser")

        # Check for fullwidth characters
        assert "ｓａｄ" in html_content or "sad code" in html_content.lower()

        # Check for gradient backgrounds
        assert "gradient" in html_content.lower()

        # Check for ASCII art
        pre_elements = soup.find_all("pre")
        ascii_art_found = any("∧＿∧" in str(pre) or "digital garden" in str(pre).lower() for pre in pre_elements)
        if ascii_art_found:
            print("ASCII art found in vaporwave profile")

    def test_goth_sysadmin_profile_html(self):
        """Test mall_goth_sysadmin profile with dark theme"""
        response = requests.get(f"{self.base_url}/profiles/mall_goth_sysadmin")
        assert response.status_code == 200

        html_content = response.text

        # Check basic elements
        assert "DarkServerLord666" in html_content
        assert "Guardian of the Dark Servers" in html_content

        # Check for dark colors
        assert "#8b0000" in html_content or "darkred" in html_content.lower() or "#1a0000" in html_content

        # Check for gothic content
        assert "ABANDON HOPE" in html_content or "skull" in html_content.lower()
        assert "Cradle of Filth" in html_content or "gothic" in html_content.lower()

    def test_no_xss_in_profiles(self):
        """Verify no script tags execute in profiles"""
        # Test all profiles for XSS prevention
        profiles = [
            "retro_coder_2006",
            "scene_kid_dev",
            "corporate_synergy_bot",
            "aesthetic_vapor_coder",
            "mall_goth_sysadmin",
        ]

        for profile_id in profiles:
            response = requests.get(f"{self.base_url}/profiles/{profile_id}")
            assert response.status_code == 200

            # Check that script tags are escaped or removed
            # Raw <script> tags should not be in the output
            assert "<script>alert(" not in response.text, f"Unescaped script tag in {profile_id}"

            # If scripts are present, they should be escaped
            if "&lt;script&gt;" in response.text:
                print(f"Script tags properly escaped in {profile_id}")

    def test_custom_html_section_exists(self):
        """Test that custom HTML section is rendered in template"""
        response = requests.get(f"{self.base_url}/profiles/retro_coder_2006")
        assert response.status_code == 200

        soup = BeautifulSoup(response.text, "html.parser")

        # Check for custom HTML section
        custom_section = soup.find(class_="custom-html-section")
        if custom_section:
            print("Custom HTML section found in template")
            assert len(custom_section.text.strip()) > 0, "Custom HTML section is empty"
        else:
            # Custom HTML might be rendered without the wrapper div
            # Check for marquee as evidence of custom HTML
            marquees = soup.find_all("marquee")
            assert len(marquees) > 0, "No custom HTML section or marquee elements found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
