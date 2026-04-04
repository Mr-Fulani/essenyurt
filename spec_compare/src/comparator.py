"""
Comparison algorithms for specification matching
Алгоритмы сравнения спецификаций - Универсальная версия
"""

import numpy as np
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _word_ngrams(words: List[str], n_min: int, n_max: int) -> List[str]:
    """Word-level n-grams (same idea as sklearn TfidfVectorizer ngram_range)."""
    out: List[str] = []
    L = len(words)
    if L == 0:
        return out
    for n in range(n_min, n_max + 1):
        if n > L:
            break
        for i in range(L - n + 1):
            out.append(" ".join(words[i : i + n]))
    return out


def _tfidf_l2_matrix(doc_tokens: List[List[str]]) -> np.ndarray:
    """
    TF-IDF with sklearn-style smooth idf, then L2-normalize rows (for cosine via dot).
    Returns shape (n_docs, n_terms); empty last dim if no vocabulary.
    """
    n_docs = len(doc_tokens)
    if n_docs == 0:
        return np.zeros((0, 0))

    vocab: Dict[str, int] = {}
    for tokens in doc_tokens:
        for t in tokens:
            if t not in vocab:
                vocab[t] = len(vocab)

    n_terms = len(vocab)
    if n_terms == 0:
        return np.zeros((n_docs, 0))

    tf = np.zeros((n_docs, n_terms), dtype=np.float64)
    for i, tokens in enumerate(doc_tokens):
        for t in tokens:
            tf[i, vocab[t]] += 1.0

    df = np.sum(tf > 0, axis=0)
    idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
    tfidf = tf * idf

    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return tfidf / norms


def _cosine_similarity_xy(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pairwise cosine similarity; rows of x and y must be L2-normalized."""
    return x @ y.T


class SpecificationComparator:
    """
    Comparator for specification files using generic similarity algorithm
    """

    WEIGHTS = {
        "content": 0.85,  # Сходство содержимого строк (85%)
        "columns": 0.15,  # Сходство структуры столбцов (15%)
    }

    NGRAM_MIN = 1
    NGRAM_MAX = 3

    def _signature_tokens(self, sig: str) -> List[str]:
        words = [w for w in sig.split() if w]
        return _word_ngrams(words, self.NGRAM_MIN, self.NGRAM_MAX)

    def compare(self, new_products: List[Dict], archive_products: List[Dict]) -> Dict:
        """Compare two generic sets of products and return similarity scores"""
        if new_products == archive_products:
            return {"content": 100.0, "columns": 100.0, "total": 100.0}

        results = {}
        results["columns"] = self._compare_columns(new_products, archive_products)
        results["content"] = self._compare_content(new_products, archive_products)

        total = sum(results[k] * self.WEIGHTS[k] for k in self.WEIGHTS.keys())

        results["total"] = round(total * 100, 2)
        results["columns"] = round(results["columns"] * 100, 2)
        results["content"] = round(results["content"] * 100, 2)

        return results

    def _get_row_signature(self, row: Dict) -> str:
        """Convert a generic row dictionary to a normalized searchable string"""
        parts = []
        for k, v in sorted(row.items()):
            if k == "row_number" or not str(v).strip() or str(v) == "nan":
                continue
            parts.append(str(v).strip().lower())
        return " ".join(parts)

    def _compare_content(self, new_products: List[Dict], archive_products: List[Dict]) -> float:
        """Compare content using TF-IDF and cosine similarity of row signatures"""
        new_sigs = [self._get_row_signature(p) for p in new_products]
        archive_sigs = [self._get_row_signature(p) for p in archive_products]

        new_sigs = [s for s in new_sigs if s]
        archive_sigs = [s for s in archive_sigs if s]

        if not new_sigs and not archive_sigs:
            return 1.0
        if not new_sigs or not archive_sigs:
            return 0.0

        all_sigs = new_sigs + archive_sigs

        if len(set(all_sigs)) <= 1:
            return 1.0  # All identical content

        try:
            doc_tokens = [self._signature_tokens(s) for s in all_sigs]
            matrix = _tfidf_l2_matrix(doc_tokens)
            if matrix.shape[1] == 0:
                return self._fallback_content_compare(new_sigs, archive_sigs)

            n_new = len(new_sigs)
            new_vectors = matrix[:n_new]
            archive_vectors = matrix[n_new:]

            similarities = _cosine_similarity_xy(new_vectors, archive_vectors)

            best_matches_for_new = similarities.max(axis=1)
            score1 = float(np.mean(best_matches_for_new))

            best_matches_for_archive = similarities.max(axis=0)
            score2 = float(np.mean(best_matches_for_archive))

            return (score1 + score2) / 2.0

        except Exception as e:
            logger.error(f"Error in TF-IDF content comparison: {e}")
            return self._fallback_content_compare(new_sigs, archive_sigs)

    def _fallback_content_compare(self, new_sigs: List[str], archive_sigs: List[str]) -> float:
        """Simple word-overlap fallback"""
        new_words = set(" ".join(new_sigs).split())
        archive_words = set(" ".join(archive_sigs).split())

        if not new_words and not archive_words:
            return 1.0
        if not new_words or not archive_words:
            return 0.0

        intersection = new_words.intersection(archive_words)
        union = new_words.union(archive_words)
        return len(intersection) / len(union)

    def _compare_columns(self, new_products: List[Dict], archive_products: List[Dict]) -> float:
        """Calculate Jaccard similarity of column names"""
        new_cols = set()
        for p in new_products:
            new_cols.update([k for k in p.keys() if k != "row_number"])

        archive_cols = set()
        for p in archive_products:
            archive_cols.update([k for k in p.keys() if k != "row_number"])

        if not new_cols and not archive_cols:
            return 1.0
        if not new_cols or not archive_cols:
            return 0.0

        intersection = new_cols.intersection(archive_cols)
        union = new_cols.union(archive_cols)
        return len(intersection) / len(union)
