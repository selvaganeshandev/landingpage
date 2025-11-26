"""
Content Comparator Service
Uses LLM (OpenAI) to compare LLM claims against source content
and detect misinformation, outdated info, and factual errors.
"""
import json
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

from django.conf import settings

logger = logging.getLogger(__name__)


class AlertType(Enum):
    MISINFORMATION = "misinformation"
    OUTDATED = "outdated"
    BROKEN_LINK = "broken_link"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComparisonResult:
    """Result of comparing LLM claim against source content."""
    has_issue: bool
    alert_type: Optional[str]
    severity: Optional[str]
    llm_claim: str
    source_content: str
    explanation: str


class ContentComparator:
    """
    Compares LLM response claims against source content to detect:
    - Misinformation (factually incorrect claims)
    - Outdated information (old data, discontinued products, etc.)
    """

    COMPARISON_PROMPT = """You are a fact-checking assistant. Your task is to compare an LLM's claim about a SPECIFIC brand against the actual source content and identify any misinformation or outdated information ONLY about that brand.

## IMPORTANT: Brand Focus
You are checking claims about this SPECIFIC brand:
- Brand Name: {brand_name}
- Brand URL: {brand_url}

ONLY flag issues that are DIRECTLY about this brand ({brand_name}).
DO NOT flag issues about:
- Other companies/brands/competitors mentioned in the content
- General industry information that doesn't specifically relate to {brand_name}
- Information about other products not belonging to {brand_name}

## LLM Claim (what the AI said about {brand_name})
{llm_claim}

## Source Content (from the cited URL: {source_url})
{source_content}

## Your Task
Compare the LLM claim against the source content and determine if there are any issues SPECIFICALLY about {brand_name}:

1. **Misinformation**: The LLM stated something about {brand_name} that contradicts the source content or is factually incorrect
2. **Outdated Information**: The LLM used old data about {brand_name} that has since been updated (old prices, discontinued products, changed features, etc.)

Respond in JSON format:
{{
    "has_issue": true/false,
    "alert_type": "misinformation" or "outdated" or null,
    "severity": "low" or "medium" or "high" or "critical",
    "specific_claim": "The exact claim about {brand_name} that is problematic",
    "correct_information": "What the source actually says about {brand_name}",
    "explanation": "Brief explanation of the discrepancy regarding {brand_name}"
}}

## Severity Guidelines (ONLY for issues about {brand_name}):
- **critical**: Completely false claims about {brand_name} (wrong products, false legal issues, fabricated partnerships)
- **high**: Significant factual errors about {brand_name} (wrong pricing, incorrect features, false contact info)
- **medium**: Outdated information about {brand_name} (old versions, discontinued products, expired promotions)
- **low**: Minor inaccuracies about {brand_name}, slight misstatements

If there are no issues ABOUT {brand_name}, respond with:
{{
    "has_issue": false,
    "alert_type": null,
    "severity": null,
    "specific_claim": null,
    "correct_information": null,
    "explanation": "The claim about {brand_name} appears to be accurate based on the source content"
}}

Be thorough but fair. Only flag genuine issues ABOUT {brand_name}, not minor wording differences or issues about other companies."""

    def __init__(self, model: str = None):
        """
        Initialize the comparator.

        Args:
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.model = model or getattr(
            settings, 'MISINFO_COMPARISON_MODEL', 'gpt-4o-mini'
        )
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            self._client = self._get_openai_client()
        return self._client

    def _get_openai_client(self):
        """Get OpenAI client."""
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            raise Exception("OpenAI API key not configured")
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key, timeout=60)
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {e}")

    def compare(
        self,
        llm_claim: str,
        source_content: str,
        source_url: str,
        brand_name: str,
        brand_url: str
    ) -> ComparisonResult:
        """
        Compare an LLM claim against source content.

        Args:
            llm_claim: The claim made by the LLM
            source_content: Content from the cited source
            source_url: URL of the source
            brand_name: Name of the brand being monitored
            brand_url: URL of the brand

        Returns:
            ComparisonResult with analysis
        """
        try:
            # Truncate content if too long
            max_source_length = 3000
            if len(source_content) > max_source_length:
                source_content = source_content[:max_source_length] + "..."

            max_claim_length = 1500
            if len(llm_claim) > max_claim_length:
                llm_claim = llm_claim[:max_claim_length] + "..."

            prompt = self.COMPARISON_PROMPT.format(
                brand_name=brand_name,
                brand_url=brand_url,
                llm_claim=llm_claim,
                source_content=source_content,
                source_url=source_url
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact-checking assistant. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            return ComparisonResult(
                has_issue=result.get('has_issue', False),
                alert_type=result.get('alert_type'),
                severity=result.get('severity'),
                llm_claim=result.get('specific_claim', llm_claim),
                source_content=result.get('correct_information', ''),
                explanation=result.get('explanation', '')
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return ComparisonResult(
                has_issue=False,
                alert_type=None,
                severity=None,
                llm_claim=llm_claim,
                source_content='',
                explanation=f"Error parsing comparison result: {e}"
            )

        except Exception as e:
            logger.error(f"Error comparing content: {e}")
            return ComparisonResult(
                has_issue=False,
                alert_type=None,
                severity=None,
                llm_claim=llm_claim,
                source_content='',
                explanation=f"Error during comparison: {e}"
            )

    def batch_compare(
        self,
        claims_with_sources: List[Dict],
        brand_name: str,
        brand_url: str
    ) -> List[ComparisonResult]:
        """
        Compare multiple claims against their sources.

        Args:
            claims_with_sources: List of dicts with 'llm_claim', 'source_content', 'source_url'
            brand_name: Name of the brand
            brand_url: URL of the brand

        Returns:
            List of ComparisonResults
        """
        results = []
        for item in claims_with_sources:
            result = self.compare(
                llm_claim=item['llm_claim'],
                source_content=item['source_content'],
                source_url=item['source_url'],
                brand_name=brand_name,
                brand_url=brand_url
            )
            results.append(result)
        return results

    def extract_brand_claims(self, response_text: str, brand_name: str) -> List[str]:
        """
        Extract claims about a specific brand from LLM response text.

        Args:
            response_text: Full LLM response
            brand_name: Brand name to look for

        Returns:
            List of sentences/claims mentioning the brand
        """
        import re

        if not response_text or not brand_name:
            return []

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', response_text)

        # Find sentences mentioning the brand
        claims = []
        brand_lower = brand_name.lower()

        for sentence in sentences:
            if brand_lower in sentence.lower():
                sentence = sentence.strip()
                if len(sentence) > 20:  # Skip very short sentences
                    claims.append(sentence)

        return claims
