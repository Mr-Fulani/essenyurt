"""
Comparison algorithms for specification matching
Алгоритмы сравнения спецификаций - Универсальная версия
"""

import numpy as np
from typing import List, Dict, Tuple, Set
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpecificationComparator:
    """
    Comparator for specification files using generic similarity algorithm
    """
    
    WEIGHTS = {
        'content': 0.85,    # Сходство содержимого строк (85%)
        'columns': 0.15,    # Сходство структуры столбцов (15%)
    }
    
    def __init__(self):
        self.tfidf = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 3),
            min_df=1,
            lowercase=True
        )
    
    def compare(self, new_products: List[Dict], archive_products: List[Dict]) -> Dict:
        """Compare two generic sets of products and return similarity scores"""
        if new_products == archive_products:
            return {'content': 100.0, 'columns': 100.0, 'total': 100.0}

        results = {}
        results['columns'] = self._compare_columns(new_products, archive_products)
        results['content'] = self._compare_content(new_products, archive_products)
        
        total = sum(results[k] * self.WEIGHTS[k] for k in self.WEIGHTS.keys())
        
        results['total'] = round(total * 100, 2)
        results['columns'] = round(results['columns'] * 100, 2)
        results['content'] = round(results['content'] * 100, 2)
        
        return results
    
    def _get_row_signature(self, row: Dict) -> str:
        """Convert a generic row dictionary to a normalized searchable string"""
        parts = []
        for k, v in sorted(row.items()):
            if k == 'row_number' or not str(v).strip() or str(v) == 'nan':
                continue
            parts.append(str(v).strip().lower())
        return ' '.join(parts)

    def _compare_content(self, new_products: List[Dict], archive_products: List[Dict]) -> float:
        """Compare content using TF-IDF and cosine similarity of row signatures"""
        new_sigs = [self._get_row_signature(p) for p in new_products]
        archive_sigs = [self._get_row_signature(p) for p in archive_products]
        
        new_sigs = [s for s in new_sigs if s]
        archive_sigs = [s for s in archive_sigs if s]
        
        if not new_sigs and not archive_sigs: return 1.0
        if not new_sigs or not archive_sigs: return 0.0
        
        all_sigs = new_sigs + archive_sigs
        
        if len(set(all_sigs)) <= 1:
            return 1.0 # All identical content
            
        try:
            tfidf_matrix = self.tfidf.fit_transform(all_sigs)
            new_vectors = tfidf_matrix[:len(new_sigs)]
            archive_vectors = tfidf_matrix[len(new_sigs):]
            
            similarities = cosine_similarity(new_vectors, archive_vectors)
            
            # For each new row, find best matching archive row
            best_matches_for_new = similarities.max(axis=1)
            score1 = np.mean(best_matches_for_new)
            
            # For each archive row, find best matching new row
            best_matches_for_archive = similarities.max(axis=0)
            score2 = np.mean(best_matches_for_archive)
            
            # Average the bidirectional similarity
            return float((score1 + score2) / 2)
            
        except Exception as e:
            logger.error(f"Error in TF-IDF content comparison: {e}")
            # Fallback to Jaccard similarity of words
            return self._fallback_content_compare(new_sigs, archive_sigs)
            
    def _fallback_content_compare(self, new_sigs: List[str], archive_sigs: List[str]) -> float:
        """Simple word-overlap fallback"""
        new_words = set(' '.join(new_sigs).split())
        archive_words = set(' '.join(archive_sigs).split())
        
        if not new_words and not archive_words: return 1.0
        if not new_words or not archive_words: return 0.0
        
        intersection = new_words.intersection(archive_words)
        union = new_words.union(archive_words)
        return len(intersection) / len(union)

    def _compare_columns(self, new_products: List[Dict], archive_products: List[Dict]) -> float:
        """Calculate Jaccard similarity of column names"""
        new_cols = set()
        for p in new_products:
            new_cols.update([k for k in p.keys() if k != 'row_number'])
            
        archive_cols = set()
        for p in archive_products:
            archive_cols.update([k for k in p.keys() if k != 'row_number'])
            
        if not new_cols and not archive_cols: return 1.0
        if not new_cols or not archive_cols: return 0.0
        
        intersection = new_cols.intersection(archive_cols)
        union = new_cols.union(archive_cols)
        return len(intersection) / len(union)
