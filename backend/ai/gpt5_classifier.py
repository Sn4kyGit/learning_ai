"""
GPT-5 Nano implementation for review classification.

This module implements the ReviewClassifierProtocol using OpenAI's GPT-4o-mini
for fast and cost-effective review sentiment analysis and topic extraction.
"""

import json
import logging
import time
import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional

import openai
from openai import AsyncOpenAI

from backend.ai.base import (
    ClassificationResult,
    ReviewText,
    CostTracker,
)

logger = logging.getLogger(__name__)


class GPT5NanoClassifier:
    """GPT-5 Nano implementation for review classification using OpenAI GPT-4o-mini."""

    # Token cost per 1K tokens (approximate pricing for GPT-4o-mini)
    INPUT_TOKEN_COST = Decimal("0.00015")  # $0.15 per 1M input tokens
    OUTPUT_TOKEN_COST = Decimal("0.0006")  # $0.60 per 1M output tokens

    def __init__(
        self, 
        api_key: str, 
        cost_tracker: CostTracker, 
        model_name: str = "gpt-4o-mini",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        request_timeout: int = 30
    ):
        """Initialize GPT-5 Nano classifier.

        Args:
            api_key: OpenAI API key
            cost_tracker: Cost tracking service
            model_name: Model name for API calls
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            request_timeout: Request timeout in seconds
        """
        self._api_key = api_key
        self._cost_tracker = cost_tracker
        self._model_name = model_name
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._request_timeout = request_timeout
        
        # Initialize OpenAI client
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=request_timeout
        )

    async def classify_review(
        self, text: str, language: str = "en", business_id: Optional[str] = None
    ) -> ClassificationResult:
        """Classify a single review for sentiment, topics, and urgency.

        Args:
            text: Review text to classify
            language: Language of the review
            business_id: Business ID for cost tracking

        Returns:
            ClassificationResult with sentiment, topics, and urgency

        Raises:
            Exception: If classification fails after all retries
        """
        start_time = time.time()
        
        try:
            # Create the classification prompt
            prompt = self._create_classification_prompt(text, language)
            
            # Make API call with retry logic
            response = await self._make_api_call_with_retry(prompt)
            
            # Parse the response
            classification_data = self._parse_classification_response(response)
            
            # Calculate processing time and cost
            processing_time = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(response.usage)
            
            # Log usage for cost tracking
            if business_id and self._cost_tracker:
                await self._cost_tracker.log_usage(
                    business_id=business_id,
                    ai_service="gpt4o_mini",
                    operation="classify_single",
                    tokens_used=response.usage.total_tokens,
                    cost_usd=cost,
                    processing_time_ms=processing_time
                )
            
            return ClassificationResult(
                sentiment=classification_data["sentiment"],
                topics=classification_data["topics"],
                urgency=classification_data["urgency"],
                competitor_mentioned=classification_data["competitor_mentioned"],
                confidence_score=classification_data["confidence_score"],
                processing_time_ms=processing_time,
                ai_model=self._model_name,
            )
            
        except Exception as e:
            logger.error(f"Review classification failed: {e}")
            raise

    async def classify_batch(
        self, reviews: List[ReviewText]
    ) -> List[ClassificationResult]:
        """Classify multiple reviews in a single API call for cost efficiency.

        Args:
            reviews: List of reviews to classify (max 500)

        Returns:
            List of ClassificationResult objects

        Raises:
            ValueError: If batch size exceeds 500 reviews
            Exception: If batch classification fails after all retries
        """
        if len(reviews) > 500:
            raise ValueError("Batch size cannot exceed 500 reviews")
        
        if not reviews:
            return []
        
        start_time = time.time()
        
        try:
            # Create batch classification prompt
            prompt = self._create_batch_classification_prompt(reviews)
            
            # Make API call with retry logic
            response = await self._make_api_call_with_retry(prompt)
            
            # Parse batch response
            classifications_data = self._parse_batch_classification_response(response, len(reviews))
            
            # Calculate processing time and cost
            processing_time = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(response.usage)
            
            # Create results
            results = []
            for i, review in enumerate(reviews):
                classification_data = classifications_data[i] if i < len(classifications_data) else {
                    "sentiment": "neutral",
                    "topics": [],
                    "urgency": "low",
                    "competitor_mentioned": False,
                    "confidence_score": 0.5
                }
                
                result = ClassificationResult(
                    sentiment=classification_data["sentiment"],
                    topics=classification_data["topics"],
                    urgency=classification_data["urgency"],
                    competitor_mentioned=classification_data["competitor_mentioned"],
                    confidence_score=classification_data["confidence_score"],
                    processing_time_ms=processing_time // len(reviews),  # Distribute time across reviews
                    ai_model=self._model_name,
                )
                results.append(result)
                
                # Log usage for each review's business
                if self._cost_tracker:
                    review_cost = cost / len(reviews)  # Distribute cost across reviews
                    await self._cost_tracker.log_usage(
                        business_id=review.business_id,
                        ai_service="gpt4o_mini",
                        operation="classify_batch",
                        tokens_used=response.usage.total_tokens // len(reviews),
                        cost_usd=review_cost,
                        processing_time_ms=processing_time // len(reviews)
                    )
            
            return results
            
        except Exception as e:
            logger.error(f"Batch review classification failed: {e}")
            raise

    def _create_classification_prompt(self, text: str, language: str) -> List[Dict[str, str]]:
        """Create classification prompt for a single review.

        Args:
            text: Review text to classify
            language: Language of the review

        Returns:
            List of messages for OpenAI API
        """
        system_prompt = """You are an expert review classifier for restaurants. Analyze the given review and return a JSON response with the following structure:

{
    "sentiment": "positive|negative|neutral",
    "topics": ["food_quality", "service", "ambiance", "price", "cleanliness"],
    "urgency": "low|medium|high",
    "competitor_mentioned": true|false,
    "confidence_score": 0.0-1.0
}

Guidelines:
- sentiment: positive (4-5 stars implied), negative (1-2 stars implied), neutral (3 stars implied)
- topics: select relevant topics from the list, can be multiple
- urgency: high for serious complaints requiring immediate attention, medium for moderate issues, low for general feedback
- competitor_mentioned: true if other restaurants/businesses are mentioned
- confidence_score: your confidence in the classification (0.0-1.0)

Return only valid JSON, no additional text."""

        user_prompt = f"Review text (language: {language}): {text}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _create_batch_classification_prompt(self, reviews: List[ReviewText]) -> List[Dict[str, str]]:
        """Create batch classification prompt for multiple reviews.

        Args:
            reviews: List of reviews to classify

        Returns:
            List of messages for OpenAI API
        """
        system_prompt = """You are an expert review classifier for restaurants. Analyze the given reviews and return a JSON array with classification results. Each result should have this structure:

{
    "sentiment": "positive|negative|neutral",
    "topics": ["food_quality", "service", "ambiance", "price", "cleanliness"],
    "urgency": "low|medium|high",
    "competitor_mentioned": true|false,
    "confidence_score": 0.0-1.0
}

Guidelines:
- sentiment: positive (4-5 stars implied), negative (1-2 stars implied), neutral (3 stars implied)
- topics: select relevant topics from the list, can be multiple
- urgency: high for serious complaints requiring immediate attention, medium for moderate issues, low for general feedback
- competitor_mentioned: true if other restaurants/businesses are mentioned
- confidence_score: your confidence in the classification (0.0-1.0)

Return a JSON array with one classification object per review, in the same order. Return only valid JSON, no additional text."""

        # Create user prompt with numbered reviews
        review_texts = []
        for i, review in enumerate(reviews, 1):
            review_texts.append(f"{i}. (language: {review.language}) {review.text}")
        
        user_prompt = "Reviews to classify:\n" + "\n".join(review_texts)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def _make_api_call_with_retry(self, messages: List[Dict[str, str]]) -> Any:
        """Make OpenAI API call with exponential backoff retry logic.

        Args:
            messages: Messages for the API call

        Returns:
            OpenAI API response

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                return response
                
            except openai.RateLimitError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue
                    
            except openai.APITimeoutError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(f"API timeout, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue
                    
            except openai.APIConnectionError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(f"API connection error, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue
                    
            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"OpenAI API call failed: {e}")
                raise
        
        # If we get here, all retries failed
        logger.error(f"OpenAI API call failed after {self._max_retries} attempts")
        raise last_exception

    def _parse_classification_response(self, response: Any) -> Dict[str, Any]:
        """Parse single review classification response.

        Args:
            response: OpenAI API response

        Returns:
            Parsed classification data

        Raises:
            ValueError: If response format is invalid
        """
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Set defaults for missing fields instead of raising errors
            data.setdefault("sentiment", "neutral")
            data.setdefault("topics", [])
            data.setdefault("urgency", "low")
            data.setdefault("competitor_mentioned", False)
            data.setdefault("confidence_score", 0.5)
            
            # Validate sentiment values
            if data["sentiment"] not in ["positive", "negative", "neutral"]:
                data["sentiment"] = "neutral"
            
            # Validate urgency values
            if data["urgency"] not in ["low", "medium", "high"]:
                data["urgency"] = "low"
            
            # Ensure topics is a list
            if not isinstance(data["topics"], list):
                data["topics"] = []
            
            # Validate confidence score
            if not isinstance(data["confidence_score"], (int, float)) or not (0 <= data["confidence_score"] <= 1):
                data["confidence_score"] = 0.5
            
            return data
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse classification response: {e}")
            # Return default classification
            return {
                "sentiment": "neutral",
                "topics": [],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.5
            }

    def _parse_batch_classification_response(self, response: Any, expected_count: int) -> List[Dict[str, Any]]:
        """Parse batch review classification response.

        Args:
            response: OpenAI API response
            expected_count: Expected number of classifications

        Returns:
            List of parsed classification data

        Raises:
            ValueError: If response format is invalid
        """
        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            
            if not isinstance(data, list):
                raise ValueError("Expected JSON array for batch response")
            
            results = []
            for i, item in enumerate(data):
                if i >= expected_count:
                    break
                    
                # Validate and clean each classification
                classification = self._validate_classification_data(item)
                results.append(classification)
            
            # Fill missing classifications with defaults
            while len(results) < expected_count:
                results.append({
                    "sentiment": "neutral",
                    "topics": [],
                    "urgency": "low",
                    "competitor_mentioned": False,
                    "confidence_score": 0.5
                })
            
            return results
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse batch classification response: {e}")
            # Return default classifications for all reviews
            return [{
                "sentiment": "neutral",
                "topics": [],
                "urgency": "low",
                "competitor_mentioned": False,
                "confidence_score": 0.5
            }] * expected_count

    def _validate_classification_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean classification data.

        Args:
            data: Raw classification data

        Returns:
            Validated classification data
        """
        # Set defaults for missing fields
        validated = {
            "sentiment": data.get("sentiment", "neutral"),
            "topics": data.get("topics", []),
            "urgency": data.get("urgency", "low"),
            "competitor_mentioned": data.get("competitor_mentioned", False),
            "confidence_score": data.get("confidence_score", 0.5)
        }
        
        # Validate sentiment
        if validated["sentiment"] not in ["positive", "negative", "neutral"]:
            validated["sentiment"] = "neutral"
        
        # Validate urgency
        if validated["urgency"] not in ["low", "medium", "high"]:
            validated["urgency"] = "low"
        
        # Ensure topics is a list
        if not isinstance(validated["topics"], list):
            validated["topics"] = []
        
        # Validate confidence score
        if not isinstance(validated["confidence_score"], (int, float)) or not (0 <= validated["confidence_score"] <= 1):
            validated["confidence_score"] = 0.5
        
        return validated

    def _calculate_cost(self, usage: Any) -> Decimal:
        """Calculate cost based on token usage.

        Args:
            usage: OpenAI usage object

        Returns:
            Cost in USD
        """
        input_cost = (Decimal(str(usage.prompt_tokens)) / 1000) * self.INPUT_TOKEN_COST
        output_cost = (Decimal(str(usage.completion_tokens)) / 1000) * self.OUTPUT_TOKEN_COST
        return input_cost + output_cost
