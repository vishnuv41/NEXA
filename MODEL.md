# NEXA WAF - Model Documentation

## Model Architecture

### HTTP Transformer

A lightweight Transformer encoder designed for HTTP request classification.

```
Input (byte sequence) → Token Embedding → Positional Encoding → Transformer Encoder × 4 → Classification Head
                                                                    ↘ Anomaly Head
```

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Vocab Size | 262 | 256 bytes + 6 structure tokens |
| d_model | 256 | Model dimension |
| n_heads | 4 | Attention heads |
| n_layers | 4 | Encoder layers |
| d_ff | 1024 | Feed-forward dimension |
| max_seq_len | 512 | Maximum sequence length |
| num_classes | 7 | Classification classes |
| dropout | 0.1 | Dropout rate |

### Classes

1. **benign** - Normal legitimate requests
2. **sql_injection** - SQL injection attempts
3. **xss** - Cross-site scripting
4. **path_traversal** - Directory traversal
5. **command_injection** - OS command injection
6. **other_malicious** - Other attack types
7. **anomalous** - Structural anomalies

## Input Representation

### Sequence Format
```
METHOD=GET PATH=/search QUERY=q=test CONTENT_TYPE=application/json BODY={"key":"value"}
```

### Tokenization
- **Byte-level**: Each UTF-8 byte → token (0-255)
- **Structure tokens**: Special tokens for METHOD, PATH, QUERY, HEADER, BODY, CONTENT_TYPE
- **CLS token**: Prepended for classification
- **SEP tokens**: Between fields
- **Padding**: To max_seq_len (512)

### Security-Relevant Symbols Preserved
```
/ ? = & % ' " < > { } [ ] : ; . - _
```

## Training Pipeline

### Data Generation
Synthetic dataset with:
- Benign requests from demo app endpoints
- Attack payloads from 4 families
- Random transformations (encoding, obfuscation)
- Balanced class distribution

### Preprocessing
1. Generate requests with labels
2. Normalize (sort query params, redact secrets)
3. Convert to sequence string
4. Tokenize to byte IDs
5. Pad/truncate to 512 tokens
6. Train/val/test split (80/10/10, stratified)

### Training
```python
# Loss
CrossEntropyLoss()

# Optimizer
AdamW(lr=2e-4, weight_decay=0.01)

# Scheduler
CosineAnnealingLR(T_max=epochs)

# Gradient clipping
max_norm=1.0

# Early stopping
patience=3 on val_loss
```

### Reproducibility
- Fixed random seeds (numpy, torch, python)
- Deterministic CUDA operations (if GPU)
- Versioned data splits

## Evaluation Metrics

### Primary Metrics
- **Accuracy**: Overall correct predictions
- **Precision (weighted)**: TP / (TP + FP) per class, weighted by support
- **Recall (weighted)**: TP / (TP + FN) per class, weighted by support
- **F1 (weighted)**: Harmonic mean of P/R, weighted by support
- **False Positive Rate**: Benign classified as malicious

### Per-Class Metrics
Each attack class gets individual P/R/F1 for visibility into weak spots.

### Confusion Matrix
7×7 matrix showing prediction vs ground truth.

### Performance Benchmarks
- **Latency**: Mean inference time per request (ms)
- **Throughput**: Requests/second at batch size 32
- **Memory**: GPU/CPU memory usage

### Robustness Metrics
- **Known Attack Detection**: Variants seen during training
- **Unseen Variant Detection**: Novel transformations not in training

## Model Artifacts

```
ml/artifacts/
├── model.pt          # PyTorch checkpoint
├── tokenizer/        # Tokenizer config (if saved separately)
└── config.json       # Model configuration
```

Checkpoint contains:
- `model_state_dict`: Weights
- `config`: Full model config
- `optimizer_state_dict`: For resuming
- `epoch`: Training epoch
- `metrics`: Validation metrics at save

## Limitations

### Known Limitations
1. **Synthetic training data** - Not representative of real-world traffic diversity
2. **Limited attack families** - Only 4 primary attack types
3. **Byte-level tokenization** - Less semantic understanding than subword
4. **Small model** - 4 layers, 256 dims; limited capacity
5. **No contextual embeddings** - Each request classified independently
6. **English-centric** - Payloads biased toward English keywords

### Not Suitable For
- Production deployment without retraining on real data
- Zero-day detection claims
- Encrypted payload inspection (TLS termination required)
- High-throughput environments without batching/GPU

## Future Improvements

1. **Real dataset integration** (CSIC 2010, HTTP Dataset, etc.)
2. **Subword tokenization** (BPE/WordPiece for HTTP)
3. **Larger model** (more layers, attention heads)
4. **Contrastive learning** for anomaly detection
5. **Sequence modeling** for session-aware classification
6. **Adversarial training** with PGD/AT
7. **Knowledge distillation** for edge deployment
8. **Online learning** from analyst feedback

## Retraining

```bash
cd backend
python scripts/train_model.py
```

Outputs new model to `ml/artifacts/model.pt` with timestamped backup.

## Inference API

```python
from app.ml.inference import get_inference_service

service = get_inference_service()
result = service.predict({
    "method": "GET",
    "path": "/search",
    "query": "q=test",
    "headers": {},
    "body": "",
})

# Returns:
# {
#   "malicious_probability": 0.95,
#   "attack_class": "sql_injection",
#   "attack_probabilities": {...},
#   "anomaly_score": 0.87,
#   "confidence": 0.92,
#   "latency_ms": 12
# }
```