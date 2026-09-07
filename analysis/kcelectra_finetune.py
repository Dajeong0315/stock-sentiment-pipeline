"""Fine-tune KcELECTRA-base on a small manually-labeled slice of the collected news, then
compare its accuracy against the zero-shot local LLM and the rule-based sentiment scorer
on the *same* held-out labels — the only fair way to compare all three.

ponytail: plain PyTorch training loop instead of HF `Trainer` (which now wants `accelerate`
installed) — a few dozen examples for a few epochs doesn't need that machinery.

Honesty note: with ~46 labeled examples total (~9 in the held-out test split), accuracy
numbers here are illustrative of the *method*, not a statistically meaningful benchmark.
See PORTFOLIO_NOTES.md for the full caveat, including who did the labeling.
"""
import json
import logging

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import config
from db.db import get_conn

log = logging.getLogger(__name__)

MODEL_NAME = "beomi/KcELECTRA-base"
LABELS_PATH = config.BASE_DIR / "analysis" / "manual_labels.json"
LABEL_TO_IDX = {-1: 0, 0: 1, 1: 2}  # negative, neutral, positive
IDX_TO_LABEL = {v: k for k, v in LABEL_TO_IDX.items()}
EPOCHS = 4
BATCH_SIZE = 4
TEST_FRACTION = 0.2
SEED = 42


class NewsDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def _load_labeled_examples():
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))["labels"]
    ids = [int(i) for i in labels]
    placeholders = ",".join("?" * len(ids))
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT id, title, content, rule_sentiment_score, llm_sentiment_score "
            f"FROM news WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
    by_id = {r["id"]: r for r in rows}

    texts, y, rule_scores, llm_scores = [], [], [], []
    for id_str, label in labels.items():
        row = by_id.get(int(id_str))
        if row is None:
            continue
        texts.append(f"{row['title']} {row['content'] or ''}".strip())
        y.append(LABEL_TO_IDX[label])
        rule_scores.append(row["rule_sentiment_score"])
        llm_scores.append(row["llm_sentiment_score"])
    return texts, y, rule_scores, llm_scores


def _bucket(score, neutral_band):
    if score is None:
        return LABEL_TO_IDX[0]
    if score > neutral_band:
        return LABEL_TO_IDX[1]
    if score < -neutral_band:
        return LABEL_TO_IDX[-1]
    return LABEL_TO_IDX[0]


def run_comparison() -> dict:
    texts, y, rule_scores, llm_scores = _load_labeled_examples()
    idx = np.arange(len(texts))
    train_idx, test_idx = train_test_split(idx, test_size=TEST_FRACTION, random_state=SEED, stratify=y)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=3)

    train_texts = [texts[i] for i in train_idx]
    train_labels = [y[i] for i in train_idx]
    train_enc = tokenizer(train_texts, truncation=True, padding=True, max_length=128, return_tensors="pt")
    train_ds = NewsDataset(train_enc, train_labels)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

    optimizer = AdamW(model.parameters(), lr=2e-5)
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            outputs = model(**batch)
            outputs.loss.backward()
            optimizer.step()
            total_loss += outputs.loss.item()
        log.info("epoch %d/%d — loss=%.4f", epoch + 1, EPOCHS, total_loss / len(train_loader))

    model.eval()
    test_texts = [texts[i] for i in test_idx]
    test_labels = [y[i] for i in test_idx]
    test_enc = tokenizer(test_texts, truncation=True, padding=True, max_length=128, return_tensors="pt")
    with torch.no_grad():
        logits = model(**test_enc).logits
    kcelectra_preds = logits.argmax(dim=1).tolist()

    rule_preds = [_bucket(rule_scores[i], neutral_band=0.005) for i in test_idx]
    llm_preds = [_bucket(llm_scores[i], neutral_band=0.1) for i in test_idx]

    def accuracy(preds, subset=None):
        pairs = zip(preds, test_labels) if subset is None else (
            (p, t) for p, t, keep in zip(preds, test_labels, subset) if keep
        )
        pairs = list(pairs)
        return float(np.mean([p == t for p, t in pairs])) if pairs else None

    non_neutral = [t != LABEL_TO_IDX[0] for t in test_labels]

    result = {
        "n_train": len(train_idx),
        "n_test": len(test_idx),
        "n_test_non_neutral": sum(non_neutral),
        "kcelectra_accuracy": accuracy(kcelectra_preds),
        "llm_zero_shot_accuracy": accuracy(llm_preds),
        "rule_based_accuracy": accuracy(rule_preds),
        "kcelectra_accuracy_non_neutral": accuracy(kcelectra_preds, non_neutral),
        "llm_accuracy_non_neutral": accuracy(llm_preds, non_neutral),
        "rule_based_accuracy_non_neutral": accuracy(rule_preds, non_neutral),
        "examples": [
            {
                "text": texts[i][:60],
                "true": IDX_TO_LABEL[test_labels[k]],
                "rule": IDX_TO_LABEL[rule_preds[k]],
                "llm": IDX_TO_LABEL[llm_preds[k]],
                "kcelectra": IDX_TO_LABEL[kcelectra_preds[k]],
            }
            for k, i in enumerate(test_idx)
        ],
    }
    log.info("Comparison result: %s", {k: v for k, v in result.items() if k != "examples"})
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_comparison())
