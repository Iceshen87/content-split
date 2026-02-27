#!/usr/bin/env python3
"""
Multi-Dimensional Quality Scoring for Structured Outputs

Scores submissions (JSON, markdown, code, text) against a rubric
returning a 0-1 weighted score with per-dimension feedback.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class FormatType(Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"
    TEXT = "text"


@dataclass
class QualityScore:
    """Score result for a single dimension."""
    dimension: str
    score: float  # 0.0 to 1.0
    weight: float
    feedback: str


@dataclass
class ScoringResult:
    """Complete scoring result."""
    weighted_score: float
    quality_rating: str
    scores: Dict[str, float]
    feedback: List[str]
    pass_threshold: bool
    format_detected: str


# Dimension weights as specified
DIMENSION_WEIGHTS = {
    "completeness": 0.30,
    "format_compliance": 0.20,
    "coverage": 0.25,
    "clarity": 0.15,
    "validity": 0.10,
}

# Quality rating thresholds
QUALITY_RATINGS = [
    (0.9, "Excellent"),
    (0.8, "Very Good"),
    (0.7, "Good"),
    (0.6, "Satisfactory"),
    (0.5, "Needs Improvement"),
    (0.0, "Poor"),
]

# Default pass threshold
DEFAULT_PASS_THRESHOLD = 0.6


def detect_format(content: str) -> FormatType:
    """Auto-detect the format of the submission."""
    content = content.strip()
    
    # Check for JSON
    if content.startswith("{") or content.startswith("["):
        try:
            json.loads(content)
            return FormatType.JSON
        except json.JSONDecodeError:
            pass
    
    # Check for code (common patterns)
    code_patterns = [
        r'^\s*(def |class |function |import |from |#include |package |func ',
        r'^\s*(public |private |protected |void |int |string |var |let |const )',
        r'^\s*<\?php',
        r'^\s*<(!DOCTYPE |html|head|body)',
        r'^\s*(import|export)\s+',
    ]
    for pattern in code_patterns:
        if re.match(pattern, content, re.MULTILINE | re.IGNORECASE):
            return FormatType.CODE
    
    # Check for markdown
    md_patterns = [
        r'^#{1,6}\s+',  # Headers
        r'^\*\*.*\*\*',  # Bold
        r'^\[.*\]\(.*\)',  # Links
        r'^```',  # Code blocks
        r'^[-*+]\s+',  # Lists
        r'^\d+\.\s+',  # Numbered lists
    ]
    md_count = sum(1 for p in md_patterns if re.search(p, content, re.MULTILINE))
    if md_count >= 2:
        return FormatType.MARKDOWN
    
    return FormatType.TEXT


def score_completeness(content: str, format_type: FormatType) -> Tuple[float, str]:
    """
    Score completeness (0.30 weight).
    Check if the submission has all expected components.
    """
    score = 0.0
    feedback = []
    
    if format_type == FormatType.JSON:
        try:
            data = json.loads(content)
            # Check for common required fields
            if isinstance(data, dict):
                required_fields = ["id", "name", "data", "value", "type"]
                found = sum(1 for f in required_fields if f in data)
                score = found / len(required_fields)
                if score < 1.0:
                    missing = [f for f in required_fields if f not in data]
                    feedback.append(f"Missing common fields: {missing[:3]}")
            elif isinstance(data, list):
                score = 1.0 if len(data) > 0 else 0.0
                if len(data) == 0:
                    feedback.append("Empty array")
            else:
                score = 0.5
                feedback.append("JSON structure is minimal")
        except:
            score = 0.0
            feedback.append("Invalid JSON structure")
    
    elif format_type == FormatType.MARKDOWN:
        # Check for common markdown elements
        elements = {
            "header": bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE)),
            "paragraph": len(re.findall(r'\n\n', content)) > 0,
            "list": bool(re.search(r'^[-*+]\s+', content, re.MULTILINE)),
            "link": bool(re.search(r'\[.*\]\(.*\)', content)),
            "code": bool(re.search(r'```', content)),
        }
        score = sum(elements.values()) / len(elements)
        missing = [k for k, v in elements.items() if not v]
        if missing:
            feedback.append(f"Consider adding: {', '.join(missing[:3])}")
    
    elif format_type == FormatType.CODE:
        # Check for code completeness
        checks = {
            "structure": len(content.split('\n')) > 5,
            "functions": bool(re.search(r'def |function |func ', content)),
            "comments": bool(re.search(r'#|//|/\*|\*/', content)),
            "returns": bool(re.search(r'return|yield', content)),
        }
        score = sum(checks.values()) / len(checks)
        missing = [k for k, v in checks.items() if not v]
        if missing:
            feedback.append(f"Consider adding: {', '.join(missing[:3])}")
    
    else:  # TEXT
        words = len(content.split())
        sentences = len(re.split(r'[.!?]+', content))
        paragraphs = len(content.split('\n\n'))
        
        # Score based on content depth
        word_score = min(1.0, words / 100)  # 100+ words is good
        sentence_score = min(1.0, sentences / 5)  # 5+ sentences is good
        paragraph_score = min(1.0, paragraphs / 2)  # 2+ paragraphs is good
        
        score = (word_score + sentence_score + paragraph_score) / 3
        
        if words < 50:
            feedback.append("Content seems brief, consider expanding")
    
    return round(score, 3), "; ".join(feedback) if feedback else "Complete"


def score_format_compliance(content: str, format_type: FormatType) -> Tuple[float, str]:
    """
    Score format compliance (0.20 weight).
    Check if the format rules are followed correctly.
    """
    score = 1.0
    feedback = []
    
    if format_type == FormatType.JSON:
        try:
            json.loads(content)
            # Check for proper indentation
            if '\n' in content and not content.startswith('{\n'):
                score -= 0.1
                feedback.append("Consider using consistent formatting")
        except json.JSONDecodeError as e:
            score = 0.0
            feedback.append(f"JSON parse error: {str(e)[:50]}")
    
    elif format_type == FormatType.MARKDOWN:
        issues = []
        
        # Check for proper header spacing
        headers = re.findall(r'^#{1,6}[^\s#]', content, re.MULTILINE)
        if headers:
            issues.append("Headers need space after #")
            score -= 0.2
        
        # Check for unclosed code blocks
        code_blocks = content.count('```')
        if code_blocks % 2 != 0:
            issues.append("Unclosed code block")
            score -= 0.3
        
        # Check for broken links
        broken_links = re.findall(r'\[([^\]]*)\]\(\s*\)', content)
        if broken_links:
            issues.append(f"Empty links found")
            score -= 0.1
        
        feedback.extend(issues)
    
    elif format_type == FormatType.CODE:
        # Basic syntax checks
        lines = content.split('\n')
        
        # Check for consistent indentation
        indent_types = set()
        for line in lines:
            if line and not line[0].isspace():
                continue
            if line.startswith('    '):
                indent_types.add('spaces')
            elif line.startswith('\t'):
                indent_types.add('tabs')
        
        if len(indent_types) > 1:
            score -= 0.2
            feedback.append("Mixed tabs and spaces")
        
        # Check for trailing whitespace
        trailing = sum(1 for l in lines if l and l[-1] == ' ')
        if trailing > len(lines) * 0.1:
            score -= 0.1
            feedback.append("Trailing whitespace detected")
    
    else:  # TEXT
        # Check for basic text quality
        issues = []
        
        # Multiple spaces
        if '  ' in content:
            issues.append("Multiple consecutive spaces")
            score -= 0.1
        
        # Proper sentence endings
        sentences = re.split(r'[.!?]', content)
        if len(sentences) > 1:
            proper_endings = len(re.findall(r'[.!?]\s+[A-Z]', content))
            if proper_endings < len(sentences) * 0.5:
                issues.append("Inconsistent sentence endings")
                score -= 0.1
        
        feedback.extend(issues)
    
    return round(max(0, score), 3), "; ".join(feedback) if feedback else "Format compliant"


def score_coverage(content: str, format_type: FormatType) -> Tuple[float, str]:
    """
    Score coverage (0.25 weight).
    Check breadth and depth of content.
    """
    score = 0.0
    feedback = []
    
    # Count meaningful elements
    word_count = len(content.split())
    char_count = len(content)
    
    # Base coverage score
    if format_type == FormatType.JSON:
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # Count keys and nested depth
                key_count = len(data.keys())
                depth = get_dict_depth(data)
                score = min(1.0, (key_count / 10) + (depth / 5)) / 2
            elif isinstance(data, list):
                score = min(1.0, len(data) / 10)
            else:
                score = 0.5
        except:
            score = 0.0
    
    elif format_type == FormatType.CODE:
        # Count functions, classes, variables
        functions = len(re.findall(r'def |function |func ', content))
        classes = len(re.findall(r'class ', content))
        variables = len(re.findall(r'\b(var|let|const|int|string|float)\s+\w+', content))
        
        total = functions + classes * 2 + variables / 5
        score = min(1.0, total / 10)
        
        if functions == 0 and classes == 0:
            feedback.append("No functions or classes found")
    
    elif format_type == FormatType.MARKDOWN:
        # Count sections, links, images
        sections = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        links = len(re.findall(r'\[.*\]\(.*\)', content))
        images = len(re.findall(r'!\[.*\]\(.*\)', content))
        code_blocks = content.count('```') // 2
        
        total = sections + links / 2 + images + code_blocks
        score = min(1.0, total / 8)
    
    else:  # TEXT
        # Word count and vocabulary diversity
        words = content.lower().split()
        unique_words = len(set(words))
        
        # Vocabulary diversity score
        diversity = unique_words / max(1, len(words))
        length_score = min(1.0, word_count / 200)
        
        score = (diversity + length_score) / 2
        
        if diversity < 0.3:
            feedback.append("Low vocabulary diversity")
    
    return round(score, 3), "; ".join(feedback) if feedback else "Good coverage"


def get_dict_depth(d: dict, depth: int = 0) -> int:
    """Get the maximum depth of a nested dictionary."""
    if not isinstance(d, dict) or not d:
        return depth
    return max(get_dict_depth(v, depth + 1) for v in d.values())


def score_clarity(content: str, format_type: FormatType) -> Tuple[float, str]:
    """
    Score clarity (0.15 weight).
    Check readability and organization.
    """
    score = 1.0
    feedback = []
    
    # Check for clear structure
    lines = content.split('\n')
    
    # Average line length (too long = hard to read)
    avg_line_len = sum(len(l) for l in lines) / max(1, len(lines))
    if avg_line_len > 100:
        score -= 0.2
        feedback.append("Long lines reduce readability")
    
    # Check for section breaks (blank lines)
    blank_lines = sum(1 for l in lines if not l.strip())
    if blank_lines < len(lines) * 0.1:
        score -= 0.1
        feedback.append("Add more paragraph breaks")
    
    # Check for very long paragraphs
    paragraphs = content.split('\n\n')
    long_paras = sum(1 for p in paragraphs if len(p.split()) > 100)
    if long_paras > 0:
        score -= 0.1 * long_paras
        feedback.append("Break up long paragraphs")
    
    # Format-specific clarity checks
    if format_type == FormatType.CODE:
        # Check for comments
        comment_lines = len(re.findall(r'^\s*(#|//|/\*|\*/)', content, re.MULTILINE))
        total_lines = len([l for l in lines if l.strip()])
        
        if total_lines > 10 and comment_lines < total_lines * 0.1:
            score -= 0.2
            feedback.append("Add more code comments")
    
    # Check for unclear abbreviations
    abbreviations = re.findall(r'\b[A-Z]{2,}\b', content)
    if len(abbreviations) > 10:
        feedback.append("Many abbreviations - consider defining them")
    
    return round(max(0, score), 3), "; ".join(feedback) if feedback else "Clear and readable"


def score_validity(content: str, format_type: FormatType) -> Tuple[float, str]:
    """
    Score validity (0.10 weight).
    Check for logical consistency and errors.
    """
    score = 1.0
    feedback = []
    
    if format_type == FormatType.JSON:
        try:
            data = json.loads(content)
            # Check for null or empty values
            null_count = count_nulls(data)
            if null_count > 0:
                score -= 0.1 * min(null_count, 5)
                feedback.append(f"Found {null_count} null/empty values")
        except json.JSONDecodeError as e:
            score = 0.0
            feedback.append(f"Invalid JSON: {str(e)[:50]}")
    
    elif format_type == FormatType.CODE:
        # Check for common code issues
        issues = []
        
        # Unclosed brackets
        open_brackets = content.count('(') + content.count('[') + content.count('{')
        close_brackets = content.count(')') + content.count(']') + content.count('}')
        if open_brackets != close_brackets:
            issues.append("Mismatched brackets")
            score -= 0.3
        
        # Empty blocks
        if re.search(r'\{\s*\}', content):
            issues.append("Empty code blocks")
            score -= 0.1
        
        # Unused imports (simple check)
        imports = re.findall(r'import\s+(\w+)', content)
        for imp in imports[:5]:  # Check first 5 imports
            if imp not in content[content.find(imp) + len(imp):]:
                issues.append(f"Potentially unused: {imp}")
                score -= 0.05
        
        feedback.extend(issues)
    
    elif format_type == FormatType.MARKDOWN:
        # Check for broken markdown
        issues = []
        
        # Unclosed formatting
        asterisks = content.count('**')
        if asterisks % 2 != 0:
            issues.append("Unclosed bold formatting")
            score -= 0.2
        
        # Broken links
        if re.search(r'\]\([^)]*$', content, re.MULTILINE):
            issues.append("Broken link syntax")
            score -= 0.2
        
        feedback.extend(issues)
    
    else:  # TEXT
        # Check for common text issues
        issues = []
        
        # Repeated words
        words = content.lower().split()
        repeated = sum(1 for i in range(len(words)-1) if words[i] == words[i+1])
        if repeated > 2:
            issues.append("Repeated words found")
            score -= 0.1
        
        # Typos (simple: check for common patterns)
        if re.search(r'\b(teh|adn|taht|wiht)\b', content.lower()):
            issues.append("Possible typos detected")
            score -= 0.1
        
        feedback.extend(issues)
    
    return round(max(0, score), 3), "; ".join(feedback) if feedback else "Valid"


def count_nulls(data: Any) -> int:
    """Count null/empty values in a data structure."""
    count = 0
    if data is None:
        return 1
    if isinstance(data, dict):
        for v in data.values():
            if v is None or v == "" or v == []:
                count += 1
            elif isinstance(v, (dict, list)):
                count += count_nulls(v)
    elif isinstance(data, list):
        for item in data:
            if item is None or item == "" or item == {}:
                count += 1
            elif isinstance(item, (dict, list)):
                count += count_nulls(item)
    return count


def get_quality_rating(score: float) -> str:
    """Convert numeric score to quality rating."""
    for threshold, rating in QUALITY_RATINGS:
        if score >= threshold:
            return rating
    return "Poor"


def score_submission(
    content: str,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD
) -> ScoringResult:
    """
    Main scoring function.
    
    Args:
        content: The submission content to score
        pass_threshold: Minimum score to pass (default 0.6)
    
    Returns:
        ScoringResult with weighted score and per-dimension feedback
    """
    # Detect format
    format_type = detect_format(content)
    
    # Score each dimension
    dimensions = {
        "completeness": score_completeness,
        "format_compliance": score_format_compliance,
        "coverage": score_coverage,
        "clarity": score_clarity,
        "validity": score_validity,
    }
    
    scores = {}
    feedback_list = []
    weighted_sum = 0.0
    
    for dim_name, scorer in dimensions.items():
        score, feedback = scorer(content, format_type)
        scores[dim_name] = score
        if feedback and feedback != "Complete" and feedback != "Format compliant" and \
           feedback != "Good coverage" and feedback != "Clear and readable" and feedback != "Valid":
            feedback_list.append(f"{dim_name}: {feedback}")
        weighted_sum += score * DIMENSION_WEIGHTS[dim_name]
    
    # Calculate final weighted score
    weighted_score = round(weighted_sum, 3)
    quality_rating = get_quality_rating(weighted_score)
    
    return ScoringResult(
        weighted_score=weighted_score,
        quality_rating=quality_rating,
        scores=scores,
        feedback=feedback_list if feedback_list else ["All dimensions satisfactory"],
        pass_threshold=weighted_score >= pass_threshold,
        format_detected=format_type.value,
    )


def score_batch(
    submissions: List[str],
    pass_threshold: float = DEFAULT_PASS_THRESHOLD
) -> List[ScoringResult]:
    """Score multiple submissions."""
    return [score_submission(s, pass_threshold) for s in submissions]


# Example usage and test
if __name__ == "__main__":
    # Test examples
    examples = [
        # JSON example
        json.dumps({
            "id": "test-001",
            "name": "Sample Data",
            "value": 42,
            "type": "example",
            "data": {"nested": True}
        }),
        
        # Markdown example
        """# Sample Document

This is a **sample** markdown document.

## Features

- Item 1
- Item 2
- Item 3

[Learn more](https://example.com)

```python
def hello():
    print("Hello, World!")
```
""",
        
        # Code example
        """
def calculate_score(data: dict) -> float:
    '''Calculate the weighted score.'''
    total = 0.0
    for key, value in data.items():
        total += value
    return total

# Main
if __name__ == "__main__":
    result = calculate_score({"a": 1, "b": 2})
    print(f"Score: {result}")
""",
        
        # Text example
        """This is a sample text submission. It contains multiple sentences that 
express a coherent idea. The text should be scored based on its completeness,
readability, and overall quality.

The second paragraph continues the discussion. Good text submissions should
have proper structure and clear communication of ideas.""",
    ]
    
    print("Quality Scoring Demo\n" + "="*50)
    
    for i, example in enumerate(examples, 1):
        result = score_submission(example)
        print(f"\nExample {i} ({result.format_detected}):")
        print(f"  Weighted Score: {result.weighted_score}")
        print(f"  Quality Rating: {result.quality_rating}")
        print(f"  Pass Threshold: {'✓' if result.pass_threshold else '✗'}")
        print(f"  Scores by Dimension:")
        for dim, score in result.scores.items():
            print(f"    {dim}: {score}")
        print(f"  Feedback: {result.feedback[:2]}")