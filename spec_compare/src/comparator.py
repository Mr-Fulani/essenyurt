"""
Comparison algorithms for specification matching
Алгоритмы сравнения спецификаций
"""

import numpy as np
from typing import List, Dict, Tuple, Set
from rapidfuzz import fuzz, process
from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpecificationComparator:
    """
    Comparator for specification files using weighted similarity algorithm
    """
    
    # Weight coefficients for similarity components
    WEIGHTS = {
        'names': 0.35,        # Наименования товаров
        'manufacturers': 0.25, # Производители/бренды
        'weight': 0.20,       # Вес нетто
        'items': 0.15,        # Количество позиций
        'articles': 0.05,     # Артикулы
    }
    
    def __init__(self):
        self.tfidf = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words=None
        )
    
    def compare(self, new_products: List[Dict], 
                archive_products: List[Dict]) -> Dict:
        """
        Compare two sets of products and return similarity scores
        
        Returns:
            Dictionary with similarity scores for each component and total
        """
        results = {}
        
        # 1. Name similarity (35%)
        results['names'] = self._compare_names(new_products, archive_products)
        
        # 2. Manufacturer/Brand similarity (25%)
        results['manufacturers'] = self._compare_manufacturers(new_products, archive_products)
        
        # 3. Weight similarity (20%)
        results['weight'] = self._compare_weight(new_products, archive_products)
        
        # 4. Items similarity (15%) - Jaccard
        results['items'] = self._compare_items(new_products, archive_products)
        
        # 5. Article similarity (5%)
        results['articles'] = self._compare_articles(new_products, archive_products)
        
        # Calculate weighted total
        total = sum(
            results[key] * self.WEIGHTS[key] 
            for key in self.WEIGHTS.keys()
        )
        results['total'] = round(total * 100, 2)  # As percentage
        
        # Round component scores
        for key in results:
            if key != 'total':
                results[key] = round(results[key] * 100, 2)
        
        return results
    
    def _compare_names(self, new_products: List[Dict], 
                       archive_products: List[Dict]) -> float:
        """
        Compare product names using fuzzy matching + TF-IDF
        Returns similarity score 0-1
        """
        new_names = [self._normalize_name(p.get('name', '')) for p in new_products]
        archive_names = [self._normalize_name(p.get('name', '')) for p in archive_products]
        
        # Filter empty names
        new_names = [n for n in new_names if n]
        archive_names = [n for n in archive_names if n]
        
        if not new_names or not archive_names:
            return 0.0
        
        # Method 1: Pairwise fuzzy matching with best matches
        match_scores = []
        for new_name in new_names:
            best_score = 0
            for archive_name in archive_names:
                score = fuzz.token_set_ratio(new_name, archive_name) / 100.0
                if score > best_score:
                    best_score = score
            match_scores.append(best_score)
        
        avg_match = np.mean(match_scores) if match_scores else 0
        
        # Method 2: TF-IDF cosine similarity
        try:
            all_names = new_names + archive_names
            if len(set(all_names)) > 1:  # Need variation for TF-IDF
                tfidf_matrix = self.tfidf.fit_transform(all_names)
                new_vectors = tfidf_matrix[:len(new_names)]
                archive_vectors = tfidf_matrix[len(new_names):]
                
                # Calculate cosine similarities
                similarities = cosine_similarity(new_vectors, archive_vectors)
                
                # Get best match for each new product
                best_tfidf_scores = similarities.max(axis=1)
                avg_tfidf = np.mean(best_tfidf_scores)
            else:
                avg_tfidf = avg_match  # Fall back to fuzzy
        except Exception as e:
            avg_tfidf = avg_match  # Fall back to fuzzy
        
        # Combine scores (weighted average)
        combined = 0.6 * avg_match + 0.4 * avg_tfidf
        return min(1.0, combined)
    
    def _compare_manufacturers(self, new_products: List[Dict], 
                               archive_products: List[Dict]) -> float:
        """
        Compare manufacturers and brands
        Returns similarity score 0-1
        """
        # Extract manufacturers and brands
        new_mfrs = set()
        archive_mfrs = set()
        
        for p in new_products:
            mfr = self._normalize_name(p.get('manufacturer', ''))
            brand = self._normalize_name(p.get('brand', ''))
            if mfr:
                new_mfrs.add(mfr)
            if brand:
                new_mfrs.add(brand)
        
        for p in archive_products:
            mfr = self._normalize_name(p.get('manufacturer', ''))
            brand = self._normalize_name(p.get('brand', ''))
            if mfr:
                archive_mfrs.add(mfr)
            if brand:
                archive_mfrs.add(brand)
        
        if not new_mfrs or not archive_mfrs:
            return 0.0
        
        # Exact matches
        exact_matches = new_mfrs & archive_mfrs
        
        # Fuzzy matches for non-exact
        fuzzy_matches = 0
        for new_mfr in new_mfrs - exact_matches:
            for arch_mfr in archive_mfrs - exact_matches:
                if fuzz.ratio(new_mfr, arch_mfr) >= 85:
                    fuzzy_matches += 1
                    break
        
        total_matches = len(exact_matches) + fuzzy_matches
        total_unique = len(new_mfrs | archive_mfrs)
        
        if total_unique == 0:
            return 0.0
        
        return total_matches / total_unique
    
    def _compare_weight(self, new_products: List[Dict], 
                        archive_products: List[Dict]) -> float:
        """
        Compare total weights
        Returns similarity score 0-1
        """
        new_weight = sum(p.get('weight_net', 0) or 0 for p in new_products)
        archive_weight = sum(p.get('weight_net', 0) or 0 for p in archive_products)
        
        if new_weight == 0 and archive_weight == 0:
            return 1.0  # Both empty = perfect match
        
        if new_weight == 0 or archive_weight == 0:
            return 0.0  # One empty, one not = no match
        
        # Calculate deviation
        diff = abs(new_weight - archive_weight)
        avg_weight = (new_weight + archive_weight) / 2
        deviation = diff / avg_weight
        
        # Scoring based on deviation
        # ±10% = 100%, ±20% = 50%, >30% = 0%
        if deviation <= 0.10:
            return 1.0
        elif deviation <= 0.20:
            return 0.5 + (0.20 - deviation) * 5  # Linear from 0.5 to 1.0
        elif deviation <= 0.30:
            return (0.30 - deviation) * 5  # Linear from 0 to 0.5
        else:
            return 0.0
    
    def _compare_items(self, new_products: List[Dict], 
                       archive_products: List[Dict]) -> float:
        """
        Compare items using Jaccard similarity
        Returns similarity score 0-1
        """
        # Create item signatures (name + manufacturer)
        new_items = set()
        archive_items = set()
        
        for p in new_products:
            name = self._normalize_name(p.get('name', ''))
            mfr = self._normalize_name(p.get('manufacturer', ''))
            if name:
                signature = f"{name}|{mfr}"
                new_items.add(signature)
        
        for p in archive_products:
            name = self._normalize_name(p.get('name', ''))
            mfr = self._normalize_name(p.get('manufacturer', ''))
            if name:
                signature = f"{name}|{mfr}"
                archive_items.add(signature)
        
        if not new_items or not archive_items:
            return 0.0
        
        # Jaccard similarity
        intersection = len(new_items & archive_items)
        union = len(new_items | archive_items)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _compare_articles(self, new_products: List[Dict], 
                          archive_products: List[Dict]) -> float:
        """
        Compare articles (exact matching)
        Returns similarity score 0-1
        """
        new_articles = set(p.get('article', '') for p in new_products if p.get('article'))
        archive_articles = set(p.get('article', '') for p in archive_products if p.get('article'))
        
        if not new_articles or not archive_articles:
            return 0.0  # No articles to compare
        
        # Exact match ratio
        matches = len(new_articles & archive_articles)
        total = len(new_articles | archive_articles)
        
        if total == 0:
            return 0.0
        
        return matches / total
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        if not name:
            return ''
        
        # Uppercase
        name = name.upper()
        
        # Remove special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Normalize whitespace
        name = ' '.join(name.split())
        
        # Remove common stop words
        stop_words = {'THE', 'AND', 'OR', 'WITH', 'FOR', 'OF', 'IN', 'ON', 'AT', 'TO', 
                      'A', 'AN', 'IS', 'IT', 'BY', 'FROM', 'AS'}
        words = [w for w in name.split() if w not in stop_words]
        
        return ' '.join(words)
    
    def find_matches(self, new_products: List[Dict], 
                     candidate_files: List[Dict],
                     top_n: int = 10) -> List[Dict]:
        """
        Find best matching files from candidates
        
        Args:
            new_products: Products from new file
            candidate_files: List of file dicts with 'products' key
            top_n: Number of top matches to return
            
        Returns:
            List of match results sorted by similarity
        """
        results = []
        
        for candidate in candidate_files:
            archive_products = candidate.get('products', [])
            
            if not archive_products:
                continue
            
            # Calculate similarity
            similarity = self.compare(new_products, archive_products)
            
            # Find intersection and unique items
            intersection, unique_new, unique_archive = self._find_differences(
                new_products, archive_products
            )
            
            result = {
                'file_id': candidate.get('id'),
                'filename': candidate.get('filename'),
                'upload_date': candidate.get('upload_date'),
                'similarity': similarity,
                'total_weight': candidate.get('total_weight', 0),
                'total_items': candidate.get('total_items', 0),
                'intersection': intersection,
                'unique_new': unique_new,
                'unique_archive': unique_archive,
            }
            
            results.append(result)
        
        # Sort by total similarity (descending)
        results.sort(key=lambda x: x['similarity']['total'], reverse=True)
        
        return results[:top_n]
    
    def _find_differences(self, new_products: List[Dict], 
                          archive_products: List[Dict]) -> Tuple[List, List, List]:
        """
        Find intersection and differences between product sets
        
        Returns:
            (intersection, unique_new, unique_archive)
        """
        # Create signatures for matching
        def make_sig(p):
            name = self._normalize_name(p.get('name', ''))
            mfr = self._normalize_name(p.get('manufacturer', ''))
            return (name, mfr)
        
        new_sigs = {make_sig(p): p for p in new_products}
        archive_sigs = {make_sig(p): p for p in archive_products}
        
        new_keys = set(new_sigs.keys())
        archive_keys = set(archive_sigs.keys())
        
        intersection = []
        for key in new_keys & archive_keys:
            intersection.append({
                'new_product': new_sigs[key],
                'archive_product': archive_sigs[key]
            })
        
        unique_new = [new_sigs[k] for k in new_keys - archive_keys]
        unique_archive = [archive_sigs[k] for k in archive_keys - new_keys]
        
        return intersection, unique_new, unique_archive


def quick_compare(products1: List[Dict], products2: List[Dict]) -> float:
    """Quick comparison returning only total similarity percentage"""
    comp = SpecificationComparator()
    result = comp.compare(products1, products2)
    return result['total']
