from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml
import re
import logging
from pathlib import Path

from app.config import get_settings
from app.database import get_db_context
from app.models import EndpointProfile, SensitivityEnum

logger = logging.getLogger(__name__)
settings = get_settings()


class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ParameterSpec:
    name: str
    param_type: ParameterType
    required: bool = False
    location: str = "query"  # query, path, header, cookie
    pattern: Optional[str] = None
    enum: Optional[List[str]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    format: Optional[str] = None


@dataclass
class EndpointSpec:
    path_template: str
    method: str
    parameters: List[ParameterSpec] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    security_requirements: List[Dict[str, List[str]]] = field(default_factory=list)
    sensitivity: SensitivityEnum = SensitivityEnum.LOW
    tags: List[str] = field(default_factory=list)
    operation_id: Optional[str] = None


class OpenAPIParser:
    """Parse OpenAPI spec and extract endpoint contracts."""

    def __init__(self):
        self.endpoints: List[EndpointSpec] = []

    def parse(self, spec: Dict[str, Any]) -> List[EndpointSpec]:
        """Parse OpenAPI spec dict."""
        self.endpoints = []

        paths = spec.get("paths", {})
        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        # Global security
        global_security = spec.get("security", [])

        for path_template, path_item in paths.items():
            # Normalize path template (OpenAPI uses {param} format)
            normalized_path = self._normalize_path_template(path_template)

            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    continue

                endpoint = self._parse_operation(
                    normalized_path,
                    method.upper(),
                    operation,
                    components,
                    security_schemes,
                    global_security,
                )
                self.endpoints.append(endpoint)

        return self.endpoints

    def _normalize_path_template(self, path: str) -> str:
        """Convert OpenAPI path template to regex-compatible pattern."""
        # OpenAPI uses {param} - convert to {param} for our matching
        # Keep as-is for now, we'll do pattern matching
        return path

    def _parse_operation(
        self,
        path_template: str,
        method: str,
        operation: Dict[str, Any],
        components: Dict[str, Any],
        security_schemes: Dict[str, Any],
        global_security: List[Dict[str, List[str]]],
    ) -> EndpointSpec:
        """Parse a single operation."""
        # Parameters
        parameters = []
        for param in operation.get("parameters", []):
            param_spec = self._parse_parameter(param, components)
            if param_spec:
                parameters.append(param_spec)

        # Request body
        request_body = None
        if "requestBody" in operation:
            request_body = self._parse_request_body(operation["requestBody"], components)

        # Responses
        responses = operation.get("responses", {})

        # Security
        security = operation.get("security", global_security)
        auth_required = len(security) > 0

        # Sensitivity from tags or x-sensitivity extension
        tags = operation.get("tags", [])
        sensitivity = self._determine_sensitivity(tags, operation, path_template)

        return EndpointSpec(
            path_template=path_template,
            method=method,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security_requirements=security,
            sensitivity=sensitivity,
            tags=tags,
            operation_id=operation.get("operationId"),
        )

    def _parse_parameter(
        self,
        param: Dict[str, Any],
        components: Dict[str, Any],
    ) -> Optional[ParameterSpec]:
        """Parse a parameter object."""
        # Handle reference
        if "$ref" in param:
            ref_path = param["$ref"].split("/")
            param = components
            for part in ref_path[1:]:
                param = param.get(part, {})
            if not param:
                return None

        schema = param.get("schema", {})
        param_type = self._map_schema_type(schema)

        return ParameterSpec(
            name=param.get("name", ""),
            param_type=param_type,
            required=param.get("required", False),
            location=param.get("in", "query"),
            pattern=schema.get("pattern"),
            enum=schema.get("enum"),
            minimum=schema.get("minimum"),
            maximum=schema.get("maximum"),
            format=schema.get("format"),
        )

    def _parse_request_body(
        self,
        request_body: Dict[str, Any],
        components: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Parse request body."""
        content = request_body.get("content", {})
        for media_type, media_obj in content.items():
            schema = media_obj.get("schema", {})
            if "$ref" in schema:
                ref_path = schema["$ref"].split("/")
                resolved = components
                for part in ref_path[1:]:
                    resolved = resolved.get(part, {})
                schema = resolved
            return {
                "content_type": media_type,
                "schema": schema,
                "required": request_body.get("required", False),
            }
        return None

    def _map_schema_type(self, schema: Dict[str, Any]) -> ParameterType:
        """Map JSON schema type to ParameterType."""
        schema_type = schema.get("type", "string")
        type_map = {
            "string": ParameterType.STRING,
            "integer": ParameterType.INTEGER,
            "number": ParameterType.NUMBER,
            "boolean": ParameterType.BOOLEAN,
            "array": ParameterType.ARRAY,
            "object": ParameterType.OBJECT,
        }
        return type_map.get(schema_type, ParameterType.STRING)

    def _determine_sensitivity(
        self,
        tags: List[str],
        operation: Dict[str, Any],
        path: str,
    ) -> SensitivityEnum:
        """Determine endpoint sensitivity."""
        # Check explicit extension
        if "x-sensitivity" in operation:
            try:
                return SensitivityEnum(operation["x-sensitivity"])
            except ValueError:
                pass

        # Infer from tags
        tag_str = " ".join(tags).lower()
        path_lower = path.lower()

        if any(kw in tag_str or kw in path_lower for kw in [
            "admin", "payment", "billing", "auth", "password", "secret",
            "export", "delete", "user-management", "security",
        ]):
            return SensitivityEnum.CRITICAL

        if any(kw in tag_str or kw in path_lower for kw in [
            "checkout", "order", "transaction", "account", "profile",
            "settings", "api-key", "webhook",
        ]):
            return SensitivityEnum.HIGH

        if any(kw in tag_str or kw in path_lower for kw in [
            "user", "product", "cart", "search", "dashboard",
        ]):
            return SensitivityEnum.MEDIUM

        return SensitivityEnum.LOW


class ApplicationContextEngine:
    """Engine for application-aware request analysis."""

    def __init__(self):
        self.endpoints: Dict[str, EndpointSpec] = {}  # key: "METHOD:path_template"
        self.path_patterns: List[tuple] = []  # (regex, EndpointSpec)

    def load_from_spec(self, spec: Dict[str, Any]) -> int:
        """Load endpoints from OpenAPI spec."""
        parser = OpenAPIParser()
        endpoints = parser.parse(spec)

        self.endpoints = {}
        self.path_patterns = []

        for ep in endpoints:
            key = f"{ep.method}:{ep.path_template}"
            self.endpoints[key] = ep
            # Compile regex for path matching
            pattern = self._template_to_regex(ep.path_template)
            self.path_patterns.append((re.compile(pattern), ep))

        logger.info(f"Loaded {len(endpoints)} endpoints from OpenAPI spec")
        return len(endpoints)

    def load_from_file(self, file_path: str) -> int:
        """Load from OpenAPI file (JSON or YAML)."""
        path = Path(file_path)
        with open(path) as f:
            if path.suffix in [".yaml", ".yml"]:
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        return self.load_from_spec(spec)

    def _template_to_regex(self, template: str) -> str:
        """Convert path template to regex."""
        # Escape special chars except {param}
        parts = re.split(r"(\{[^}]+\})", template)
        regex_parts = []
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                param_name = part[1:-1]
                regex_parts.append(f"(?P<{param_name}>[^/]+)")
            else:
                regex_parts.append(re.escape(part))
        return "^" + "".join(regex_parts) + "$"

    def match_endpoint(self, method: str, path: str) -> Optional[EndpointSpec]:
        """Match request to endpoint spec."""
        key = f"{method}:{path}"
        if key in self.endpoints:
            return self.endpoints[key]

        # Try pattern matching
        for pattern, ep in self.path_patterns:
            if ep.method == method and pattern.match(path):
                return ep

        return None

    def analyze_request(
        self,
        request: Dict[str, Any],
        matched_endpoint: Optional[EndpointSpec] = None,
    ) -> Dict[str, Any]:
        """Analyze request against endpoint contract."""
        if matched_endpoint is None:
            matched_endpoint = self.match_endpoint(
                request.get("method", ""),
                request.get("path", ""),
            )

        if not matched_endpoint:
            return {
                "score": 0.0,
                "reasons": ["No matching endpoint contract"],
                "matched": False,
            }

        reasons = []
        scores = []

        # Check path parameters
        path_params = self._extract_path_params(request.get("path", ""), matched_endpoint)
        for param in matched_endpoint.parameters:
            if param.location == "path":
                value = path_params.get(param.name)
                if value is not None:
                    violation = self._validate_parameter(value, param)
                    if violation:
                        scores.append(0.8)
                        reasons.append(f"Path parameter '{param.name}': {violation}")

        # Check query parameters
        query_params = self._parse_query(request.get("query", ""))
        for param in matched_endpoint.parameters:
            if param.location == "query":
                value = query_params.get(param.name)
                if param.required and value is None:
                    scores.append(0.6)
                    reasons.append(f"Missing required query parameter: {param.name}")
                elif value is not None:
                    violation = self._validate_parameter(value, param)
                    if violation:
                        scores.append(0.7)
                        reasons.append(f"Query parameter '{param.name}': {violation}")

        # Check unexpected parameters
        expected_query = {p.name for p in matched_endpoint.parameters if p.location == "query"}
        for param_name in query_params:
            if param_name not in expected_query:
                scores.append(0.4)
                reasons.append(f"Unexpected query parameter: {param_name}")

        # Check authentication
        if matched_endpoint.security_requirements:
            auth_present = self._check_authentication(request)
            if not auth_present:
                scores.append(0.7)
                reasons.append("Authentication required but not present")

        # Check content type
        if matched_endpoint.request_body:
            content_type = request.get("headers", {}).get("content-type", "")
            expected_types = [matched_endpoint.request_body.get("content_type", "")]
            if expected_types and expected_types[0] not in content_type and content_type:
                scores.append(0.5)
                reasons.append(f"Unexpected content type: {content_type}")

        # Check method
        # (already matched by method)

        # Sensitivity boost
        if matched_endpoint.sensitivity in [SensitivityEnum.HIGH, SensitivityEnum.CRITICAL]:
            if scores:
                scores = [min(1.0, s * 1.2) for s in scores]

        final_score = max(scores) if scores else 0.0
        if len(scores) > 1:
            final_score = min(1.0, final_score * 1.1)

        return {
            "score": round(final_score, 3),
            "reasons": reasons,
            "matched": True,
            "endpoint": {
                "path": matched_endpoint.path_template,
                "method": matched_endpoint.method,
                "sensitivity": matched_endpoint.sensitivity.value,
            },
        }

    def _extract_path_params(self, path: str, endpoint: EndpointSpec) -> Dict[str, str]:
        """Extract path parameter values from request path."""
        pattern = self._template_to_regex(endpoint.path_template)
        match = re.match(pattern, path)
        if match:
            return match.groupdict()
        return {}

    def _parse_query(self, query: str) -> Dict[str, str]:
        """Parse query string to dict (first value)."""
        from urllib.parse import parse_qs
        parsed = parse_qs(query, keep_blank_values=True)
        return {k: v[0] for k, v in parsed.items()}

    def _validate_parameter(self, value: str, param: ParameterSpec) -> Optional[str]:
        """Validate parameter value against spec."""
        # Type validation
        if param.param_type == ParameterType.INTEGER:
            try:
                int(value)
            except ValueError:
                return f"expected integer, got '{value[:50]}'"
        elif param.param_type == ParameterType.NUMBER:
            try:
                float(value)
            except ValueError:
                return f"expected number, got '{value[:50]}'"
        elif param.param_type == ParameterType.BOOLEAN:
            if value.lower() not in ["true", "false", "1", "0"]:
                return f"expected boolean, got '{value[:50]}'"

        # Pattern validation
        if param.pattern:
            if not re.match(param.pattern, value):
                return f"value '{value[:50]}' does not match pattern"

        # Enum validation
        if param.enum and value not in param.enum:
            return f"value '{value[:50]}' not in allowed values: {param.enum}"

        # Range validation
        if param.param_type in [ParameterType.INTEGER, ParameterType.NUMBER]:
            try:
                num_val = float(value)
                if param.minimum is not None and num_val < param.minimum:
                    return f"value {num_val} below minimum {param.minimum}"
                if param.maximum is not None and num_val > param.maximum:
                    return f"value {num_val} above maximum {param.maximum}"
            except ValueError:
                pass

        # Format validation
        if param.format == "email" and "@" not in value:
            return "invalid email format"
        if param.format == "uuid":
            uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            if not re.match(uuid_pattern, value, re.IGNORECASE):
                return "invalid UUID format"

        return None

    def _check_authentication(self, request: Dict[str, Any]) -> bool:
        """Check if request has authentication."""
        headers = request.get("headers", {})
        # Check common auth headers
        if "authorization" in headers:
            return True
        if "x-api-key" in headers:
            return True
        if "cookie" in headers and "session" in headers["cookie"].lower():
            return True
        return False

    async def persist_endpoints(self) -> int:
        """Persist endpoints to database."""
        count = 0
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                for key, ep in self.endpoints.items():
                    result = await db.execute(
                        select(EndpointProfile).where(
                            EndpointProfile.path_template == ep.path_template,
                            EndpointProfile.method == ep.method,
                        )
                    )
                    db_ep = result.scalar_one_or_none()

                    if not db_ep:
                        db_ep = EndpointProfile(
                            path_template=ep.path_template,
                            method=ep.method,
                        )
                        db.add(db_ep)

                    db_ep.expected_parameters = {
                        "parameters": [
                            {
                                "name": p.name,
                                "type": p.param_type.value,
                                "required": p.required,
                                "location": p.location,
                                "pattern": p.pattern,
                                "enum": p.enum,
                            }
                            for p in ep.parameters
                        ],
                        "request_body": ep.request_body,
                    }
                    db_ep.authentication_required = len(ep.security_requirements) > 0
                    db_ep.sensitivity_level = ep.sensitivity
                    db_ep.allowed_content_types = [
                        ep.request_body.get("content_type") if ep.request_body else None
                    ]
                    count += 1

                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist endpoints: {e}")

        return count

    def get_endpoints_summary(self) -> List[Dict[str, Any]]:
        """Get summary for UI."""
        return [
            {
                "path": ep.path_template,
                "method": ep.method,
                "parameters": len(ep.parameters),
                "auth_required": len(ep.security_requirements) > 0,
                "sensitivity": ep.sensitivity.value,
                "tags": ep.tags,
            }
            for ep in self.endpoints.values()
        ]


# Singleton
_app_context: Optional[ApplicationContextEngine] = None


def get_app_context() -> ApplicationContextEngine:
    global _app_context
    if _app_context is None:
        _app_context = ApplicationContextEngine()
    return _app_context