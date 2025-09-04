#!/usr/bin/env python3
"""
Migration to remove custom_css field from ProfileCustomization table
Since we're blocking custom CSS for security, we should not store it at all
"""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.config import get_database_url  # noqa: E402


def remove_custom_css_field():
    """Remove the custom_css column from profile_customizations table"""

    db_url = get_database_url()
    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='profile_customizations'
                AND column_name='custom_css'
            """
                )
            )

            if result.fetchone():
                # Drop the column
                conn.execute(
                    text(
                        """
                    ALTER TABLE profile_customizations
                    DROP COLUMN custom_css
                """
                    )
                )
                conn.commit()
                print("✅ Successfully removed custom_css field from ProfileCustomization table")
            else:
                print("ℹ️ custom_css field does not exist, no action needed")

    except OperationalError as e:
        print(f"❌ Error removing custom_css field: {e}")
        return False

    return True


if __name__ == "__main__":
    remove_custom_css_field()
