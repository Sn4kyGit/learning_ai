"""
Claude Haiku implementation for business advisory services.

This module implements the BusinessAdvisorProtocol using Anthropic's Claude 3 Haiku
for contextual business advice and weekly report generation.
"""

import json
import logging
import time
import asyncio
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import anthropic
from anthropic import AsyncAnthropic

from backend.ai.base import (
    BusinessAdvisorProtocol,
    BusinessContext,
    AdvisorResponse,
    WeeklyReport,
    CostTracker,
)

logger = logging.getLogger(__name__)


class ClaudeHaikuAdvisor:
    """Claude Haiku implementation for business advisory services."""

    # Token cost per 1K tokens (approximate pricing for Claude 3 Haiku)
    INPUT_TOKEN_COST = Decimal("0.00025")  # $0.25 per 1M input tokens
    OUTPUT_TOKEN_COST = Decimal("0.00125")  # $1.25 per 1M output tokens

    def __init__(
        self,
        api_key: str,
        cost_tracker: CostTracker,
        model_name: str = "claude-3-haiku-20240307",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        request_timeout: int = 30,
        max_tokens: int = 1000,
    ):
        """Initialize Claude Haiku advisor.

        Args:
            api_key: Anthropic API key
            cost_tracker: Cost tracking service
            model_name: Model name for API calls
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            request_timeout: Request timeout in seconds
            max_tokens: Maximum tokens for responses
        """
        self._api_key = api_key
        self._cost_tracker = cost_tracker
        self._model_name = model_name
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._request_timeout = request_timeout
        self._max_tokens = max_tokens

        # Initialize Anthropic client
        self._client = AsyncAnthropic(
            api_key=api_key,
            timeout=request_timeout
        )

    async def generate_response(
        self, 
        message: str, 
        context: BusinessContext, 
        language: str = "en",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AdvisorResponse:
        """Generate contextual business advice based on review data.

        Args:
            message: User's question or request
            context: Business context with review data and metrics
            language: Response language (en, de, tr, ar)
            conversation_history: Previous conversation messages

        Returns:
            AdvisorResponse with business advice

        Raises:
            Exception: If response generation fails after all retries
        """
        start_time = time.time()

        try:
            # Create the advisory prompt
            system_prompt = self._create_advisory_system_prompt(context, language)
            messages = self._build_conversation_messages(message, conversation_history)

            # Make API call with retry logic
            response = await self._make_api_call_with_retry(system_prompt, messages)

            # Extract response content
            response_content = response.content[0].text

            # Calculate processing time and cost
            processing_time = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(response.usage)

            # Log usage for cost tracking
            if self._cost_tracker:
                await self._cost_tracker.log_usage(
                    business_id=context.business_id,
                    ai_service="claude_haiku",
                    operation="chat",
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                    cost_usd=cost,
                    processing_time_ms=processing_time
                )

            return AdvisorResponse(
                message=response_content,
                language=language,
                confidence_score=Decimal("0.9"),  # Claude generally provides high-quality responses
                processing_time_ms=processing_time,
                ai_model=self._model_name,
                cost_usd=cost,
            )

        except Exception as e:
            logger.error(f"Business advisory response generation failed: {e}")
            raise

    async def generate_report(
        self, 
        business_data: BusinessContext, 
        language: str = "en",
        report_period_days: int = 7
    ) -> WeeklyReport:
        """Generate comprehensive weekly business report.

        Args:
            business_data: Business context with analytics data
            language: Report language (en, de, tr, ar)
            report_period_days: Number of days to cover in report

        Returns:
            WeeklyReport with analysis and action items

        Raises:
            Exception: If report generation fails after all retries
        """
        start_time = time.time()

        try:
            # Create the report generation prompt
            system_prompt = self._create_report_system_prompt(language)
            user_prompt = self._create_report_user_prompt(business_data, report_period_days)

            messages = [{"role": "user", "content": user_prompt}]

            # Make API call with retry logic
            response = await self._make_api_call_with_retry(system_prompt, messages)

            # Parse the structured report response
            report_data = self._parse_report_response(response.content[0].text)

            # Calculate processing time and cost
            processing_time = int((time.time() - start_time) * 1000)
            cost = self._calculate_cost(response.usage)

            # Log usage for cost tracking
            if self._cost_tracker:
                await self._cost_tracker.log_usage(
                    business_id=business_data.business_id,
                    ai_service="claude_haiku",
                    operation="report",
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                    cost_usd=cost,
                    processing_time_ms=processing_time
                )

            # Calculate report period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=report_period_days)

            return WeeklyReport(
                business_id=business_data.business_id,
                report_period_start=start_date,
                report_period_end=end_date,
                summary=report_data["summary"],
                action_items=report_data["action_items"],
                sentiment_analysis=report_data["sentiment_analysis"],
                top_themes=report_data["top_themes"],
                competitor_mentions=business_data.competitor_mentions,
                language=language,
                ai_model=self._model_name,
            )

        except Exception as e:
            logger.error(f"Weekly report generation failed: {e}")
            raise

    def _create_advisory_system_prompt(self, context: BusinessContext, language: str) -> str:
        """Create system prompt for business advisory responses.

        Args:
            context: Business context with review data
            language: Response language

        Returns:
            System prompt for Claude
        """
        language_instructions = {
            "en": "Respond in English",
            "de": "Respond in German (Deutsch)",
            "tr": "Respond in Turkish (Türkçe)",
            "ar": "Respond in Arabic (العربية)"
        }

        language_instruction = language_instructions.get(language, "Respond in English")

        return f"""You are an expert business advisor specializing in restaurant management and customer experience. You help restaurant owners understand their customer feedback and improve their business performance.

Business Context:
- Restaurant: {context.business_name}
- Average Rating: {context.avg_rating}/5.0
- Total Reviews: {context.total_reviews}
- Recent Sentiment Trend: {context.recent_sentiment_trend}
- Top Discussion Topics: {', '.join(context.top_topics)}
- Competitor Mentions: {context.competitor_mentions}

Guidelines:
1. {language_instruction}
2. Provide specific, actionable advice based on the business data
3. Reference the actual metrics and trends when making recommendations
4. Be supportive and constructive in your tone
5. Focus on practical solutions that small restaurant owners can implement
6. If asked about competitors, provide strategic insights without being negative
7. Keep responses concise but comprehensive (aim for 150-300 words)
8. Always ground your advice in the actual review data and metrics provided

Your role is to help this restaurant owner make data-driven decisions to improve their customer experience and business performance."""

    def _build_conversation_messages(
        self, 
        current_message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Build conversation messages including history.

        Args:
            current_message: Current user message
            conversation_history: Previous conversation messages

        Returns:
            List of messages for API call
        """
        messages = []

        # Add conversation history if provided
        if conversation_history:
            # Limit history to last 10 messages to stay within token limits
            recent_history = conversation_history[-10:]
            messages.extend(recent_history)

        # Add current message
        messages.append({"role": "user", "content": current_message})

        return messages

    def _create_report_system_prompt(self, language: str) -> str:
        """Create system prompt for weekly report generation.

        Args:
            language: Report language

        Returns:
            System prompt for report generation
        """
        language_instructions = {
            "en": "Generate the report in English",
            "de": "Generate the report in German (Deutsch)",
            "tr": "Generate the report in Turkish (Türkçe)",
            "ar": "Generate the report in Arabic (العربية)"
        }

        language_instruction = language_instructions.get(language, "Generate the report in English")

        return f"""You are an expert business analyst specializing in restaurant performance reports. Generate a comprehensive weekly business report based on customer review data and business metrics.

{language_instruction}

The report should be structured as a JSON object with the following format:
{{
    "summary": "Brief overview of the week's performance (2-3 sentences)",
    "action_items": ["Specific action item 1", "Specific action item 2", "Specific action item 3"],
    "sentiment_analysis": "Analysis of customer sentiment trends and changes",
    "top_themes": ["Theme 1", "Theme 2", "Theme 3"]
}}

Guidelines:
1. Provide 3-5 specific, actionable recommendations
2. Focus on trends and changes rather than just current state
3. Be constructive and solution-oriented
4. Reference specific metrics when possible
5. Keep action items practical for small restaurant owners
6. Highlight both positive achievements and areas for improvement

Return only valid JSON, no additional text."""

    def _create_report_user_prompt(self, business_data: BusinessContext, report_period_days: int) -> str:
        """Create user prompt for report generation with business data.

        Args:
            business_data: Business context and metrics
            report_period_days: Number of days covered in report

        Returns:
            User prompt with business data
        """
        return f"""Generate a weekly business report for the following restaurant:

Restaurant: {business_data.business_name}
Report Period: Last {report_period_days} days

Current Metrics:
- Average Rating: {business_data.avg_rating}/5.0
- Total Reviews: {business_data.total_reviews}
- Recent Sentiment Trend: {business_data.recent_sentiment_trend}
- Top Discussion Topics: {', '.join(business_data.top_topics) if business_data.top_topics else 'No specific topics identified'}
- Competitor Mentions: {business_data.competitor_mentions}

Please analyze this data and provide insights, trends, and actionable recommendations for the restaurant owner."""

    async def _make_api_call_with_retry(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, str]]
    ) -> Any:
        """Make Anthropic API call with exponential backoff retry logic.

        Args:
            system_prompt: System prompt for the conversation
            messages: List of conversation messages

        Returns:
            Anthropic API response

        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(self._max_retries):
            try:
                response = await self._client.messages.create(
                    model=self._model_name,
                    max_tokens=self._max_tokens,
                    temperature=0.1,
                    system=system_prompt,
                    messages=messages
                )
                return response

            except anthropic.RateLimitError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue

            except anthropic.APITimeoutError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(f"API timeout, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue

            except anthropic.APIConnectionError as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.warning(f"API connection error, retrying in {delay}s (attempt {attempt + 1}/{self._max_retries})")
                    await asyncio.sleep(delay)
                    continue

            except Exception as e:
                # For other exceptions, don't retry
                logger.error(f"Anthropic API call failed: {e}")
                raise

        # If we get here, all retries failed
        logger.error(f"Anthropic API call failed after {self._max_retries} attempts")
        raise last_exception

    def _parse_report_response(self, response_content: str) -> Dict[str, Any]:
        """Parse weekly report response from Claude.

        Args:
            response_content: Raw response content from Claude

        Returns:
            Parsed report data

        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Try to extract JSON from the response
            # Claude might include additional text, so we need to find the JSON part
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_content = response_content[start_idx:end_idx]
            data = json.loads(json_content)

            # Validate required fields and set defaults
            report_data = {
                "summary": data.get("summary", "Weekly performance summary not available."),
                "action_items": data.get("action_items", ["Review customer feedback", "Monitor service quality", "Analyze competitor activity"]),
                "sentiment_analysis": data.get("sentiment_analysis", "Sentiment analysis not available for this period."),
                "top_themes": data.get("top_themes", ["General feedback"])
            }

            # Ensure action_items is a list
            if not isinstance(report_data["action_items"], list):
                report_data["action_items"] = ["Review customer feedback", "Monitor service quality"]

            # Ensure top_themes is a list
            if not isinstance(report_data["top_themes"], list):
                report_data["top_themes"] = ["General feedback"]

            return report_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse report response: {e}")
            # Return default report structure
            return {
                "summary": "Unable to generate detailed summary. Please review your recent customer feedback manually.",
                "action_items": [
                    "Review recent customer reviews for common themes",
                    "Monitor service quality during peak hours",
                    "Analyze competitor activity in your area"
                ],
                "sentiment_analysis": "Sentiment analysis unavailable. Please check individual reviews for customer satisfaction trends.",
                "top_themes": ["Service quality", "Food quality", "Customer experience"]
            }

    def _calculate_cost(self, usage: Any) -> Decimal:
        """Calculate cost based on token usage.

        Args:
            usage: Anthropic usage object

        Returns:
            Cost in USD
        """
        input_cost = (Decimal(str(usage.input_tokens)) / 1000) * self.INPUT_TOKEN_COST
        output_cost = (Decimal(str(usage.output_tokens)) / 1000) * self.OUTPUT_TOKEN_COST
        return input_cost + output_cost