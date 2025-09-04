"""
Test suite for verifying code block syntax highlighting with Prism.js
"""

import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TestSyntaxHighlighting:
    @classmethod
    def setup_class(cls):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        cls.driver = webdriver.Chrome(options=options)
        cls.wait = WebDriverWait(cls.driver, 10)
        cls.base_url = "http://bulletin-web:8080"

    @classmethod
    def teardown_class(cls):
        """Clean up after tests"""
        cls.driver.quit()

    def test_prism_js_loaded(self):
        """Verify Prism.js library is loaded on the page"""
        self.driver.get(self.base_url)

        # Check if Prism.js CSS is loaded
        prism_css = self.driver.find_elements(By.CSS_SELECTOR, 'link[href*="prism"]')
        assert len(prism_css) > 0, "Prism.js CSS not found"

        # Check if Prism.js scripts are loaded
        prism_scripts = self.driver.find_elements(By.CSS_SELECTOR, 'script[src*="prism"]')
        assert len(prism_scripts) > 0, "Prism.js scripts not found"

        # Verify Prism object is available in JavaScript
        prism_available = self.driver.execute_script("return typeof Prism !== 'undefined';")
        assert prism_available, "Prism object not available in JavaScript"

    def test_code_blocks_have_language_classes(self):
        """Verify code blocks have proper language classes for syntax highlighting"""
        self.driver.get(self.base_url)

        # Wait for posts to load
        time.sleep(2)

        # Look for code blocks with language classes
        code_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'code[class*="language-"]')

        if len(code_blocks) > 0:
            # Check that code blocks have proper language classes
            for block in code_blocks:
                class_attr = block.get_attribute("class")
                assert "language-" in class_attr, f"Code block missing language class: {class_attr}"

                # Check if syntax tokens are present (Prism adds spans with token classes)
                tokens = block.find_elements(By.CSS_SELECTOR, "span.token")
                if block.text.strip():  # Only check if there's actual code content
                    assert (
                        len(tokens) > 0
                    ), f"No syntax highlighting tokens found in code block with content: {block.text[:50]}"

    def test_python_code_highlighting(self):
        """Test that Python code blocks are properly highlighted"""
        # Navigate to check any existing Python code blocks
        self.driver.get(self.base_url)
        time.sleep(2)

        python_blocks = self.driver.find_elements(By.CSS_SELECTOR, "code.language-python")

        for block in python_blocks:
            # Check for Python-specific token classes
            keywords = block.find_elements(By.CSS_SELECTOR, "span.token.keyword")
            functions = block.find_elements(By.CSS_SELECTOR, "span.token.function")
            strings = block.find_elements(By.CSS_SELECTOR, "span.token.string")

            # At least one type of syntax element should be highlighted
            assert len(keywords) > 0 or len(functions) > 0 or len(strings) > 0, "Python code block lacks syntax highlighting"

    def test_javascript_code_highlighting(self):
        """Test that JavaScript code blocks are properly highlighted"""
        self.driver.get(self.base_url)
        time.sleep(2)

        js_blocks = self.driver.find_elements(By.CSS_SELECTOR, "code.language-javascript, code.language-js")

        for block in js_blocks:
            # Check for JavaScript-specific token classes
            tokens = block.find_elements(By.CSS_SELECTOR, "span.token")
            if block.text.strip():
                assert len(tokens) > 0, "JavaScript code block lacks syntax highlighting"

    def test_markdown_to_html_conversion(self):
        """Verify markdown content is converted to HTML with proper code blocks"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Check if there are pre/code blocks (indicating markdown was converted)
        pre_blocks = self.driver.find_elements(By.CSS_SELECTOR, "pre > code")

        # If we have markdown posts, they should be converted to proper HTML structure
        if pre_blocks:
            for pre_code in pre_blocks:
                # Verify the structure: <pre><code class="language-xxx">
                assert pre_code.tag_name == "code", "Code block not properly nested in <pre>"

                # Check parent is <pre>
                parent = pre_code.find_element(By.XPATH, "..")
                assert parent.tag_name == "pre", "Code block not wrapped in <pre> tag"

    def test_prism_theme_applied(self):
        """Verify Prism theme (Tomorrow Night) is applied"""
        self.driver.get(self.base_url)

        # Check if Tomorrow Night theme CSS is loaded
        theme_css = self.driver.find_elements(By.CSS_SELECTOR, 'link[href*="prism-tomorrow"]')
        assert len(theme_css) > 0, "Prism Tomorrow Night theme not loaded"

        # Check if code blocks have appropriate styling
        code_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'pre > code[class*="language-"]')

        for block in code_blocks[:1]:  # Check at least one block
            # Get computed styles
            background = self.driver.execute_script(
                "return window.getComputedStyle(arguments[0].parentElement).backgroundColor;", block
            )
            # Tomorrow Night theme has a dark background
            # We just check it's not the default white/transparent
            assert background not in [
                "transparent",
                "rgba(0, 0, 0, 0)",
                "rgb(255, 255, 255)",
            ], f"Code block doesn't have theme styling applied. Background: {background}"

    def test_inline_code_styling(self):
        """Test that inline code has appropriate styling"""
        self.driver.get(self.base_url)
        time.sleep(2)

        # Look for inline code elements
        inline_codes = self.driver.find_elements(By.CSS_SELECTOR, 'code.inline-code, code:not([class*="language-"])')

        for code in inline_codes[:3]:  # Check first few inline codes
            # Inline code should have different styling than block code
            parent = code.find_element(By.XPATH, "..")
            # Inline code should NOT be inside <pre> tags
            if parent.tag_name != "pre":
                # Check it has some styling (background or border)
                background = self.driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", code)
                padding = self.driver.execute_script("return window.getComputedStyle(arguments[0]).padding;", code)
                # Should have some visual distinction
                assert background != "rgba(0, 0, 0, 0)" or padding != "0px", "Inline code lacks visual styling"
