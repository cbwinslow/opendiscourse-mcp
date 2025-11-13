#!/usr/bin/env python3

"""
Activity Logger - Tracks user activity including applications, websites, typing, and interactions
"""

import time
import json
import psutil
import psycopg2
import os
from datetime import datetime
from pynput import mouse, keyboard
from threading import Thread, Event
from collections import defaultdict

class ActivityLogger:
    def __init__(self, db_url, log_interval=60):
        self.db_url = db_url
        self.log_interval = log_interval
        self.stop_event = Event()
        
        # Activity tracking
        self.keystrokes = 0
        self.mouse_clicks = 0
        self.current_app = None
        self.current_window = None
        self.app_times = defaultdict(float)
        self.last_activity = time.time()
        
        # Database connection
        self.conn = None
        self.connect_db()
        
    def connect_db(self):
        """Connect to monitoring database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print("✅ Connected to monitoring database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def on_key_press(self, event):
        """Handle keyboard events"""
        self.keystrokes += 1
        self.last_activity = time.time()
    
    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse events"""
        if pressed:
            self.mouse_clicks += 1
            self.last_activity = time.time()
    
    def get_active_window_info(self):
        """Get current active window information"""
        try:
            # This is a simplified version - in production you'd use platform-specific methods
            active_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 0.1:  # Active processes
                        active_processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if active_processes:
                # Get most active process
                most_active = max(active_processes, key=lambda x: x['cpu_percent'])
                return most_active['name'], f"Process {most_active['pid']}"
        except Exception as e:
            print(f"Error getting window info: {e}")
        
        return None, None
    
    def get_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_gb = disk.used / (1024**3)
            
            # Network
            network = psutil.net_io_counters()
            
            # Processes and uptime
            active_processes = len([p for p in psutil.process_iter() if p.status() == 'running'])
            uptime_seconds = time.time() - psutil.boot_time()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_usage_gb': disk_usage_gb,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'active_processes': active_processes,
                'uptime_seconds': int(uptime_seconds)
            }
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return None
    
    def log_activity(self):
        """Log current activity to database"""
        try:
            # Get current window info
            app_name, window_title = self.get_active_window_info()
            
            # Calculate duration since last log
            current_time = time.time()
            duration = int(current_time - self.last_activity)
            
            # Get system metrics
            system_metrics = self.get_system_metrics()
            
            # Prepare activity data
            activity_data = {
                'timestamp': datetime.now(),
                'activity_type': 'user_activity',
                'application': app_name,
                'window_title': window_title,
                'duration_seconds': duration,
                'keystrokes': self.keystrokes,
                'mouse_clicks': self.mouse_clicks,
                'raw_data': {
                    'system_metrics': system_metrics,
                    'active_processes': len(list(psutil.process_iter()))
                }
            }
            
            # Insert into database
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO activity_logs 
                (activity_type, application, website, duration_seconds, 
                 keystrokes, mouse_clicks, window_title, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                activity_data['activity_type'],
                activity_data['application'],
                None,  # website - would need browser extension
                activity_data['duration_seconds'],
                activity_data['keystrokes'],
                activity_data['mouse_clicks'],
                activity_data['window_title'],
                json.dumps(activity_data['raw_data'])
            ))
            
            # Log system metrics separately
            if system_metrics:
                cursor.execute("""
                    INSERT INTO system_metrics 
                    (cpu_percent, memory_percent, disk_usage_gb, 
                     network_bytes_sent, network_bytes_recv, active_processes, uptime_seconds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    system_metrics['cpu_percent'],
                    system_metrics['memory_percent'],
                    system_metrics['disk_usage_gb'],
                    system_metrics['network_bytes_sent'],
                    system_metrics['network_bytes_recv'],
                    system_metrics['active_processes'],
                    system_metrics['uptime_seconds']
                ))
            
            self.conn.commit()
            cursor.close()
            
            # Reset counters
            self.keystrokes = 0
            self.mouse_clicks = 0
            self.last_activity = current_time
            
            print(f"📊 Activity logged: {app_name} - {duration}s, {self.keystrokes} keys, {self.mouse_clicks} clicks")
            
        except Exception as e:
            print(f"❌ Error logging activity: {e}")
            if self.conn:
                self.conn.rollback()
    
    def start_monitoring(self):
        """Start activity monitoring"""
        print("🚀 Starting activity monitoring...")
        
        # Start input listeners in separate threads
        keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        
        keyboard_listener.start()
        mouse_listener.start()
        
        print("✅ Input listeners started")
        
        # Main logging loop
        try:
            while not self.stop_event.is_set():
                time.sleep(self.log_interval)
                if not self.stop_event.is_set():
                    self.log_activity()
        except KeyboardInterrupt:
            print("\n⏹️ Stopping activity monitoring...")
        finally:
            # Cleanup
            keyboard_listener.stop()
            mouse_listener.stop()
            if self.conn:
                self.conn.close()
            print("✅ Activity monitoring stopped")
    
    def stop(self):
        """Stop monitoring"""
        self.stop_event.set()

if __name__ == "__main__":
    # Load environment
    db_url = os.getenv('MONITORING_DB', 'postgresql://cbwinslow@localhost:5432/monitoring_db')
    log_interval = int(os.getenv('ACTIVITY_LOG_INTERVAL', '60'))
    
    # Start monitoring
    logger = ActivityLogger(db_url, log_interval)
    
    try:
        logger.start_monitoring()
    except KeyboardInterrupt:
        logger.stop()