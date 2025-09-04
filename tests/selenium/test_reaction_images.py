#!/usr/bin/env python3
"""
Selenium test for reaction image rendering in comments
"""

import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@pytest.fixture
def driver():
    """Create and configure Chrome driver"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    yield driver
    driver.quit()


def test_reaction_images_render_in_comments(driver):
    """Test that reaction images properly render in comment content"""

    # Navigate to the bulletin board
    driver.get("http://localhost:8080")

    # Wait for page to load
    wait = WebDriverWait(driver, 10)

    try:
        # Wait for posts to load
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post")))

        # Find and click on the first post to load comments
        first_post = driver.find_element(By.CSS_SELECTOR, ".post")
        post_title = first_post.find_element(By.CSS_SELECTOR, ".post-title")
        post_title.click()

        # Wait for comments to load
        time.sleep(2)  # Allow time for dynamic content to load

        # Check for reaction images in comments
        reaction_images = driver.find_elements(By.CSS_SELECTOR, ".comment-body img.reaction-img")

        assert len(reaction_images) > 0, "No reaction images found in comments"

        # Verify reaction images have proper attributes
        for img in reaction_images[:3]:  # Check first 3 images
            src = img.get_attribute("src")
            assert "AndrewAltimit/Media" in src, f"Invalid reaction image source: {src}"
            assert "/reaction/" in src, f"Not a reaction image path: {src}"

            # Check that image is visible
            assert img.is_displayed(), "Reaction image is not visible"

            # Check image has reasonable dimensions (not 0x0)
            width = img.get_attribute("width") or img.size["width"]
            height = img.get_attribute("height") or img.size["height"]

            # Images should have some size (either from attributes or computed)
            if width and height:
                assert int(width) > 0 or img.size["width"] > 0, "Image has no width"
                assert int(height) > 0 or img.size["height"] > 0, "Image has no height"

        print(f"✓ Found {len(reaction_images)} reaction images in comments")

        # Check that reaction images have proper CSS class
        for img in reaction_images:
            classes = img.get_attribute("class")
            assert "reaction-img" in classes, f"Missing reaction-img class: {classes}"

        print("✓ All reaction images have proper CSS class")

        # Verify images are within comment bodies
        for img in reaction_images[:3]:
            parent = img.find_element(By.XPATH, "./..")
            # Navigate up to find comment-body
            attempts = 0
            while attempts < 5:
                if "comment-body" in parent.get_attribute("class"):
                    break
                parent = parent.find_element(By.XPATH, "./..")
                attempts += 1

            assert attempts < 5, "Reaction image not within comment-body"

        print("✓ All reaction images are properly nested in comment bodies")

    except TimeoutException:
        pytest.fail("Page elements did not load in time")
    except Exception as e:
        # Take screenshot on failure
        driver.save_screenshot("/tmp/reaction_image_test_failure.png")
        raise e


def test_reaction_images_have_alt_text(driver):
    """Test that reaction images have proper alt text for accessibility"""

    driver.get("http://localhost:8080")
    wait = WebDriverWait(driver, 10)

    # Wait for page and click first post
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post")))
    first_post = driver.find_element(By.CSS_SELECTOR, ".post .post-title")
    first_post.click()

    time.sleep(2)

    # Find reaction images
    reaction_images = driver.find_elements(By.CSS_SELECTOR, ".comment-body img.reaction-img")

    for img in reaction_images:
        alt_text = img.get_attribute("alt")
        assert alt_text, "Reaction image missing alt text"
        assert "Reaction" in alt_text, f"Invalid alt text: {alt_text}"

    print(f"✓ All {len(reaction_images)} reaction images have proper alt text")


def test_markdown_images_not_escaped(driver):
    """Test that markdown image syntax is properly converted to HTML img tags"""

    driver.get("http://localhost:8080")
    wait = WebDriverWait(driver, 10)

    # Wait and click first post
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "post")))
    first_post = driver.find_element(By.CSS_SELECTOR, ".post .post-title")
    first_post.click()

    time.sleep(2)

    # Check that comment bodies don't contain raw markdown syntax
    comment_bodies = driver.find_elements(By.CSS_SELECTOR, ".comment-body")

    for body in comment_bodies:
        text = body.text
        # Should not contain raw markdown image syntax
        assert "![Reaction]" not in text, "Found unprocessed markdown image syntax in comment"

        # If the comment mentions reaction, it should have an actual img element
        if "reaction" in text.lower() or body.find_elements(By.TAG_NAME, "img"):
            inner_html = body.get_attribute("innerHTML")
            # Should have img tags, not escaped markdown
            if "AndrewAltimit/Media" in inner_html:
                assert "<img" in inner_html, "Reaction reference found but no img tag"

    print("✓ No escaped markdown syntax found in comments")


if __name__ == "__main__":
    # Run tests
    import sys

    # Create driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    test_driver = webdriver.Chrome(options=options)

    try:
        print("Running reaction image tests...")

        test_reaction_images_render_in_comments(test_driver)
        test_reaction_images_have_alt_text(test_driver)
        test_markdown_images_not_escaped(test_driver)

        print("\n✅ All reaction image tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    finally:
        test_driver.quit()
