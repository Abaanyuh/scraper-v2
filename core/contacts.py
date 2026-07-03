"""
Email extraction utilities.
"""

import re

GENERIC_ALIASES: set[str] = {
    "support", "info", "admin", "contact", "sales", "billing",
    "hello", "noreply", "no-reply", "webmaster", "postmaster",
    "abuse", "marketing", "press", "media",
}


def extract_contacts(html_text: str, max_emails: int = 5) -> list[str]:
    """
    Extract non-generic email addresses from *html_text*.

    Returns up to *max_emails* unique addresses.
    """
    raw = re.findall(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        html_text,
    )
    unique: list[str] = []
    for email in raw:
        prefix = email.split("@", 1)[0].lower()
        if prefix not in GENERIC_ALIASES and email not in unique:
            unique.append(email)
        if len(unique) >= max_emails:
            break
    return unique
