"""Async HTTP client utilities for high-performance API data ingestion."""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIResponse:
    """Container for API response data."""
    url: str
    status: int
    data: Any
    headers: Dict[str, str]
    response_time: float
    success: bool
    error: Optional[str] = None

class AsyncCongressClient:
    """Async HTTP client optimized for Congress.gov API calls."""

    def __init__(self, api_key: str, max_concurrent: int = 10, rate_limit_delay: float = 0.1):
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_times: List[float] = []

    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'OpenDiscourse/1.0',
                'Accept': 'application/json'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Make a single API request with rate limiting."""
        async with self.semaphore:
            start_time = time.time()

            # Add API key to params
            if params is None:
                params = {}
            params['api_key'] = self.api_key

            try:
                async with self.session.get(url, params=params) as response:
                    response_time = time.time() - start_time
                    self.request_times.append(response_time)

                    if response.status == 200:
                        try:
                            data = await response.json()
                            return APIResponse(
                                url=str(response.url),
                                status=response.status,
                                data=data,
                                headers=dict(response.headers),
                                response_time=response_time,
                                success=True
                            )
                        except json.JSONDecodeError as e:
                            return APIResponse(
                                url=str(response.url),
                                status=response.status,
                                data=None,
                                headers=dict(response.headers),
                                response_time=response_time,
                                success=False,
                                error=f"JSON decode error: {e}"
                            )
                    else:
                        error_text = await response.text()
                        return APIResponse(
                            url=str(response.url),
                            status=response.status,
                            data=None,
                            headers=dict(response.headers),
                            response_time=response_time,
                            success=False,
                            error=f"HTTP {response.status}: {error_text}"
                        )

            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                return APIResponse(
                    url=url,
                    status=0,
                    data=None,
                    headers={},
                    response_time=response_time,
                    success=False,
                    error="Request timeout"
                )
            except Exception as e:
                response_time = time.time() - start_time
                return APIResponse(
                    url=url,
                    status=0,
                    data=None,
                    headers={},
                    response_time=response_time,
                    success=False,
                    error=f"Request error: {e}"
                )
            finally:
                # Rate limiting delay
                await asyncio.sleep(self.rate_limit_delay)

    async def fetch_page(self, base_url: str, params: Optional[Dict[str, Any]] = None,
                        page: int = 1, limit: int = 250) -> APIResponse:
        """Fetch a specific page of data."""
        request_params = params.copy() if params else {}
        request_params.update({
            'page': page,
            'limit': limit
        })

        return await self._make_request(base_url, request_params)

    async def fetch_all_pages(self, base_url: str, params: Optional[Dict[str, Any]] = None,
                             max_pages: Optional[int] = None, limit: int = 250) -> List[APIResponse]:
        """Fetch all pages of data concurrently."""
        # First, get the first page to determine total pages
        first_response = await self.fetch_page(base_url, params, page=1, limit=limit)

        if not first_response.success:
            return [first_response]

        try:
            # Extract pagination info
            pagination = first_response.data.get('pagination', {})
            total_pages = pagination.get('count', 1)

            if max_pages:
                total_pages = min(total_pages, max_pages)

            if total_pages <= 1:
                return [first_response]

            # Create tasks for remaining pages
            tasks = []
            for page in range(2, total_pages + 1):
                task = self.fetch_page(base_url, params, page=page, limit=limit)
                tasks.append(task)

            # Execute all requests concurrently
            remaining_responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results
            all_responses = [first_response]

            for response in remaining_responses:
                if isinstance(response, Exception):
                    # Handle exceptions as failed responses
                    error_response = APIResponse(
                        url=base_url,
                        status=0,
                        data=None,
                        headers={},
                        response_time=0.0,
                        success=False,
                        error=f"Exception: {response}"
                    )
                    all_responses.append(error_response)
                else:
                    all_responses.append(response)

            return all_responses

        except (KeyError, TypeError) as e:
            logger.warning(f"Could not parse pagination info: {e}")
            return [first_response]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the session."""
        if not self.request_times:
            return {'total_requests': 0}

        return {
            'total_requests': len(self.request_times),
            'avg_response_time': sum(self.request_times) / len(self.request_times),
            'min_response_time': min(self.request_times),
            'max_response_time': max(self.request_times),
            'total_time': sum(self.request_times)
        }

async def fetch_congress_data_async(base_url: str, api_key: str, params: Optional[Dict[str, Any]] = None,
                                   max_pages: Optional[int] = None, max_concurrent: int = 5) -> List[APIResponse]:
    """Convenience function to fetch Congress data asynchronously."""
    async with AsyncCongressClient(api_key, max_concurrent=max_concurrent) as client:
        responses = await client.fetch_all_pages(base_url, params, max_pages)
        return responses

def extract_successful_data(responses: List[APIResponse]) -> List[Dict[str, Any]]:
    """Extract successful response data from a list of API responses."""
    successful_data = []
    for response in responses:
        if response.success and response.data:
            successful_data.append(response.data)
    return successful_data
