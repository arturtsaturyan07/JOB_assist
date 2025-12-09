"""
Embedding Service for TwinWork AI

Provides semantic matching using sentence-transformers:
- Skill similarity scoring (Python ≈ Python3 ≈ Py)
- Job-to-profile matching beyond keywords
- Career goal alignment scoring

Uses all-MiniLM-L6-v2 (free, fast, runs locally)
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️ sentence-transformers not installed. Run: pip install sentence-transformers")


@dataclass
class MatchScore:
    """Result of a semantic match"""
    score: float  # 0.0 to 1.0
    explanation: str
    matched_items: List[str]


class EmbeddingService:
    """
    Semantic matching service using sentence embeddings.
    
    Falls back to keyword matching if sentence-transformers not available.
    """
    
    # Pre-computed skill synonyms for fallback matching
    SKILL_SYNONYMS = {
        'python': ['python', 'python3', 'py', 'python programming'],
        'javascript': ['javascript', 'js', 'ecmascript', 'es6', 'es2015'],
        'typescript': ['typescript', 'ts'],
        'react': ['react', 'reactjs', 'react.js', 'react native'],
        'angular': ['angular', 'angularjs', 'angular.js'],
        'vue': ['vue', 'vuejs', 'vue.js', 'vue3'],
        'node': ['node', 'nodejs', 'node.js'],
        'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'mssql', 'sqlite'],
        'nosql': ['nosql', 'mongodb', 'mongo', 'dynamodb', 'cassandra'],
        'docker': ['docker', 'containerization', 'containers'],
        'kubernetes': ['kubernetes', 'k8s', 'container orchestration'],
        'aws': ['aws', 'amazon web services', 'amazon cloud'],
        'azure': ['azure', 'microsoft azure', 'microsoft cloud'],
        'gcp': ['gcp', 'google cloud', 'google cloud platform'],
        'machine learning': ['machine learning', 'ml', 'ai', 'artificial intelligence'],
        'data science': ['data science', 'data analysis', 'analytics'],
        'devops': ['devops', 'dev ops', 'sre', 'site reliability'],
    }
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        if EMBEDDINGS_AVAILABLE:
            try:
                print(f"📦 Loading embedding model: {model_name}...")
                self.model = SentenceTransformer(model_name)
                print("✅ Embedding model loaded")
            except Exception as e:
                print(f"⚠️ Could not load embedding model: {e}")
                self.model = None
        else:
            print("ℹ️ Using fallback keyword matching (install sentence-transformers for semantic matching)")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text, with caching"""
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        if self.model:
            embedding = self.model.encode(text, convert_to_numpy=True)
            self._embedding_cache[text] = embedding
            return embedding
        
        return np.array([])
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        if len(a) == 0 or len(b) == 0:
            return 0.0
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """
        Compute semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score from 0.0 to 1.0
        """
        if self.model:
            emb1 = self._get_embedding(text1.lower())
            emb2 = self._get_embedding(text2.lower())
            similarity = self._cosine_similarity(emb1, emb2)
            # Normalize to 0-1 range (cosine can be negative)
            return max(0.0, min(1.0, (similarity + 1) / 2))
        else:
            # Fallback: Simple word overlap
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            return intersection / union if union > 0 else 0.0
    
    def match_skills(
        self, 
        user_skills: List[str], 
        job_skills: List[str],
        threshold: float = 0.6
    ) -> MatchScore:
        """
        Match user skills against job requirements.
        
        Args:
            user_skills: List of user's skills
            job_skills: List of required job skills
            threshold: Minimum similarity to count as a match
        
        Returns:
            MatchScore with overall score and matched items
        """
        if not job_skills:
            return MatchScore(1.0, "No specific skills required", [])
        
        if not user_skills:
            return MatchScore(0.0, "No user skills provided", [])
        
        matched = []
        total_score = 0.0
        
        user_skills_lower = [s.lower() for s in user_skills]
        job_skills_lower = [s.lower() for s in job_skills]
        
        for job_skill in job_skills_lower:
            best_match_score = 0.0
            best_match_skill = None
            
            for user_skill in user_skills_lower:
                # First check exact match
                if job_skill == user_skill:
                    best_match_score = 1.0
                    best_match_skill = user_skill
                    break
                
                # Check synonyms
                synonym_match = self._check_synonym_match(user_skill, job_skill)
                if synonym_match:
                    best_match_score = 0.95
                    best_match_skill = user_skill
                    break
                
                # Semantic similarity
                if self.model:
                    similarity = self.compute_text_similarity(user_skill, job_skill)
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_skill = user_skill
            
            if best_match_score >= threshold and best_match_skill:
                matched.append(f"{best_match_skill} → {job_skill}")
                total_score += best_match_score
            else:
                # Partial credit for unmatched skills
                total_score += 0.0
        
        # Calculate overall score
        overall_score = total_score / len(job_skills) if job_skills else 0.0
        
        # Generate explanation
        match_rate = len(matched) / len(job_skills) * 100 if job_skills else 100
        if match_rate >= 80:
            explanation = f"Excellent match! {len(matched)}/{len(job_skills)} skills matched"
        elif match_rate >= 60:
            explanation = f"Good match. {len(matched)}/{len(job_skills)} skills matched"
        elif match_rate >= 40:
            explanation = f"Partial match. {len(matched)}/{len(job_skills)} skills matched"
        else:
            explanation = f"Low match. Only {len(matched)}/{len(job_skills)} skills matched"
        
        return MatchScore(
            score=overall_score,
            explanation=explanation,
            matched_items=matched
        )
    
    def _check_synonym_match(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are synonyms"""
        skill1_lower = skill1.lower()
        skill2_lower = skill2.lower()
        
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            synonyms_lower = [s.lower() for s in synonyms]
            if skill1_lower in synonyms_lower and skill2_lower in synonyms_lower:
                return True
            if skill1_lower == canonical and skill2_lower in synonyms_lower:
                return True
            if skill2_lower == canonical and skill1_lower in synonyms_lower:
                return True
        
        return False
    
    def match_job_to_profile(
        self,
        job_title: str,
        job_description: str,
        job_skills: List[str],
        user_career_goals: str,
        user_skills: List[str],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, MatchScore]:
        """
        Comprehensive job-to-profile matching.
        
        Returns scores for different aspects:
        - skills: Technical skill match
        - career: Career goal alignment
        - description: Overall job fit
        """
        results = {}
        
        # Skills matching
        results['skills'] = self.match_skills(user_skills, job_skills)
        
        # Career goal matching
        if user_career_goals and job_title:
            career_similarity = self.compute_text_similarity(
                user_career_goals, 
                job_title
            )
            
            if career_similarity >= 0.7:
                career_explanation = f"Great career fit: '{job_title}' aligns with your goals"
            elif career_similarity >= 0.5:
                career_explanation = f"Good potential: '{job_title}' is related to your goals"
            else:
                career_explanation = f"'{job_title}' might be a stretch from your stated goals"
            
            results['career'] = MatchScore(
                score=career_similarity,
                explanation=career_explanation,
                matched_items=[f"{user_career_goals} ↔ {job_title}"]
            )
        else:
            results['career'] = MatchScore(1.0, "No specific career goals", [])
        
        # Description matching (if semantic model available)
        if self.model and job_description and user_career_goals:
            # Combine user profile into a searchable string
            user_profile_text = f"{user_career_goals} {' '.join(user_skills)}"
            desc_similarity = self.compute_text_similarity(
                user_profile_text[:500],  # Limit length
                job_description[:500]
            )
            
            results['description'] = MatchScore(
                score=desc_similarity,
                explanation=f"Job description relevance: {desc_similarity:.0%}",
                matched_items=[]
            )
        else:
            results['description'] = MatchScore(0.5, "Description analysis unavailable", [])
        
        return results
    
    def rank_jobs(
        self,
        jobs: List[Dict[str, Any]],
        user_profile: Dict[str, Any],
        weights: Dict[str, float] = None
    ) -> List[Tuple[Dict[str, Any], float, Dict[str, MatchScore]]]:
        """
        Rank jobs by relevance to user profile.
        
        Args:
            jobs: List of job dictionaries
            user_profile: User profile dictionary
            weights: Optional weights for different matching aspects
        
        Returns:
            List of (job, overall_score, detailed_scores) tuples, sorted by score
        """
        if weights is None:
            weights = {
                'skills': 0.4,
                'career': 0.35,
                'description': 0.25
            }
        
        ranked = []
        
        for job in jobs:
            scores = self.match_job_to_profile(
                job_title=job.get('title', ''),
                job_description=job.get('description', ''),
                job_skills=job.get('required_skills', []),
                user_career_goals=user_profile.get('career_goals', ''),
                user_skills=user_profile.get('skills', []),
                user_preferences=user_profile.get('preferences', {})
            )
            
            # Calculate weighted overall score
            overall = sum(
                scores[aspect].score * weight 
                for aspect, weight in weights.items() 
                if aspect in scores
            )
            
            ranked.append((job, overall, scores))
        
        # Sort by overall score, descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked
    
    def find_similar_skills(self, skill: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find skills similar to the given skill.
        
        Useful for skill suggestions and gap analysis.
        """
        if not self.model:
            # Fallback: return synonyms if available
            skill_lower = skill.lower()
            for canonical, synonyms in self.SKILL_SYNONYMS.items():
                if skill_lower in [s.lower() for s in synonyms] or skill_lower == canonical:
                    return [(s, 0.9) for s in synonyms[:top_k] if s.lower() != skill_lower]
            return []
        
        # Get all known skills
        all_skills = []
        for category_skills in self.SKILL_SYNONYMS.values():
            all_skills.extend(category_skills)
        all_skills = list(set(all_skills))
        
        # Compute similarities
        skill_embedding = self._get_embedding(skill.lower())
        similarities = []
        
        for s in all_skills:
            if s.lower() != skill.lower():
                s_embedding = self._get_embedding(s.lower())
                sim = self._cosine_similarity(skill_embedding, s_embedding)
                similarities.append((s, sim))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_skill_gap(
        self, 
        user_skills: List[str], 
        job_skills: List[str]
    ) -> List[str]:
        """
        Identify skills the user is missing for a job.
        
        Takes into account semantic similarity, so won't flag
        "Python3" as missing if user has "Python".
        """
        missing = []
        user_skills_lower = [s.lower() for s in user_skills]
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            
            # Check exact match
            if job_skill_lower in user_skills_lower:
                continue
            
            # Check synonym match
            has_synonym = False
            for user_skill in user_skills_lower:
                if self._check_synonym_match(user_skill, job_skill_lower):
                    has_synonym = True
                    break
            
            if has_synonym:
                continue
            
            # Check semantic similarity
            if self.model:
                has_similar = False
                for user_skill in user_skills_lower:
                    similarity = self.compute_text_similarity(user_skill, job_skill_lower)
                    if similarity >= 0.7:
                        has_similar = True
                        break
                
                if has_similar:
                    continue
            
            missing.append(job_skill)
        
        return missing
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self._embedding_cache.clear()


# Singleton instance for reuse
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
