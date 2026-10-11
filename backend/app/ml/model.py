import torch
import torch.nn as nn
from torch.nn import functional as F
from typing import Optional, Tuple
import math


class HTTPTransformer(nn.Module):
    """
    Lightweight Transformer for HTTP request classification.
    
    Uses byte-level or subword tokenization with security-relevant vocabulary.
    """

    def __init__(
        self,
        vocab_size: int = 256,  # Byte-level
        d_model: int = 256,
        n_heads: int = 4,
        n_layers: int = 4,
        d_ff: int = 1024,
        max_seq_len: int = 512,
        num_classes: int = 7,
        dropout: float = 0.1,
        use_byte_embeddings: bool = True,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.num_classes = num_classes
        self.use_byte_embeddings = use_byte_embeddings

        # Token embeddings
        if use_byte_embeddings:
            self.token_embedding = nn.Embedding(vocab_size, d_model)
        else:
            self.token_embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(d_model, max_seq_len, dropout)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Classification head
        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_ff // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff // 2, num_classes),
        )

        # Anomaly detection head (reconstruction-based)
        self.anomaly_head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_ff // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff // 2, 1),
            nn.Sigmoid(),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        return_hidden: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass.
        
        Args:
            input_ids: (batch_size, seq_len)
            attention_mask: (batch_size, seq_len) - 1 for real tokens, 0 for padding
            
        Returns:
            logits: (batch_size, num_classes)
            anomaly_score: (batch_size, 1)
            hidden_states: (batch_size, seq_len, d_model) if return_hidden
        """
        batch_size, seq_len = input_ids.shape

        # Embeddings
        x = self.token_embedding(input_ids) * math.sqrt(self.d_model)
        x = self.pos_encoding(x)

        # Attention mask for padding
        if attention_mask is not None:
            # Convert to transformer format (True = attend, False = mask)
            src_key_padding_mask = ~attention_mask.bool()
        else:
            src_key_padding_mask = None

        # Transformer
        hidden = self.transformer(x, src_key_padding_mask=src_key_padding_mask)

        # Pool (use [CLS]-like first token or mean pooling)
        pooled = hidden[:, 0]  # First token as aggregate representation

        # Classification
        logits = self.classifier(pooled)

        # Anomaly score
        anomaly = self.anomaly_head(pooled)

        if return_hidden:
            return logits, anomaly, hidden
        return logits, anomaly, None


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class HTTPTransformerConfig:
    """Configuration for HTTP Transformer."""

    def __init__(
        self,
        vocab_size: int = 256,
        d_model: int = 256,
        n_heads: int = 4,
        n_layers: int = 4,
        d_ff: int = 1024,
        max_seq_len: int = 512,
        num_classes: int = 7,
        dropout: float = 0.1,
        use_byte_embeddings: bool = True,
        class_names: Optional[list] = None,
    ):
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.d_ff = d_ff
        self.max_seq_len = max_seq_len
        self.num_classes = num_classes
        self.dropout = dropout
        self.use_byte_embeddings = use_byte_embeddings
        self.class_names = class_names or [
            "benign",
            "sql_injection",
            "xss",
            "path_traversal",
            "command_injection",
            "other_malicious",
            "anomalous",
        ]

    def to_dict(self) -> dict:
        return {
            "vocab_size": self.vocab_size,
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "n_layers": self.n_layers,
            "d_ff": self.d_ff,
            "max_seq_len": self.max_seq_len,
            "num_classes": self.num_classes,
            "dropout": self.dropout,
            "use_byte_embeddings": self.use_byte_embeddings,
            "class_names": self.class_names,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HTTPTransformerConfig":
        return cls(**d)


def create_model(config: HTTPTransformerConfig) -> HTTPTransformer:
    """Factory function to create model from config."""
    return HTTPTransformer(
        vocab_size=config.vocab_size,
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_layers,
        d_ff=config.d_ff,
        max_seq_len=config.max_seq_len,
        num_classes=config.num_classes,
        dropout=config.dropout,
        use_byte_embeddings=config.use_byte_embeddings,
    )


def load_model(checkpoint_path: str, device: torch.device, config: Optional[HTTPTransformerConfig] = None) -> Tuple[HTTPTransformer, HTTPTransformerConfig]:
    """Load model from checkpoint."""
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    
    if config is None:
        config = HTTPTransformerConfig.from_dict(checkpoint["config"])
    
    model = create_model(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    
    return model, config


def save_model(
    model: HTTPTransformer,
    config: HTTPTransformerConfig,
    checkpoint_path: str,
    optimizer_state: Optional[dict] = None,
    epoch: Optional[int] = None,
    metrics: Optional[dict] = None,
) -> None:
    """Save model checkpoint."""
    checkpoint = {
        "config": config.to_dict(),
        "model_state_dict": model.state_dict(),
    }
    if optimizer_state:
        checkpoint["optimizer_state_dict"] = optimizer_state
    if epoch is not None:
        checkpoint["epoch"] = epoch
    if metrics:
        checkpoint["metrics"] = metrics
    
    torch.save(checkpoint, checkpoint_path)