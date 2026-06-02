"""Regression test for #3429 — getModelLabel() mangles URI-scheme model IDs.

PR #3366 (fix for #3360) changed getModelLabel() to strip only the first
``/``-segment instead of ``split('/').pop()``. That fixed multi-slash proxy IDs
but regressed URI-scheme IDs (e.g. Yandex ``gpt://${FOLDER}/deepseek-v4-flash/latest``)
because ``indexOf('/')`` lands inside the ``://`` and leaves ``/${FOLDER}/...``
path junk in the composer model chip.

The fix detects a ``scheme://`` id and takes the last meaningful path segment
(skipping ``${...}`` env-var placeholders and bare version tails like ``latest``),
while NOT touching the #3360 multi-slash behavior for non-URI ids.

Runs the live getModelLabel() via Node so drift between the test and the real
code is caught immediately.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
UI_JS_PATH = REPO_ROOT / "static" / "ui.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")

_DRIVER = r"""
const fs = require('fs');
const ui = fs.readFileSync(process.argv[1], 'utf8');
// Slice getModelLabel() by function boundaries (regex literals inside it defeat
// a naive brace counter, so bound it by the next top-level function instead).
const start = ui.indexOf('function getModelLabel(');
if (start < 0) throw new Error('getModelLabel not found');
const after = ui.indexOf('\nfunction _gatewayProviderName(', start);
if (after < 0) throw new Error('getModelLabel end boundary not found');
const fnSrc = ui.slice(start, after);
const _dynamicModelLabels = {};
function _fmtOllamaLabel(s){ return s; }
eval(fnSrc);
const out = {};
for (const m of JSON.parse(process.argv[2])) out[m] = getModelLabel(m);
process.stdout.write(JSON.stringify(out));
"""


def _labels(model_ids):
    import json
    proc = subprocess.run(
        [NODE, "-e", _DRIVER, str(UI_JS_PATH), json.dumps(model_ids)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"node driver failed: {proc.stderr}"
    return json.loads(proc.stdout)


def test_uri_scheme_model_id_label_is_model_name_not_path_junk():
    """#3429: a gpt://.../model/latest id must label as the model name."""
    out = _labels([
        "gpt://${YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        "gpt://folder123/deepseek-v4-flash/latest",
        "openrouter://acct/qwen-3-coder",
        "gpt://${F}/qwen-3-coder",
    ])
    assert out["gpt://${YANDEX_FOLDER_ID}/deepseek-v4-flash/latest"] == "deepseek-v4-flash"
    assert out["gpt://folder123/deepseek-v4-flash/latest"] == "deepseek-v4-flash"
    assert out["openrouter://acct/qwen-3-coder"] == "qwen-3-coder"
    assert out["gpt://${F}/qwen-3-coder"] == "qwen-3-coder"
    # The env-var placeholder must never leak into the label.
    for label in out.values():
        assert "${" not in label, f"env-var placeholder leaked into label: {label!r}"


def test_uri_fix_does_not_regress_multi_slash_or_bare_ids():
    """#3360 multi-slash hierarchy + single-slash/bare ids stay correct."""
    out = _labels([
        "vendor_a/deepseek/deepseek-v4-pro",  # #3360: keep vendor hierarchy
        "claude-sonnet-4-6",                  # bare id unchanged
    ])
    # Non-URI multi-slash id keeps everything after the first segment (#3360).
    assert out["vendor_a/deepseek/deepseek-v4-pro"] == "deepseek/deepseek-v4-pro"
    assert out["claude-sonnet-4-6"] == "claude-sonnet-4-6"
