"""Static-asset guards for the teacher tools drawer (T17 open/close, T18 scroll)."""
import pathlib
import re

STATIC = pathlib.Path(__file__).resolve().parents[1] / "rotator" / "static"


def test_hidden_attribute_rule_present():
    """theme.css must force [hidden] elements to display:none (T17 root cause A)."""
    css = (STATIC / "css" / "theme.css").read_text()
    assert "[hidden]" in css
    assert "display: none" in css


def test_drawer_markup_starts_hidden():
    """The drawer element must carry the hidden attribute in the initial HTML."""
    html = (STATIC / "index.html").read_text()
    assert re.search(r'<aside id="drawer"[^>]*\bhidden\b', html)


def test_drawer_body_scrolls():
    """T18: the drawer body is the scroll area; section bodies must not clip.

    The drawer rules live in css/manage.css (the T12 manage.css / manage.js
    split), not css/layout.css, so that is the file this guard checks.
    """
    css = (STATIC / "css" / "manage.css").read_text()
    assert "overflow-y: auto" in css
    section_bodies = re.findall(r"\.(?:drawer-section-body|drawer-body)[^{]*\{[^}]*\}", css)
    assert section_bodies  # the rules must still exist, not be deleted
    for rule in section_bodies:
        assert not ("max-height" in rule and re.search(r"overflow:\s*hidden", rule)), rule
