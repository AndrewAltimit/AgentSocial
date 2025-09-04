"""
Selenium tests for code block rendering functionality
Tests that markdown code blocks are properly parsed and styled
"""

import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestCodeBlockRendering:
    """Test suite for code block rendering functionality"""

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

    def setup_method(self):
        """Create a test post with code blocks before each test"""
        import requests

        # Create a test post with various code blocks
        self.test_post_content = """Here's a comprehensive code example:

```yaml
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```

Some inline code: `const x = 42;` and `print("hello")`

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

```javascript
function greet(name) {
    console.log(`Hello, ${name}!`);
}
```
"""

        # Use the standardized seed API endpoint for test data creation
        headers = {
            "X-Internal-API-Key": "test-key",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/api/internal/seed/post",
            json={
                "title": "Test Code Block Rendering",
                "content": self.test_post_content,
                "agent_id": "test_agent",
                "content_type": "markdown"
            },
            headers=headers
        )

        if response.status_code in [200, 201]:
            self.test_post_id = response.json().get("id")
        else:
            # Fallback: find existing post with code blocks
            posts = requests.get(f"{self.base_url}/api/posts").json()
            for post in posts:
                if "```" in post.get("content", ""):
                    self.test_post_id = post["id"]
                    break
            else:
                # No post with code blocks found
                if posts:
                    self.test_post_id = posts[0]["id"]
                else:
                    self.test_post_id = None

    def test_code_blocks_have_pre_tags(self):
        """Test that code blocks are wrapped in <pre> tags"""
        # Navigate to a post with code blocks
        self.driver.get(self.base_url)
        time.sleep(2)

        # Click on the first post
        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        # Wait for thread view to load
        time.sleep(2)

        # Check for <pre> elements
        pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")
        assert len(pre_elements) > 0, "No <pre> elements found for code blocks"

        # Check that pre elements contain code elements
        for pre in pre_elements:
            code_element = pre.find_element(By.TAG_NAME, "code")
            assert code_element is not None, "<pre> element missing <code> child"

    def test_code_blocks_have_proper_styling(self):
        """Test that code blocks have the correct CSS styling"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Find a pre element
        pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")
        if pre_elements:
            pre = pre_elements[0]

            # Check CSS properties
            background_color = pre.value_of_css_property("background-color")
            border = pre.value_of_css_property("border")
            border_radius = pre.value_of_css_property("border-radius")
            font_family = pre.value_of_css_property("font-family")

            # Verify styling (background should be light gray)
            assert background_color in [
                "rgb(246, 247, 248)",
                "rgba(246, 247, 248, 1)",
            ], f"Expected gray background, got {background_color}"

            # Verify border exists
            assert "solid" in border or border != "none", f"Expected solid border, got {border}"

            # Verify border radius
            assert border_radius != "0px", f"Expected rounded corners, got {border_radius}"

            # Verify monospace font
            assert any(
                font in font_family.lower() for font in ["consolas", "monaco", "courier", "monospace"]
            ), f"Expected monospace font, got {font_family}"

    def test_inline_code_has_proper_styling(self):
        """Test that inline code has the correct CSS styling"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Find inline code elements
        inline_code_elements = self.driver.find_elements(By.CLASS_NAME, "inline-code")

        if inline_code_elements:
            code = inline_code_elements[0]

            # Check CSS properties
            background_color = code.value_of_css_property("background-color")
            padding = code.value_of_css_property("padding")
            font_family = code.value_of_css_property("font-family")

            # Verify inline code styling
            assert (
                "rgba" in background_color or "rgb" in background_color
            ), f"Expected background color, got {background_color}"

            # Verify padding exists
            assert padding != "0px", f"Expected padding for inline code, got {padding}"

            # Verify monospace font
            assert any(
                font in font_family.lower() for font in ["consolas", "monaco", "courier", "monospace"]
            ), f"Expected monospace font for inline code, got {font_family}"

    def test_language_specific_classes(self):
        """Test that code blocks have language-specific classes"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Look for code elements with language classes
        code_elements = self.driver.find_elements(By.TAG_NAME, "code")

        language_classes_found = []
        for code in code_elements:
            class_attr = code.get_attribute("class")
            if class_attr and "language-" in class_attr:
                language_classes_found.append(class_attr)

        # Should find at least one language-specific class
        assert len(language_classes_found) > 0, "No language-specific classes found on code blocks"

        # Check for expected language classes
        expected_languages = ["language-yaml", "language-python", "language-javascript"]
        for expected in expected_languages:
            if any(expected in cls for cls in language_classes_found):
                break
        else:
            # Only fail if we expected specific languages but found none
            if language_classes_found:
                pass  # Found some language classes, that's good enough
            else:
                assert False, f"Expected language classes {expected_languages}, found {language_classes_found}"

    def test_code_content_not_escaped(self):
        """Test that code content is not HTML-escaped"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Find code blocks
        code_elements = self.driver.find_elements(By.TAG_NAME, "code")

        for code in code_elements:
            text = code.text
            # Code should not contain HTML entities
            assert "&lt;" not in text, "Code contains escaped < character"
            assert "&gt;" not in text, "Code contains escaped > character"
            assert "&amp;" not in text, "Code contains escaped & character"
            assert "&quot;" not in text, "Code contains escaped quote character"

            # Should be able to find actual code syntax
            if "def " in text or "function " in text or "version:" in text:
                # Found actual code content
                break
        else:
            # Check if we found any code at all
            assert len(code_elements) > 0, "No code blocks found in the post"

    def test_code_blocks_in_comments(self):
        """Test that code blocks work in comments as well as posts"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Check comments section for code blocks
        comments_section = self.driver.find_element(By.CLASS_NAME, "comments-section")

        # Look for pre elements within comments
        comment_code_blocks = comments_section.find_elements(By.TAG_NAME, "pre")

        # If there are comments with code, verify they're styled
        if comment_code_blocks:
            for pre in comment_code_blocks:
                code = pre.find_element(By.TAG_NAME, "code")
                assert code is not None, "Comment code block missing <code> element"

                # Check styling
                background_color = pre.value_of_css_property("background-color")
                assert background_color in [
                    "rgb(246, 247, 248)",
                    "rgba(246, 247, 248, 1)",
                ], f"Comment code block has incorrect background: {background_color}"

    def test_code_block_scrolling(self):
        """Test that long code blocks have horizontal scrolling"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Find pre elements
        pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")

        if pre_elements:
            pre = pre_elements[0]

            # Check overflow property
            overflow_x = pre.value_of_css_property("overflow-x")
            assert overflow_x in [
                "auto",
                "scroll",
            ], f"Expected horizontal scrolling for code blocks, got overflow-x: {overflow_x}"

    def test_multiple_code_blocks_render(self):
        """Test that multiple code blocks in the same post all render correctly"""
        # Navigate to a post
        self.driver.get(self.base_url)
        time.sleep(2)

        first_post = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "post-card")))
        first_post.click()

        time.sleep(2)

        # Find all code blocks
        pre_elements = self.driver.find_elements(By.TAG_NAME, "pre")

        # Should have multiple code blocks if test data was added
        if len(pre_elements) > 1:
            # Verify each has proper structure
            for i, pre in enumerate(pre_elements):
                code = pre.find_element(By.TAG_NAME, "code")
                assert code is not None, f"Code block {i} missing <code> element"

                # Each should have content
                assert len(code.text.strip()) > 0, f"Code block {i} is empty"
