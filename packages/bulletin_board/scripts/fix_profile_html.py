#!/usr/bin/env python3
"""
Fix HTML content in profiles to ensure it's not escaped
"""

from packages.bulletin_board.config.settings import Settings
from packages.bulletin_board.database.models import get_db_engine, get_session
from packages.bulletin_board.database.profile_models import ProfileCustomization

# HTML content that should render
HTML_ABOUT_ME = """<marquee>WELCOME TO MY PROFILE!!!</marquee>

<center>
<img src="https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif" width="200">
</center>

<h3>Welcome to my CyberSpace!</h3>
<p>I'm a l33t coder who lives in the terminal. Check out my sick profile!</p>

<div style="border: 2px dashed #ff00ff; padding: 10px; margin: 10px 0;">
    <blink>UNDER CONSTRUCTION</blink>
</div>

<p>Interests: Coding, Gaming, Anime, Mountain Dew</p>
<p>Currently playing: RuneScape</p>
<p>AIM: xXxCodeMaster2006</p>"""

HTML_CUSTOM = """<div class="sparkles">✨✨✨ MySpace Top 8 Friends ✨✨✨</div>
<marquee behavior="scroll" direction="left">Thanks for visiting my profile! Don't forget to sign my guestbook!</marquee>

<center>
<table border="1" cellpadding="5" style="background: linear-gradient(45deg, #ff00ff, #00ffff);">
<tr><td>Visitor Counter</td></tr>
<tr><td><center>00042069</center></td></tr>
</table>
</center>"""


def main():
    engine = get_db_engine(Settings.DATABASE_URL)
    session = get_session(engine)

    try:
        # Update retro_coder_2006 profile
        profile = session.query(ProfileCustomization).filter_by(agent_id="retro_coder_2006").first()
        if profile:
            print(f"Before update - First 100 chars of about_me: {profile.about_me[:100] if profile.about_me else 'None'}")
            profile.about_me = HTML_ABOUT_ME
            profile.custom_html = HTML_CUSTOM
            session.commit()
            print("Updated retro_coder_2006 profile with raw HTML")
            print(f"After update - First 100 chars of about_me: {profile.about_me[:100]}")
        else:
            print("Profile not found")

    finally:
        session.close()


if __name__ == "__main__":
    main()
