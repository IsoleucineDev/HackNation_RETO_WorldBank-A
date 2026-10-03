"""Clasificador de intencion pequeno (TF-IDF de caracteres + regresion logistica, < 1 MB, corre en un celular)."""
import csv
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline
from .common import ROOT, norm

DATA = ROOT / "data" / "synthetic_sms.csv"
MODEL = ROOT / "models" / "intent.joblib"


def _pipe():
    return Pipeline([
        ("feats", FeatureUnion([
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
        ])),
        ("clf", LogisticRegression(C=30, max_iter=2000)),
    ])


def _load(data=DATA):
    X, y = [], []
    with open(data, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            X.append(norm(r["text"]))
            y.append(r["intent"])
    return X, y


def cross_val(data=DATA, cv=5) -> float:
    X, y = _load(data)
    return float(cross_val_score(_pipe(), X, y, cv=cv).mean())


class IntentClassifier:
    def __init__(self, pipe):
        self.pipe = pipe

    @classmethod
    def train(cls, data=DATA, save=MODEL):
        X, y = _load(data)
        pipe = _pipe().fit(X, y)
        if save:
            save.parent.mkdir(exist_ok=True)
            joblib.dump(pipe, save, compress=3)
        return cls(pipe)

    @classmethod
    def load(cls):
        return cls(joblib.load(MODEL)) if MODEL.exists() else cls.train()

    def predict(self, text: str):
        """-> (intencion, confianza, P(malestar))"""
        proba = self.pipe.predict_proba([norm(text)])[0]
        classes = list(self.pipe.classes_)
        i = int(proba.argmax())
        return str(classes[i]), float(proba[i]), float(proba[classes.index("malestar")])
