"""Progress tracking utilities for data ingestion with visual progress bars."""

import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, MofNCompleteColumn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import psutil
import os

console = Console()

class IngestionProgressTracker:
    """Tracks progress of data ingestion operations with visual feedback."""

    def __init__(self, description: str = "Processing"):
        self.description = description
        self.start_time = time.time()
        self.records_processed = 0
        self.total_records = 0
        self.current_operation = ""
        self.progress = None
        self.task_id = None

    def initialize(self, total_records: Optional[int] = None, description: str = None):
        """Initialize the progress tracker."""
        if description:
            self.description = description

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            TextColumn("[dim]{task.fields[operation]}"),
            console=console,
            refresh_per_second=2,
        )

        self.progress.start()
        self.task_id = self.progress.add_task(
            self.description,
            total=total_records or 100,  # Default to 100 if unknown
            operation="Initializing...",
            records_processed=0
        )

        if total_records:
            self.total_records = total_records
            self.progress.update(self.task_id, total=total_records)

    def update_progress(self, records_added: int = 0, operation: str = None):
        """Update progress with new records processed."""
        if operation:
            self.current_operation = operation

        self.records_processed += records_added

        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=self.records_processed,
                operation=self.current_operation or "Processing...",
                records_processed=self.records_processed
            )

    def set_operation(self, operation: str):
        """Set the current operation description."""
        self.current_operation = operation
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, operation=operation)

    def set_total(self, total: int):
        """Set the total number of records to process."""
        self.total_records = total
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, total=total)

    def get_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        elapsed = time.time() - self.start_time
        rate = self.records_processed / elapsed if elapsed > 0 else 0

        return {
            'records_processed': self.records_processed,
            'total_records': self.total_records,
            'elapsed_time': elapsed,
            'processing_rate': rate,
            'percent_complete': (self.records_processed / self.total_records * 100) if self.total_records > 0 else 0,
            'current_operation': self.current_operation
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource usage statistics."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_used_mb': memory_info.rss / 1024 / 1024,
            'memory_percent': process.memory_percent()
        }

    def display_summary(self):
        """Display a final summary of the ingestion process."""
        stats = self.get_stats()
        system_stats = self.get_system_stats()

        summary_text = Text()
        summary_text.append("🎉 Ingestion Complete!\n\n", style="bold green")
        summary_text.append(f"📊 Records Processed: {stats['records_processed']:,}\n")
        summary_text.append(f"⏱️  Total Time: {stats['elapsed_time']:.2f} seconds\n")
        summary_text.append(f"⚡ Processing Rate: {stats['processing_rate']:.1f} records/sec\n")
        summary_text.append(f"💾 Memory Used: {system_stats['memory_used_mb']:.1f} MB\n")
        summary_text.append(f"🖥️  CPU Usage: {system_stats['cpu_percent']:.1f}%\n")

        if stats['total_records'] > 0:
            summary_text.append(f"📈 Completion: {stats['percent_complete']:.1f}%\n")

        panel = Panel(summary_text, title="📋 Ingestion Summary", border_style="green")
        console.print(panel)

    def finish(self):
        """Complete the progress tracking and display summary."""
        if self.progress:
            self.progress.update(self.task_id, operation="Complete!")
            self.progress.stop()

        self.display_summary()

@contextmanager
def track_progress(description: str = "Processing", total: Optional[int] = None):
    """Context manager for progress tracking."""
    tracker = IngestionProgressTracker(description)
    tracker.initialize(total, description)

    try:
        yield tracker
    finally:
        tracker.finish()

def create_congress_progress_tracker(congress: int, data_type: str) -> IngestionProgressTracker:
    """Create a progress tracker specifically for Congress data ingestion."""
    description = f"🏛️ Congress {congress} - {data_type.title()}"
    return IngestionProgressTracker(description)
