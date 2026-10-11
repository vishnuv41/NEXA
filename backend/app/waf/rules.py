import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class RuleCategory(str, Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    MALFORMED = "malformed"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class Rule:
    id: str
    name: str
    category: RuleCategory
    pattern: re.Pattern
    severity: float = 0.8
    description: str = ""
    enabled: bool = True


@dataclass
class RuleMatch:
    rule_id: str
    rule_name: str
    category: RuleCategory
    severity: float
    matched_content: str
    location: str


class RuleEngine:
    """Deterministic rule engine for known attack patterns."""

    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load built-in detection rules."""
        rules = [
            # SQL Injection
            Rule(
                id="sqli_001",
                name="SQL Union Select",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)\bunion\s+select\b", re.IGNORECASE),
                severity=0.9,
                description="UNION SELECT SQL injection attempt",
            ),
            Rule(
                id="sqli_002",
                name="SQL Comment",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)(--|#|/\*|\*/)", re.IGNORECASE),
                severity=0.7,
                description="SQL comment sequence",
            ),
            Rule(
                id="sqli_003",
                name="SQL OR 1=1",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)\bor\s+1\s*=\s*1\b", re.IGNORECASE),
                severity=0.85,
                description="Classic OR 1=1 bypass",
            ),
            Rule(
                id="sqli_004",
                name="SQL Drop Table",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)\bdrop\s+table\b", re.IGNORECASE),
                severity=0.95,
                description="DROP TABLE statement",
            ),
            Rule(
                id="sqli_005",
                name="SQL Information Schema",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)information_schema\.", re.IGNORECASE),
                severity=0.8,
                description="Information schema enumeration",
            ),
            Rule(
                id="sqli_006",
                name="SQL Sleep/Benchmark",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)\b(sleep|benchmark)\s*\(", re.IGNORECASE),
                severity=0.9,
                description="Time-based blind SQL injection",
            ),
            Rule(
                id="sqli_007",
                name="SQL Quote Injection",
                category=RuleCategory.SQL_INJECTION,
                pattern=re.compile(r"(?i)('\s*;\s*--)|('\s*or\s+'1'='1)", re.IGNORECASE),
                severity=0.85,
                description="Quote-based SQL injection",
            ),

            # XSS
            Rule(
                id="xss_001",
                name="Script Tag",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)<script\b[^>]*>", re.IGNORECASE),
                severity=0.9,
                description="HTML script tag injection",
            ),
            Rule(
                id="xss_002",
                name="Event Handler",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)\bon\w+\s*=", re.IGNORECASE),
                severity=0.75,
                description="JavaScript event handler",
            ),
            Rule(
                id="xss_003",
                name="Javascript Protocol",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)javascript:", re.IGNORECASE),
                severity=0.8,
                description="JavaScript protocol handler",
            ),
            Rule(
                id="xss_004",
                name="Data URI XSS",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)data:text/html", re.IGNORECASE),
                severity=0.7,
                description="Data URI with HTML content",
            ),
            Rule(
                id="xss_005",
                name="Expression/Import",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)(expression\s*\(|@import)", re.IGNORECASE),
                severity=0.7,
                description="CSS expression or import",
            ),
            Rule(
                id="xss_006",
                name="SVG Onload",
                category=RuleCategory.XSS,
                pattern=re.compile(r"(?i)<svg\b[^>]*onload\s*=", re.IGNORECASE),
                severity=0.85,
                description="SVG onload event handler",
            ),

            # Path Traversal
            Rule(
                id="path_001",
                name="Directory Traversal",
                category=RuleCategory.PATH_TRAVERSAL,
                pattern=re.compile(r"\.\./|\.\.\\", re.IGNORECASE),
                severity=0.85,
                description="Directory traversal sequence",
            ),
            Rule(
                id="path_002",
                name="Encoded Traversal",
                category=RuleCategory.PATH_TRAVERSAL,
                pattern=re.compile(r"%2e%2e%2f|%2e%2e%5c|..%2f|..%5c", re.IGNORECASE),
                severity=0.9,
                description="URL-encoded directory traversal",
            ),
            Rule(
                id="path_003",
                name="Double Encoded Traversal",
                category=RuleCategory.PATH_TRAVERSAL,
                pattern=re.compile(r"%252e%252e%252f", re.IGNORECASE),
                severity=0.95,
                description="Double URL-encoded traversal",
            ),
            Rule(
                id="path_004",
                name="Absolute Path",
                category=RuleCategory.PATH_TRAVERSAL,
                pattern=re.compile(r"^/(etc|proc|var|root|home|windows|system32)/", re.IGNORECASE),
                severity=0.8,
                description="Absolute system path access",
            ),

            # Command Injection
            Rule(
                id="cmd_001",
                name="Command Separator",
                category=RuleCategory.COMMAND_INJECTION,
                pattern=re.compile(r"[;&|`$]\s*(ls|cat|id|whoami|pwd|uname|ps|netstat|curl|wget|nc|bash|sh)", re.IGNORECASE),
                severity=0.9,
                description="Command injection with separator",
            ),
            Rule(
                id="cmd_002",
                name="Subshell",
                category=RuleCategory.COMMAND_INJECTION,
                pattern=re.compile(r"\$\([^)]+\)|`[^`]+`", re.IGNORECASE),
                severity=0.85,
                description="Subshell execution",
            ),
            Rule(
                id="cmd_003",
                name="Pipe to Shell",
                category=RuleCategory.COMMAND_INJECTION,
                pattern=re.compile(r"\|\s*(bash|sh|nc|python|perl)\b", re.IGNORECASE),
                severity=0.9,
                description="Piping to shell interpreter",
            ),

            # Malformed/Suspicious
            Rule(
                id="malformed_001",
                name="Null Byte",
                category=RuleCategory.MALFORMED,
                pattern=re.compile(r"%00|\x00"),
                severity=0.8,
                description="Null byte injection",
            ),
            Rule(
                id="malformed_002",
                name="Excessive Length",
                category=RuleCategory.MALFORMED,
                pattern=re.compile(r".{10000,}"),
                severity=0.6,
                description="Excessively long input",
            ),
            Rule(
                id="malformed_003",
                name="High Entropy",
                category=RuleCategory.MALFORMED,
                pattern=re.compile(r"[A-Za-z0-9+/]{50,}={0,2}"),
                severity=0.5,
                description="Potential encoded payload",
            ),

            # Suspicious Patterns
            Rule(
                id="suspicious_001",
                name="Base64 Encoded Script",
                category=RuleCategory.SUSPICIOUS_PATTERN,
                pattern=re.compile(r"(?i)(PHNjcmlwd|YWxlcnQo|ZG9jdW1lbnQu)"),
                severity=0.75,
                description="Base64 encoded script tag",
            ),
            Rule(
                id="suspicious_002",
                name="Hex Encoded",
                category=RuleCategory.SUSPICIOUS_PATTERN,
                pattern=re.compile(r"(?i)(\\x[0-9a-f]{2}){10,}"),
                severity=0.7,
                description="Hex encoded payload",
            ),
        ]
        self.rules = rules

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        """Enable/disable a rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = enabled
                return True
        return False

    def inspect(self, text: str, location: str = "body") -> List[RuleMatch]:
        """Inspect text against all enabled rules."""
        matches = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            for match in rule.pattern.finditer(text):
                matches.append(RuleMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    category=rule.category,
                    severity=rule.severity,
                    matched_content=match.group()[:100],
                    location=location,
                ))
        return matches

    def inspect_request(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a full normalized request."""
        all_matches = []

        # Check path
        all_matches.extend(self.inspect(normalized.get("path", ""), "path"))

        # Check query
        all_matches.extend(self.inspect(normalized.get("query", ""), "query"))

        # Check body
        all_matches.extend(self.inspect(normalized.get("body", ""), "body"))

        # Check headers (values only)
        for header_name, header_value in normalized.get("headers", {}).items():
            if header_value != "[REDACTED]":
                all_matches.extend(self.inspect(header_value, f"header:{header_name}"))

        # Calculate aggregate score
        if not all_matches:
            return {
                "score": 0.0,
                "matches": [],
                "categories": {},
            }

        # Weight by severity and category
        category_scores: Dict[RuleCategory, float] = {}
        for match in all_matches:
            cat = match.category
            if cat not in category_scores:
                category_scores[cat] = 0.0
            category_scores[cat] = max(category_scores[cat], match.severity)

        # Overall score is max across categories with some combination
        overall_score = max(category_scores.values()) if category_scores else 0.0

        # Boost if multiple categories triggered
        if len(category_scores) > 1:
            overall_score = min(1.0, overall_score * 1.2)

        return {
            "score": round(overall_score, 3),
            "matches": [
                {
                    "rule_id": m.rule_id,
                    "rule_name": m.rule_name,
                    "category": m.category.value,
                    "severity": m.severity,
                    "matched_content": m.matched_content,
                    "location": m.location,
                }
                for m in all_matches
            ],
            "categories": {cat.value: score for cat, score in category_scores.items()},
        }

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules for UI."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category.value,
                "severity": r.severity,
                "description": r.description,
                "enabled": r.enabled,
            }
            for r in self.rules
        ]


# Singleton
_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine