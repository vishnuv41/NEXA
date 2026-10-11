import re
import hashlib
from typing import Dict, List, Optional, Any
from urllib.parse import parse_qs, urlparse
import json


class RequestNormalizer:
    """Normalizes HTTP requests for consistent processing."""

    SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "proxy-authorization",
    }

    SENSITIVE_PARAMS = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "authorization",
        "credit_card",
        "cc_number",
        "cvv",
        "ssn",
    }

    def __init__(self, max_body_length: int = 10000):
        self.max_body_length = max_body_length

    def normalize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a request dictionary."""
        return {
            "method": request.get("method", "").upper(),
            "path": self._normalize_path(request.get("path", "")),
            "query": self._normalize_query(request.get("query", "")),
            "headers": self._normalize_headers(request.get("headers", {})),
            "body": self._normalize_body(request.get("body", "")),
            "source_ip": request.get("source_ip", ""),
            "session_id": request.get("session_id"),
            "user_id": request.get("user_id"),
        }

    def _normalize_path(self, path: str) -> str:
        """Normalize URL path."""
        if not path:
            return "/"
        # Remove duplicate slashes
        path = re.sub(r"/+", "/", path)
        # Ensure leading slash
        if not path.startswith("/"):
            path = "/" + path
        return path

    def _normalize_query(self, query: str) -> str:
        """Normalize query string - sort parameters for consistency."""
        if not query:
            return ""
        parsed = parse_qs(query, keep_blank_values=True)
        # Sort by key for consistent representation
        sorted_params = []
        for key in sorted(parsed.keys()):
            for value in sorted(parsed[key]):
                sorted_params.append(f"{key}={value}")
        return "&".join(sorted_params)

    def _normalize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Normalize headers - lowercase keys, redact sensitive."""
        normalized = {}
        for key, value in headers.items():
            lower_key = key.lower()
            if lower_key in self.SENSITIVE_HEADERS:
                normalized[lower_key] = "[REDACTED]"
            else:
                normalized[lower_key] = value[:500]  # Truncate long values
        return normalized

    def _normalize_body(self, body: str) -> str:
        """Normalize request body."""
        if not body:
            return ""
        # Truncate
        if len(body) > self.max_body_length:
            body = body[:self.max_body_length] + "...[TRUNCATED]"
        # Try to parse JSON for consistent formatting
        try:
            parsed = json.loads(body)
            return json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        except (json.JSONDecodeError, TypeError):
            # Return as-is for non-JSON
            return body

    def create_summary(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe summary for logging/storage."""
        headers_summary = {}
        for k, v in normalized.get("headers", {}).items():
            if k not in self.SENSITIVE_HEADERS:
                headers_summary[k] = v[:100] if isinstance(v, str) else str(v)[:100]

        body = normalized.get("body", "")
        body_summary = body[:500] if body else ""

        return {
            "method": normalized.get("method"),
            "path": normalized.get("path"),
            "query": normalized.get("query")[:500] if normalized.get("query") else "",
            "headers_count": len(normalized.get("headers", {})),
            "body_length": len(body),
            "headers_summary": headers_summary,
            "body_summary": body_summary,
        }

    def to_sequence(self, normalized: Dict[str, Any]) -> str:
        """Convert normalized request to a sequence string for ML model."""
        parts = [
            f"METHOD={normalized.get('method', 'GET')}",
            f"PATH={normalized.get('path', '/')}",
        ]

        query = normalized.get("query", "")
        if query:
            parts.append(f"QUERY={query}")

        content_type = normalized.get("headers", {}).get("content-type", "none")
        parts.append(f"CONTENT_TYPE={content_type}")

        body = normalized.get("body", "")
        if body:
            parts.append(f"BODY={body[:2000]}")

        return " ".join(parts)


class RequestFingerprint:
    """Generate fingerprints for request deduplication and correlation."""

    @staticmethod
    def generate(request: Dict[str, Any]) -> str:
        """Generate a fingerprint for a request."""
        normalized = RequestNormalizer().normalize(request)
        content = RequestNormalizer().to_sequence(normalized)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def generate_structural(request: Dict[str, Any]) -> str:
        """Generate a structural fingerprint (ignores values)."""
        normalized = RequestNormalizer().normalize(request)
        # Replace values with placeholders
        structural = re.sub(r'=[^&\s]+', '=*', normalized.get("query", ""))
        structural = re.sub(r'/[^/]+', '/*', normalized.get("path", "/"))
        content = f"{normalized.get('method')}{structural}{normalized.get('path')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]