"""T17: static-asset guards for the teacher tools drawer fix."""
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
