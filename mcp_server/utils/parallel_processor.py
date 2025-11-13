"""Parallel processing utilities for high-performance data ingestion with Congress session isolation."""

import asyncio
import concurrent.futures
from typing import Dict, List, Any, Callable, Optional, TypeVar, Generic
import threading
import time
from dataclasses import dataclass
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class ProcessingResult(Generic[T]):
    """Result container for parallel processing operations."""
    congress: int
    data_type: str
    success: bool
    records_processed: int
    duration: float
    result: Optional[T] = None
    error: Optional[str] = None

class CongressSessionProcessor:
    """Processes data for individual Congress sessions with isolation."""

    def __init__(self, congress: int, max_workers: int = 4):
        self.congress = congress
        self.max_workers = max_workers
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=f"Congress-{congress}"
        )
        self.local_data = threading.local()

    def process_data_type(self, data_type: str, processor_func: Callable,
                         *args, **kwargs) -> ProcessingResult:
        """Process a specific data type for this Congress session."""
        start_time = time.time()

        try:
            # Execute the processor function
            result = processor_func(*args, **kwargs)

            duration = time.time() - start_time

            # Extract record count if possible
            records_processed = getattr(result, 'records_processed', 0)
            if isinstance(result, dict) and 'count' in result:
                records_processed = result['count']
            elif isinstance(result, list):
                records_processed = len(result)

            return ProcessingResult(
                congress=self.congress,
                data_type=data_type,
                success=True,
                records_processed=records_processed,
                duration=duration,
                result=result
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error processing {data_type} for Congress {self.congress}: {e}")

            return ProcessingResult(
                congress=self.congress,
                data_type=data_type,
                success=False,
                records_processed=0,
                duration=duration,
                error=str(e)
            )

    async def process_data_types_async(self, data_types: List[str],
                                      processor_factory: Callable[[str], Callable]) -> List[ProcessingResult]:
        """Process multiple data types asynchronously for this Congress session."""
        loop = asyncio.get_event_loop()

        # Create tasks for each data type
        tasks = []
        for data_type in data_types:
            processor_func = processor_factory(data_type)
            task = loop.run_in_executor(
                self.thread_pool,
                self.process_data_type,
                data_type,
                processor_func
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                data_type = data_types[i]
                processed_results.append(ProcessingResult(
                    congress=self.congress,
                    data_type=data_type,
                    success=False,
                    records_processed=0,
                    duration=0.0,
                    error=f"Exception: {result}"
                ))
            else:
                processed_results.append(result)

        return processed_results

    def shutdown(self):
        """Shutdown the thread pool."""
        self.thread_pool.shutdown(wait=True)

class ParallelCongressProcessor:
    """Manages parallel processing across multiple Congress sessions."""

    def __init__(self, max_concurrent_sessions: int = 3, workers_per_session: int = 2):
        self.max_concurrent_sessions = max_concurrent_sessions
        self.workers_per_session = workers_per_session
        self.session_processors: Dict[int, CongressSessionProcessor] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_sessions)

    async def process_congress_session(self, congress: int, data_types: List[str],
                                     processor_factory: Callable[[str], Callable]) -> List[ProcessingResult]:
        """Process all data types for a single Congress session."""
        async with self.semaphore:
            # Create or reuse session processor
            if congress not in self.session_processors:
                self.session_processors[congress] = CongressSessionProcessor(
                    congress=congress,
                    max_workers=self.workers_per_session
                )

            processor = self.session_processors[congress]

            # Process all data types for this session
            results = await processor.process_data_types_async(data_types, processor_factory)

            return results

    async def process_multiple_sessions(self, congresses: List[int], data_types: List[str],
                                      processor_factory: Callable[[str], Callable]) -> Dict[int, List[ProcessingResult]]:
        """Process multiple Congress sessions in parallel with session isolation."""
        logger.info(f"Processing {len(congresses)} Congress sessions with max {self.max_concurrent_sessions} concurrent")

        # Create tasks for each Congress session
        tasks = []
        for congress in congresses:
            task = self.process_congress_session(congress, data_types, processor_factory)
            tasks.append((congress, task))

        # Execute all sessions concurrently (but isolated)
        session_results = {}
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # Map results back to congress numbers
        for i, (congress, _) in enumerate(tasks):
            result = completed_tasks[i]
            if isinstance(result, Exception):
                logger.error(f"Session {congress} failed with exception: {result}")
                session_results[congress] = [ProcessingResult(
                    congress=congress,
                    data_type="session",
                    success=False,
                    records_processed=0,
                    duration=0.0,
                    error=f"Session exception: {result}"
                )]
            else:
                session_results[congress] = result

        return session_results

    def shutdown(self):
        """Shutdown all session processors."""
        for processor in self.session_processors.values():
            processor.shutdown()
        self.session_processors.clear()

@contextmanager
def congress_session_isolation(congress: int):
    """Context manager for Congress session data isolation."""
    # Set thread-local storage for this Congress session
    thread_local = threading.local()
    thread_local.congress = congress
    thread_local.session_data = {}

    try:
        yield thread_local
    finally:
        # Clean up session data
        if hasattr(thread_local, 'session_data'):
            thread_local.session_data.clear()

def get_current_congress() -> Optional[int]:
    """Get the current Congress session from thread-local storage."""
    thread_local = threading.current_thread()
    if hasattr(thread_local, 'congress'):
        return thread_local.congress
    return None

def create_congress_processor_factory(base_processor: Callable) -> Callable[[str], Callable]:
    """Create a processor factory that binds Congress session context."""
    def factory(data_type: str) -> Callable:
        def processor(*args, **kwargs):
            congress = get_current_congress()
            if congress is None:
                raise RuntimeError("No Congress session context available")

            # Bind the Congress to the processor
            return base_processor(data_type, congress, *args, **kwargs)

        return processor

    return factory
