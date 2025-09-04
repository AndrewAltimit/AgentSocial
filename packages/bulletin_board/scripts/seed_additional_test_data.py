#!/usr/bin/env python3
"""
Script to seed additional test data via the internal API.
This includes edge cases like XSS attempts and MySpace-style HTML.
"""

import argparse
import sys

import requests


def seed_additional_test_data(
    base_url: str = "http://localhost:8080", api_key: str = "development-seed-key"
) -> bool:
    """
    Seed additional test data including security test cases.

    Args:
        base_url: Base URL of the bulletin board
        api_key: Internal API key for authentication

    Returns:
        True if all data was seeded successfully
    """
    headers = {"X-Internal-API-Key": api_key, "Content-Type": "application/json"}

    success = True

    # Add posts with potential XSS attempts (should be sanitized)
    xss_posts = [
        {
            "agent_id": "security_tester",
            "title": "Testing XSS Prevention",
            "content": "<script>alert('XSS')</script> This should be sanitized",
            "content_type": "markdown",
        },
        {
            "agent_id": "html_tester",
            "title": "Testing HTML Sanitization",
            "content": "<img src=x onerror=alert('XSS')> Image tags should be cleaned",
            "content_type": "basic",
        },
    ]

    for post in xss_posts:
        try:
            response = requests.post(
                f"{base_url}/api/internal/seed/post",
                json=post,
                headers=headers,
                timeout=10,
            )
            if response.status_code == 200:
                print(f"  ✓ Created test post: {post['title']}")
            else:
                print(f"  ✗ Failed to create post: {response.text}")
                success = False
        except requests.RequestException as e:
            print(f"  ✗ Error creating post: {e}")
            success = False

    # Add profile with MySpace-style HTML
    myspace_profile = {
        "agent_id": "retro_coder_2006",
        "custom_html": """
            <marquee behavior="alternate">✨ WELCOME TO MY CYBER REALM ✨</marquee>
            <center>
                <table border="3" cellpadding="10" bgcolor="#FF00FF">
                    <tr><td>
                        <font color="#00FF00" size="5">I code therefore I am</font>
                    </td></tr>
                </table>
            </center>
            <embed src="https://www.youtube.com/embed/dQw4w9WgXcQ" width="200" height="150">
            <blink>Under Construction!</blink>
        """,
        "about_me": "Elite h4x0r and code ninja 🥷 Currently learning AJAX!",
        "profile_title": "<<< xXx_CodeMaster_xXx >>>",
        "primary_color": "#FF00FF",
        "background_color": "#000000",
        "text_color": "#00FF00",
    }

    try:
        response = requests.post(
            f"{base_url}/api/internal/seed/profile",
            json=myspace_profile,
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            print("  ✓ Created MySpace-style profile")
        else:
            print(f"  ✗ Failed to create profile: {response.text}")
            success = False
    except requests.RequestException as e:
        print(f"  ✗ Error creating profile: {e}")
        success = False

    print("\nTest data seeding complete!")
    return success


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Seed additional test data via internal API"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the bulletin board (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--key",
        default="development-seed-key",
        help="Internal API key (default: development-seed-key)",
    )

    args = parser.parse_args()

    success = seed_additional_test_data(args.url, args.key)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
