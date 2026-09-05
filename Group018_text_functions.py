"""
Group018_text_functions.py

The six fixed text-processing functions required by the FIT5196 A1
specification (Task 3). These functions are used to clean narrative text
(customer notes, delivery notes, product descriptions and product reviews)
and to extract structured business references and script information from
that text.

Design notes:
- Every function accepts None or a string, and never raises on ordinary
  missing/blank input; instead it returns the literal string "NaN", per the
  fixed interface in the specification.
- No file I/O, network access or row-specific (per-record) lookups happen
  inside these functions.
- Only the Python standard library is used: re, html, unicodedata.
- Reference extraction (order/SKU/promo) is designed to run on the RAW value
  BEFORE cleaning, and clean_narrative_text is designed to run on the RAW
  value too (it performs its own decode/strip steps internally), matching
  the published processing order in the spec (extract first, then clean).
"""

import re
import html
import unicodedata


# ---------------------------------------------------------------------------
# Compiled patterns (built once at import time)
# ---------------------------------------------------------------------------

# Bracketed system/catalogue/verification markers and social tokens that must
# be removed. [SOURCE: ...] and [RATING: n/5] have variable inner content.
_MARKER_RE = re.compile(
    r"\[SYSTEM\]"
    r"|\[CATALOGUE\]"
    r"|\[VERIFIED_PURCHASE\]"
    r"|\[SOURCE:[^\]]*\]"
    r"|\[RATING:\s*\d/5\]"
    r"|#verified-buyer"
    r"|@store_support",
    flags=re.IGNORECASE,
)

# HTML/XML-like tags, e.g. <b>, </b>, <br/>
_TAG_RE = re.compile(r"<[^>]+>")

# URLs (http/https and bare www. links)
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", flags=re.IGNORECASE)

# Common emoji / pictograph Unicode ranges seen in review text
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U00002B00-\U00002BFF"  # misc symbols and arrows (e.g. the plain star, U+2B50)
    "\U00002300-\U000023FF"  # misc technical (e.g. watch/hourglass symbols)
    "\U0001F1E6-\U0001F1FF"  # regional indicator (flag) letters
    "\U0000FE0F"              # variation selector-16
    "]+",
    flags=re.UNICODE,
)

# Complete review-reference wrapper, e.g. "Reference: HORD123456 | SKU: SKU-ABC123".
# The separator between the order reference and "SKU:" varies in practice
# (pipe, semicolon, slash, or just a bare newline/tab) -- the character
# class below covers whitespace AND punctuation together so any of those
# variants match, rather than requiring a punctuation character to be present.
_REFERENCE_WRAPPER_RE = re.compile(
    r"Reference:\s*(?:HORD|CORD)\d{6}[\s|,;/\-]+SKU:\s*SKU-[A-Za-z0-9]+",
    flags=re.IGNORECASE,
)

# Complete promotion wrapper, e.g. "PROMO: B1SAVE-14"
_PROMO_WRAPPER_RE = re.compile(
    r"PROMO:\s*B[1-5]SAVE-\d{2}",
    flags=re.IGNORECASE,
)

# Whitespace collapsing (spaces, tabs, newlines, etc.)
_WHITESPACE_RE = re.compile(r"\s+")

# Business-reference extraction patterns. A "not alphanumeric" lookbehind and
# lookahead are used on both sides so a reference embedded inside a longer
# token (e.g. "XHORD123456" or "HORD1234567") is correctly rejected.
_ORDER_REF_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:HORD|CORD)\d{6}(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_SKU_RE = re.compile(
    r"(?<![A-Za-z0-9])SKU-[A-Za-z0-9]+(?![A-Za-z0-9-])",
    flags=re.IGNORECASE,
)
_PROMO_RE = re.compile(
    r"(?<![A-Za-z0-9])B[1-5]SAVE-\d{2}(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)

_NAN = "NaN"

# A small set of common non-ASCII punctuation marks that turn up in ordinary
# Latin-script text (e.g. pasted from Word) -- kept in the Latin analysis
# field rather than being treated as script-specific punctuation.
_COMMON_SMART_PUNCTUATION = set("\u2018\u2019\u201c\u201d\u2013\u2014\u2026")


def _is_blank(value):
    """Return True when value is None, not a string, or blank after stripping."""
    if value is None or not isinstance(value, str):
        return True
    return value.strip() == ""


def clean_narrative_text(value):
    """
    Accept None or a string; return cleaned text or the string 'NaN'.

    Follows the published cleaning order (spec steps 3-9):
    decode entities + NFC normalise -> strip tags -> strip markers/URLs/emoji
    -> strip the reference wrapper -> strip the promo wrapper -> collapse
    whitespace, trim and lower-case -> return 'NaN' if nothing readable
    remains.
    """
    if _is_blank(value):
        return _NAN

    text = value

    # Step 3: decode HTML entities (e.g. &amp;) then apply NFC normalisation
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)

    # Step 4: remove HTML/XML-like tags but keep the text between them
    text = _TAG_RE.sub("", text)

    # Step 5: remove system/source/rating/social markers, URLs and emoji
    text = _MARKER_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)

    # Step 6: remove a complete "Reference: ... | SKU: ..." wrapper
    text = _REFERENCE_WRAPPER_RE.sub("", text)

    # Step 7: remove a complete "PROMO: ..." wrapper
    text = _PROMO_WRAPPER_RE.sub("", text)

    # Step 8: collapse whitespace, trim, and lower-case the result
    text = _WHITESPACE_RE.sub(" ", text).strip().lower()

    # Step 9: if nothing readable remains, return the literal sentinel
    if text == "":
        return _NAN
    return text


def extract_order_reference(value):
    """
    Accept None or a string; return the upper-case order reference or 'NaN'.

    A valid order reference is HORD or CORD followed by exactly six digits,
    with no letter or digit directly touching either side (this rejects
    embedded, overlong or otherwise malformed near-matches).
    """
    if _is_blank(value):
        return _NAN
    match = _ORDER_REF_RE.search(value)
    if not match:
        return _NAN
    return match.group(0).upper()


def extract_product_sku(value):
    """
    Accept None or a string; return the upper-case SKU or 'NaN'.

    A valid SKU is 'SKU-' followed by one or more ASCII letters/digits, not
    directly preceded by another letter or digit, and not immediately
    followed by a hyphen (which would indicate a longer, malformed variant
    rather than a clean SKU code).
    """
    if _is_blank(value):
        return _NAN
    match = _SKU_RE.search(value)
    if not match:
        return _NAN
    return match.group(0).upper()


def extract_promo_code(value):
    """
    Accept None or a string; return the upper-case promo code or 'NaN'.

    A valid promotion code is B1SAVE- to B5SAVE-, followed by exactly two
    digits, with no letter or digit directly touching either side.
    """
    if _is_blank(value):
        return _NAN
    match = _PROMO_RE.search(value)
    if not match:
        return _NAN
    return match.group(0).upper()


def build_latin_analysis(value):
    """
    Accept cleaned multilingual text; return Latin analysis or 'NaN'.

    Keeps Latin-script letters (including European diacritics), digits,
    whitespace and punctuation; removes non-Latin letters. A character is
    treated as Latin when it is alphabetic and its Unicode character name
    contains 'LATIN' -- this correctly keeps accented Latin letters while
    dropping letters from other scripts (Chinese, Cyrillic, Arabic, etc.).
    """
    if _is_blank(value) or value == _NAN:
        return _NAN

    kept_chars = []
    for ch in value:
        if ch.isalpha():
            # Only keep alphabetic characters that belong to the Latin script
            name = unicodedata.name(ch, "")
            if "LATIN" in name:
                kept_chars.append(ch)
            # non-Latin letters are dropped silently
        elif ord(ch) < 128:
            # Plain ASCII digits, punctuation and whitespace are always
            # "applicable" regardless of the surrounding script.
            kept_chars.append(ch)
        elif ch in _COMMON_SMART_PUNCTUATION:
            # A small set of everyday non-ASCII punctuation (curly quotes,
            # en/em dash, ellipsis) that shows up in ordinary Latin-script
            # text copied from word processors -- worth keeping.
            kept_chars.append(ch)
        else:
            # Anything else non-ASCII here is either a combining mark
            # (accents, harakat, niqqud, matras) or script-specific
            # punctuation/symbols (e.g. CJK full-width punctuation, Arabic
            # punctuation). None of this is "applicable" Latin-field
            # punctuation, so it is dropped.
            continue

    result = _WHITESPACE_RE.sub(" ", "".join(kept_chars)).strip()

    # Drop any standalone token that is pure punctuation/symbols with no
    # surviving letter or digit -- these are orphaned marks left behind
    # once the non-Latin word they belonged to was removed, and keeping
    # them just clutters the field with meaningless leftover commas/dots.
    # Punctuation still attached to a real word/number is untouched, since
    # that punctuation is part of a different (non-empty) token.
    tokens = [
        token for token in result.split()
        if any(ch.isalpha() or ch.isdigit() for ch in token)
    ]
    result = " ".join(tokens)

    # If no Latin letter survived, there is nothing meaningful to analyse
    if not any(c.isalpha() for c in result):
        return _NAN
    return result


def contains_non_latin_script(value):
    """
    Accept cleaned multilingual text; return a Python bool.

    True when the text contains at least one letter whose Unicode script is
    not Latin. A non-ASCII character alone (e.g. a digit, punctuation mark or
    diacritic) does not by itself count as non-Latin.
    """
    if _is_blank(value) or value == _NAN:
        return False

    for ch in value:
        if ch.isalpha():
            name = unicodedata.name(ch, "")
            if "LATIN" not in name:
                return True
    return False
