"""
Base HTTP client for external API integrations.

This module provides a base HTTP client with common functionality
for external API calls including retry logic and error handling.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import aiohttp
from aiohttp import ClientTimeout, ClientError

logger = logging.getLogger(__name__)


class BaseHTTPClient(ABC):
    """Base HTTP client for external API integrations."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize base HTTP client.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = ClientTimeout(total=timeout)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            headers = self._get_default_headers()
            self._session = aiohttp.ClientSession(
                headers=headers, timeout=self._timeout
            )

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests.

        Returns:
            Dictionary of default headers
        """
        pass

    async def _make_request(  # noqa: C901
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data as dictionary

        Raises:
            ClientError: If request fails after all retries
        """
        await self._ensure_session()

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        request_headers = headers or {}

        for attempt in range(self._max_retries + 1):
            try:
                async with self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                ) as response:

                    # Log request details
                    logger.debug(f"{method} {url} - Status: {response.status}")

                    # Handle different response types
                    if response.content_type == "application/json":
                        response_data = await response.json()
                    else:
                        response_text = await response.text()
                        response_data = {"text": response_text}

                    # Check for successful response
                    if 200 <= response.status < 300:
                        return response_data

                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(
                            response.headers.get("Retry-After", self._retry_delay)
                        )
                        if attempt < self._max_retries:
                            logger.warning(
                                f"Rate limited, retrying after {retry_after}s"
                            )
                            await asyncio.sleep(retry_after)
                            continue

                    # Handle server errors with retry
                    if response.status >= 500 and attempt < self._max_retries:
                        delay = self._retry_delay * (2**attempt)  # Exponential backoff
                        logger.warning(
                            f"Server error {response.status}, retrying in {delay}s"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Raise exception for client errors or final attempt
                    response.raise_for_status()

            except ClientError as e:
                if attempt < self._max_retries:
                    delay = self._retry_delay * (2**attempt)
                    logger.warning(f"Request failed: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Request failed after {self._max_retries} retries: {e}"
                    )
                    raise

            except Exception as e:
                logger.error(f"Unexpected error in request: {e}")
                raise

        # This should never be reached, but just in case
        raise ClientError("Request failed after all retries")

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data
        """
        return await self._make_request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data
        """
        return await self._make_request(
            "POST", endpoint, data=data, params=params, headers=headers
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data
        """
        return await self._make_request(
            "PUT", endpoint, data=data, params=params, headers=headers
        )

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers

        Returns:
            Response data
        """
        return await self._make_request(
            "DELETE", endpoint, params=params, headers=headers
        )
