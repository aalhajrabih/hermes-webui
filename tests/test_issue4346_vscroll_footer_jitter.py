"""Static source assertions for issue #4346 virtual-scroll footer jitter fix."""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent

CSS = (ROOT / 'static' / 'style.css').read_text(encoding='utf-8')
JS  = (ROOT / 'static' / 'ui.js').read_text(encoding='utf-8')


def test_css_vscroll_measuring_guard():
    """style.css suppresses opacity transitions on .msg-foot and .msg-actions
    while .vscroll-measuring is present on the scroll container."""
    assert 'vscroll-measuring' in CSS
    guard_match = re.search(
        r'(?m)^\.vscroll-measuring\s+\.msg-foot,\n'
        r'^\.vscroll-measuring\s+\.msg-actions,\n'
        r'^\.vscroll-measuring\s+\.msg-time\{transition:none !important;\}$',
        CSS,
    )
    assert guard_match, \
        "missing contiguous .vscroll-measuring transition:none !important guard block"


def test_js_compensate_adds_vscroll_measuring():
    """_compensateScrollForMeasurementDelta adds and removes the vscroll-measuring
    class around the render callback."""
    fn_match = re.search(
        r'function _compensateScrollForMeasurementDelta\(renderFn\)\{(.+?)^(?=function )',
        JS, re.DOTALL | re.MULTILINE
    )
    assert fn_match, "_compensateScrollForMeasurementDelta not found"
    body = fn_match.group(1)
    assert "classList.add('vscroll-measuring')" in body
    assert "classList.remove('vscroll-measuring')" in body


def test_js_try_finally_guards_class_removal():
    """The classList.remove is inside the finally{} block, not after it."""
    fn_match = re.search(
        r'function _compensateScrollForMeasurementDelta\(renderFn\)\{(.+?)^(?=function )',
        JS, re.DOTALL | re.MULTILINE
    )
    assert fn_match
    body = fn_match.group(1)
    try_idx = body.find('try{')
    finally_idx = body.find('finally{')
    remove_idx = body.find("classList.remove('vscroll-measuring')")
    assert try_idx != -1, "no try block found in _compensateScrollForMeasurementDelta"
    assert finally_idx != -1, "no finally block found in _compensateScrollForMeasurementDelta"
    assert remove_idx != -1, "missing classList.remove('vscroll-measuring')"
    assert try_idx < finally_idx < remove_idx, \
        "classList.remove must remain in the finally{} cleanup path"
