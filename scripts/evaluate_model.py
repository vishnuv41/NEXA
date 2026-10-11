import os
import json
import torch
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support
import logging
from datetime import datetime

from app.ml.model import HTTPTransformer, HTTPTransformerConfig, load_model
from app.ml.tokenizer import create_tokenizer
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

CLASS_MAP = {
    "benign": 0,
    "sql_injection": 1,
    "xss": 2,
    "path_traversal": 3,
    "command_injection": 4,
    "other_malicious": 5,
    "anomalous": 6,
}

CLASS_NAMES = list(CLASS_MAP.keys())


def load_test_data():
    """Load or generate test data."""
    from scripts.train_model import generate_synthetic_data, prepare_data
    
    requests, labels = generate_synthetic_data(2000, seed=123)
    tokenizer = create_tokenizer(max_length=512)
    X, y = prepare_data(requests, labels, tokenizer)
    
    return X, y, tokenizer


def evaluate_model(model_path=None):
    """Evaluate model on test data."""
    device = torch.device(settings.model_device)
    
    # Load model
    if model_path:
        model, config = load_model(model_path, device)
    else:
        model, config = load_model(settings.model_path, device)
    
    logger.info(f"Model loaded: {config.num_classes} classes, {config.n_layers} layers")
    
    # Load test data
    X, y, tokenizer = load_test_data()
    
    # Run inference
    model.eval()
    batch_size = 64
    all_preds = []
    all_probs = []
    all_anomaly = []
    latencies = []
    
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            batch_X = X[i:i+batch_size].to(device)
            attention_mask = (batch_X != 0).long()
            
            import time
            start = time.perf_counter()
            logits, anomaly, _ = model(batch_X, attention_mask=attention_mask)
            latencies.append((time.perf_counter() - start) * 1000 / len(batch_X))
            
            probs = torch.softmax(logits, dim=-1)
            _, preds = logits.max(1)
            
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_anomaly.extend(anomaly.cpu().numpy())
    
    # Metrics
    accuracy = accuracy_score(y.numpy(), all_preds)
    precision, recall, f1, _ = precision_recall_fscore_support(y.numpy(), all_preds, average='weighted')
    _, _, _, support = precision_recall_fscore_support(y.numpy(), all_preds, average=None)
    
    per_class_precision, per_class_recall, per_class_f1, _ = precision_recall_fscore_support(
        y.numpy(), all_preds, average=None, labels=range(len(CLASS_NAMES))
    )
    
    cm = confusion_matrix(y.numpy(), all_preds, labels=range(len(CLASS_NAMES)))
    
    # False positive rate (benign classified as malicious)
    benign_idx = CLASS_MAP["benign"]
    tn = cm[benign_idx, benign_idx]
    fp = cm[benign_idx, :].sum() - tn
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    
    avg_latency = np.mean(latencies)
    throughput = 1000 / avg_latency if avg_latency > 0 else 0
    
    # Known vs unseen (simulate by checking if attack types in training)
    # For now, just report overall
    known_attack_rate = 0.0
    unseen_attack_rate = 0.0
    
    results = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_positive_rate": float(fpr),
        "per_class": {
            CLASS_NAMES[i]: {
                "precision": float(per_class_precision[i]) if i < len(per_class_precision) else 0,
                "recall": float(per_class_recall[i]) if i < len(per_class_recall) else 0,
                "f1": float(per_class_f1[i]) if i < len(per_class_f1) else 0,
                "support": int(support[i]) if i < len(support) else 0,
            }
            for i in range(len(CLASS_NAMES))
        },
        "confusion_matrix": cm.tolist(),
        "latency_ms": float(avg_latency),
        "throughput": float(throughput),
        "known_attack_detection_rate": float(known_attack_rate),
        "unseen_variant_detection_rate": float(unseen_attack_rate),
        "avg_anomaly_score": float(np.mean(all_anomaly)),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall: {recall:.4f}")
    logger.info(f"F1: {f1:.4f}")
    logger.info(f"FPR: {fpr:.4f}")
    logger.info(f"Avg Latency: {avg_latency:.2f}ms")
    logger.info(f"Throughput: {throughput:.0f} req/s")
    
    # Save results
    os.makedirs("./ml/evaluation", exist_ok=True)
    with open("./ml/evaluation/results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results


if __name__ == "__main__":
    evaluate_model()