import os
import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

from app.ml.model import HTTPTransformer, HTTPTransformerConfig, create_model, save_model
from app.ml.tokenizer import HTTPRequestTokenizer, create_tokenizer
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Attack payloads for synthetic data generation
ATTACK_PAYLOADS = {
    "sql_injection": [
        "' OR '1'='1", "' OR 1=1--", "' UNION SELECT NULL,NULL,NULL--",
        "'; DROP TABLE users--", "admin'--", "' OR '1'='1' LIMIT 1--",
        "1' ORDER BY 1--", "' UNION SELECT username,password FROM users--",
    ],
    "xss": [
        "<script>alert('XSS')</script>", "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>", "javascript:alert('XSS')",
        "<body onload=alert('XSS')>", "<iframe src=javascript:alert('XSS')>",
    ],
    "path_traversal": [
        "../../../etc/passwd", "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "....//....//....//etc/passwd", "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ],
    "command_injection": [
        "; cat /etc/passwd", "| cat /etc/passwd", "`cat /etc/passwd`",
        "$(cat /etc/passwd)", "&& cat /etc/passwd", "; id",
    ],
}

BENIGN_PAYLOADS = [
    {"method": "GET", "path": "/", "query": "", "headers": {}, "body": ""},
    {"method": "GET", "path": "/products", "query": "", "headers": {}, "body": ""},
    {"method": "GET", "path": "/products/1", "query": "", "headers": {}, "body": ""},
    {"method": "GET", "path": "/search", "query": "q=laptop", "headers": {}, "body": ""},
    {"method": "GET", "path": "/search", "query": "q=headphones", "headers": {}, "body": ""},
    {"method": "GET", "path": "/dashboard", "query": "", "headers": {"authorization": "Bearer token"}, "body": ""},
    {"method": "POST", "path": "/login", "query": "", "headers": {"content-type": "application/json"}, "body": '{"username":"user","password":"pass"}'},
    {"method": "POST", "path": "/cart", "query": "", "headers": {"content-type": "application/json"}, "body": '{"product_id":1,"quantity":2}'},
    {"method": "POST", "path": "/checkout", "query": "", "headers": {"authorization": "Bearer token"}, "body": ""},
    {"method": "GET", "path": "/users/1", "query": "", "headers": {"authorization": "Bearer token"}, "body": ""},
]

CLASS_MAP = {
    "benign": 0,
    "sql_injection": 1,
    "xss": 2,
    "path_traversal": 3,
    "command_injection": 4,
    "other_malicious": 5,
    "anomalous": 6,
}


def generate_synthetic_data(num_samples=10000, seed=42):
    """Generate synthetic training data."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    
    requests = []
    labels = []
    
    # Generate benign requests
    for _ in range(num_samples // 2):
        base = np.random.choice(BENIGN_PAYLOADS)
        # Add some variation
        req = base.copy()
        if req["query"] and np.random.random() < 0.3:
            req["query"] += f"&page={np.random.randint(1, 10)}"
        requests.append(req)
        labels.append(CLASS_MAP["benign"])
    
    # Generate attack requests
    attack_types = list(ATTACK_PAYLOADS.keys())
    for attack_type in attack_types:
        payloads = ATTACK_PAYLOADS[attack_type]
        for _ in range(num_samples // (2 * len(attack_types))):
            payload = np.random.choice(payloads)
            # Apply random transformations
            if np.random.random() < 0.5:
                payload = payload.upper()
            if np.random.random() < 0.3:
                import urllib.parse
                payload = urllib.parse.quote(payload)
            
            req = {
                "method": np.random.choice(["GET", "POST"]),
                "path": np.random.choice(["/search", "/products/1", "/login", "/api/data"]),
                "query": f"q={payload}" if np.random.random() < 0.7 else f"id={payload}",
                "headers": {},
                "body": payload if np.random.random() < 0.3 else "",
            }
            requests.append(req)
            labels.append(CLASS_MAP[attack_type])
    
    return requests, labels


def prepare_data(requests, labels, tokenizer, max_len=512):
    """Tokenize and prepare data for training."""
    tokenized = []
    for req in requests:
        tokens = tokenizer.encode(tokenizer._request_to_sequence(req))
        tokenized.append(tokens)
    
    X = torch.tensor(tokenized, dtype=torch.long)
    y = torch.tensor(labels, dtype=torch.long)
    return X, y


def train_model(
    epochs=10,
    batch_size=32,
    learning_rate=2e-4,
    num_samples=10000,
    seed=42,
    output_dir="./ml/artifacts",
):
    """Train the HTTP Transformer model."""
    logger.info("Starting model training...")
    
    # Generate data
    requests, labels = generate_synthetic_data(num_samples, seed)
    logger.info(f"Generated {len(requests)} samples")
    logger.info(f"Class distribution: {pd.Series(labels).value_counts().to_dict()}")
    
    # Create tokenizer
    tokenizer = create_tokenizer(max_length=512)
    
    # Prepare data
    X, y = prepare_data(requests, labels, tokenizer)
    
    # Split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )
    
    # Create datasets
    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Create model
    config = HTTPTransformerConfig(
        vocab_size=262,
        d_model=256,
        n_heads=4,
        n_layers=4,
        d_ff=1024,
        max_seq_len=512,
        num_classes=7,
        dropout=0.1,
    )
    
    device = torch.device(settings.model_device)
    model = create_model(config).to(device)
    
    # Optimizer and loss
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Training loop
    best_val_acc = 0
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            
            attention_mask = (batch_X != 0).long()
            
            optimizer.zero_grad()
            logits, _, _ = model(batch_X, attention_mask=attention_mask)
            loss = criterion(logits, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = logits.max(1)
            train_correct += predicted.eq(batch_y).sum().item()
            train_total += batch_y.size(0)
        
        # Validate
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X = batch_X.to(device)
                batch_y = batch_y.to(device)
                attention_mask = (batch_X != 0).long()
                
                logits, _, _ = model(batch_X, attention_mask=attention_mask)
                loss = criterion(logits, batch_y)
                
                val_loss += loss.item()
                _, predicted = logits.max(1)
                val_correct += predicted.eq(batch_y).sum().item()
                val_total += batch_y.size(0)
                
                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(batch_y.cpu().numpy())
        
        train_acc = train_correct / train_total
        val_acc = val_correct / val_total
        
        logger.info(
            f"Epoch {epoch+1}/{epochs} | "
            f"Train Loss: {train_loss/len(train_loader):.4f} Acc: {train_acc:.4f} | "
            f"Val Loss: {val_loss/len(val_loader):.4f} Acc: {val_acc:.4f}"
        )
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            # Save best model
            os.makedirs(output_dir, exist_ok=True)
            save_model(
                model, config,
                os.path.join(output_dir, "model.pt"),
                optimizer_state=optimizer.state_dict(),
                epoch=epoch,
                metrics={"val_acc": val_acc, "train_acc": train_acc},
            )
            logger.info(f"Saved best model (val_acc={val_acc:.4f})")
        
        scheduler.step()
    
    logger.info(f"Training complete. Best validation accuracy: {best_val_acc:.4f}")
    
    # Final evaluation
    evaluate_model(model, val_loader, device, CLASS_MAP)
    
    return model, config


def evaluate_model(model, val_loader, device, class_map):
    """Evaluate model on validation set."""
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            attention_mask = (batch_X != 0).long()
            
            logits, _, _ = model(batch_X, attention_mask=attention_mask)
            _, predicted = logits.max(1)
            
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(batch_y.cpu().numpy())
    
    # Classification report
    class_names = list(class_map.keys())
    report = classification_report(all_labels, all_preds, target_names=class_names, output_dict=True)
    
    logger.info("\nClassification Report:")
    for cls in class_names:
        if cls in report:
            logger.info(f"  {cls}: P={report[cls]['precision']:.3f} R={report[cls]['recall']:.3f} F1={report[cls]['f1-score']:.3f}")
    
    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    logger.info(f"\nConfusion Matrix:\n{cm}")
    
    return report, cm


if __name__ == "__main__":
    train_model()