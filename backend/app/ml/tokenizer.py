from typing import List, Dict, Optional, Tuple, Any
import torch
import re


class ByteLevelTokenizer:
    """
    Byte-level tokenizer for HTTP requests.
    
    Preserves security-relevant symbols by operating at byte level.
    Special tokens for structure markers.
    """

    # Special tokens
    PAD_TOKEN = 0
    CLS_TOKEN = 1
    SEP_TOKEN = 2
    UNK_TOKEN = 3
    MASK_TOKEN = 4

    # Structure markers (mapped to high byte values + offset)
    STRUCTURE_TOKENS = {
        "METHOD": 256,
        "PATH": 257,
        "QUERY": 258,
        "HEADER": 259,
        "BODY": 260,
        "CONTENT_TYPE": 261,
    }

    def __init__(
        self,
        max_length: int = 512,
        add_structure_markers: bool = True,
    ):
        self.max_length = max_length
        self.add_structure_markers = add_structure_markers
        self.vocab_size = 262  # 256 bytes + 6 structure tokens

        # Byte to token mapping (identity for bytes 0-255)
        self.byte_to_token = {i: i for i in range(256)}
        # Structure tokens
        for name, token_id in self.STRUCTURE_TOKENS.items():
            self.byte_to_token[name] = token_id

        self.token_to_byte = {v: k for k, v in self.byte_to_token.items()}

    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs."""
        tokens = [self.CLS_TOKEN]

        if self.add_structure_markers:
            # This expects pre-formatted sequence like "METHOD=GET PATH=/ QUERY=..."
            # We'll parse and add markers
            parts = self._parse_sequence(text)
            for marker, value in parts:
                if marker in self.STRUCTURE_TOKENS:
                    tokens.append(self.STRUCTURE_TOKENS[marker])
                # Encode value as bytes
                for byte in value.encode("utf-8", errors="replace"):
                    tokens.append(byte)
                tokens.append(self.SEP_TOKEN)
        else:
            # Simple byte encoding
            for byte in text.encode("utf-8", errors="replace"):
                tokens.append(byte)

        # Truncate
        if len(tokens) > self.max_length:
            tokens = tokens[:self.max_length - 1] + [self.SEP_TOKEN]

        # Pad
        if len(tokens) < self.max_length:
            tokens.extend([self.PAD_TOKEN] * (self.max_length - len(tokens)))

        return tokens

    def _parse_sequence(self, text: str) -> List[Tuple[str, str]]:
        """Parse structured sequence into (marker, value) pairs."""
        # Expected format: "METHOD=GET PATH=/search QUERY=q=laptop BODY=..."
        parts = []
        # Split by structure markers
        pattern = r"(METHOD|PATH|QUERY|HEADER|BODY|CONTENT_TYPE)=([^ ]*)"
        matches = re.findall(pattern, text)
        for marker, value in matches:
            parts.append((marker, value))
        return parts

    def decode(self, tokens: List[int]) -> str:
        """Decode token IDs to text (approximate)."""
        bytes_list = []
        for token in tokens:
            if token == self.PAD_TOKEN:
                break
            if token in self.token_to_byte:
                val = self.token_to_byte[token]
                if isinstance(val, int) and 0 <= val < 256:
                    bytes_list.append(val)
                elif isinstance(val, str) and val in self.STRUCTURE_TOKENS:
                    bytes_list.append(ord("|"))  # Visual separator
        return bytes(bytes_list).decode("utf-8", errors="replace")

    def encode_batch(self, texts: List[str]) -> torch.Tensor:
        """Encode batch of texts."""
        encoded = [self.encode(text) for text in texts]
        return torch.tensor(encoded, dtype=torch.long)

    def get_attention_mask(self, tokens: List[int]) -> List[int]:
        """Generate attention mask (1 for real tokens, 0 for padding)."""
        return [1 if t != self.PAD_TOKEN else 0 for t in tokens]

    def get_attention_mask_batch(self, token_batch: torch.Tensor) -> torch.Tensor:
        """Generate attention mask for batch."""
        return (token_batch != self.PAD_TOKEN).long()


class HTTPRequestTokenizer:
    """
    High-level tokenizer for HTTP requests.
    Converts request dict to structured sequence string.
    """

    def __init__(self, max_length: int = 512):
        self.tokenizer = ByteLevelTokenizer(max_length=max_length)
        self.max_length = max_length

    def tokenize_request(self, request: Dict[str, Any]) -> torch.Tensor:
        """Tokenize a normalized request dict."""
        sequence = self._request_to_sequence(request)
        tokens = self.tokenizer.encode(sequence)
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)

    def tokenize_batch(self, requests: List[Dict[str, Any]]) -> Tuple[torch.Tensor, torch.Tensor]:
        """Tokenize batch of requests."""
        sequences = [self._request_to_sequence(r) for r in requests]
        token_batch = self.tokenizer.encode_batch(sequences)
        attention_mask = self.tokenizer.get_attention_mask_batch(token_batch)
        return token_batch, attention_mask

    def _request_to_sequence(self, request: Dict[str, Any]) -> str:
        """Convert request dict to structured sequence string."""
        parts = []

        method = request.get("method", "GET")
        parts.append(f"METHOD={method}")

        path = request.get("path", "/")
        parts.append(f"PATH={path}")

        query = request.get("query", "")
        if query:
            parts.append(f"QUERY={query}")

        content_type = request.get("headers", {}).get("content-type", "none")
        parts.append(f"CONTENT_TYPE={content_type}")

        body = request.get("body", "")
        if body:
            parts.append(f"BODY={body}")

        return " ".join(parts)


def create_tokenizer(max_length: int = 512) -> HTTPRequestTokenizer:
    """Factory function."""
    return HTTPRequestTokenizer(max_length=max_length)