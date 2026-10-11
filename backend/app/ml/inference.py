import torch
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
import time
from pathlib import Path

from app.config import get_settings
from app.ml.model import HTTPTransformer, HTTPTransformerConfig, load_model
from app.ml.tokenizer import HTTPRequestTokenizer, create_tokenizer

logger = logging.getLogger(__name__)

settings = get_settings()


class MLInferenceService:
    """Service for running ML inference on HTTP requests."""

    def __init__(self):
        self.model: Optional[HTTPTransformer] = None
        self.config: Optional[HTTPTransformerConfig] = None
        self.tokenizer: Optional[HTTPRequestTokenizer] = None
        self.device: torch.device = torch.device(settings.model_device)
        self._loaded = False
        self.class_names = [
            "benign",
            "sql_injection",
            "xss",
            "path_traversal",
            "command_injection",
            "other_malicious",
            "anomalous",
        ]

    def load(self) -> bool:
        """Load model and tokenizer."""
        try:
            model_path = Path(settings.model_path)
            if not model_path.exists():
                logger.warning(f"Model not found at {model_path}, using bootstrap mode")
                return self._bootstrap()

            self.model, self.config = load_model(str(model_path), self.device)
            self.tokenizer = create_tokenizer(self.config.max_seq_len)
            self.class_names = self.config.class_names
            self._loaded = True
            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return self._bootstrap()

    def _bootstrap(self) -> bool:
        """Create a minimal bootstrap model for development."""
        logger.info("Creating bootstrap model")
        self.config = HTTPTransformerConfig()
        self.model = HTTPTransformer(
            vocab_size=self.config.vocab_size,
            d_model=self.config.d_model,
            n_heads=self.config.n_heads,
            n_layers=self.config.n_layers,
            d_ff=self.config.d_ff,
            max_seq_len=self.config.max_seq_len,
            num_classes=self.config.num_classes,
            dropout=self.config.dropout,
        )
        self.model.to(self.device)
        self.model.eval()
        self.tokenizer = create_tokenizer(self.config.max_seq_len)
        self._loaded = True
        return True

    def is_loaded(self) -> bool:
        return self._loaded

    def predict(
        self,
        request: Dict[str, Any],
        return_details: bool = False,
    ) -> Dict[str, Any]:
        """
        Predict threat classification for a request.
        
        Returns:
            {
                "malicious_probability": float,
                "attack_class": str,
                "attack_probabilities": Dict[str, float],
                "anomaly_score": float,
                "confidence": float,
                "latency_ms": int,
            }
        """
        if not self._loaded:
            self.load()

        start_time = time.perf_counter()

        try:
            # Tokenize
            token_batch, attention_mask = self.tokenizer.tokenize_batch([request])
            token_batch = token_batch.to(self.device)
            attention_mask = attention_mask.to(self.device)

            # Inference
            with torch.no_grad():
                logits, anomaly_score, _ = self.model(
                    token_batch,
                    attention_mask=attention_mask,
                    return_hidden=False,
                )

                # Probabilities
                probs = F.softmax(logits, dim=-1)
                probs_np = probs.cpu().numpy()[0]

                # Get predictions
                malicious_prob = 1.0 - probs_np[0]  # 1 - P(benign)
                pred_class_idx = int(probs_np.argmax())
                pred_class = self.class_names[pred_class_idx]
                confidence = float(probs_np[pred_class_idx])

                attack_probs = {
                    self.class_names[i]: float(probs_np[i])
                    for i in range(len(self.class_names))
                }

                anomaly = float(anomaly_score.cpu().numpy()[0][0])

        except Exception as e:
            logger.error(f"Inference error: {e}")
            # Return safe defaults
            malicious_prob = 0.0
            pred_class = "benign"
            confidence = 1.0
            attack_probs = {name: 0.0 for name in self.class_names}
            attack_probs["benign"] = 1.0
            anomaly = 0.0

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        result = {
            "malicious_probability": round(malicious_prob, 4),
            "attack_class": pred_class,
            "attack_probabilities": {k: round(v, 4) for k, v in attack_probs.items()},
            "anomaly_score": round(anomaly, 4),
            "confidence": round(confidence, 4),
            "latency_ms": latency_ms,
        }

        if return_details:
            result["model_version"] = self.config.version if self.config else "bootstrap"
            result["device"] = str(self.device)

        return result

    def predict_batch(
        self,
        requests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Predict for multiple requests."""
        if not self._loaded:
            self.load()

        start_time = time.perf_counter()

        token_batch, attention_mask = self.tokenizer.tokenize_batch(requests)
        token_batch = token_batch.to(self.device)
        attention_mask = attention_mask.to(self.device)

        with torch.no_grad():
            logits, anomaly_scores, _ = self.model(
                token_batch,
                attention_mask=attention_mask,
                return_hidden=False,
            )

            probs = F.softmax(logits, dim=-1)
            probs_np = probs.cpu().numpy()
            anomaly_np = anomaly_scores.cpu().numpy()

        results = []
        for i in range(len(requests)):
            probs_i = probs_np[i]
            malicious_prob = 1.0 - probs_i[0]
            pred_class_idx = int(probs_i.argmax())
            pred_class = self.class_names[pred_class_idx]
            confidence = float(probs_i[pred_class_idx])
            anomaly = float(anomaly_np[i][0])

            attack_probs = {
                self.class_names[j]: float(probs_i[j])
                for j in range(len(self.class_names))
            }

            results.append({
                "malicious_probability": round(malicious_prob, 4),
                "attack_class": pred_class,
                "attack_probabilities": {k: round(v, 4) for k, v in attack_probs.items()},
                "anomaly_score": round(anomaly, 4),
                "confidence": round(confidence, 4),
            })

        total_latency = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Batch inference: {len(requests)} requests in {total_latency}ms")

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return {
            "loaded": self._loaded,
            "device": str(self.device),
            "config": self.config.to_dict() if self.config else None,
            "class_names": self.class_names,
            "model_path": settings.model_path,
        }


# Singleton instance
_inference_service: Optional[MLInferenceService] = None


def get_inference_service() -> MLInferenceService:
    global _inference_service
    if _inference_service is None:
        _inference_service = MLInferenceService()
    return _inference_service