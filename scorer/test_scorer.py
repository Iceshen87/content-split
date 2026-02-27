#!/usr/bin/env python3
"""Tests for quality scorer."""
import sys
sys.path.insert(0, '/root/.openclaw/workspace')
from quality_scorer import (
    score_submission, detect_format, FormatType
)
import json

def test_format_detection():
    assert detect_format('{"key": "value"}') == FormatType.JSON
    assert detect_format('[1, 2, 3]') == FormatType.JSON
    assert detect_format('def hello():\n    pass') == FormatType.CODE
    print("Format detection: OK")

def test_json_scoring():
    content = json.dumps({"id": "1", "name": "Test", "value": 100})
    result = score_submission(content)
    assert result.format_detected == "json"
    assert 0 <= result.weighted_score <= 1
    print("JSON scoring: OK")

def test_markdown_scoring():
    # Markdown needs multiple features to be detected
    content = "# Title\n\nParagraph with **bold**.\n\n- Item 1\n\n[link](url)"
    result = score_submission(content)
    assert result.weighted_score > 0
    print("Markdown scoring: OK")

def test_code_scoring():
    content = "def calculate(x):\n    return x * 2\n\n# Main\nprint(calculate(5))"
    result = score_submission(content)
    assert result.format_detected == "code"
    assert "completeness" in result.scores
    print("Code scoring: OK")

def test_threshold():
    good = json.dumps({"id": "1", "name": "Test", "value": 100, "type": "example", "data": {}})
    result = score_submission(good, pass_threshold=0.5)
    assert result.pass_threshold == (result.weighted_score >= 0.5)
    print("Threshold: OK")

def test_performance():
    import time
    start = time.time()
    for _ in range(100):
        score_submission('{"test": "data"}')
    elapsed = time.time() - start
    assert elapsed < 10, f"100 submissions took {elapsed}s (should be <10s)"
    print(f"Performance: OK ({elapsed:.2f}s for 100 submissions)")

if __name__ == "__main__":
    test_format_detection()
    test_json_scoring()
    test_markdown_scoring()
    test_code_scoring()
    test_threshold()
    test_performance()
    print("\n✓ All tests passed!")
