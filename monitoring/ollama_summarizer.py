#!/usr/bin/env python3

"""
Ollama Summarizer - Real-time activity summarization using Ollama
"""

import time
import json
import requests
import psycopg2
import os
from datetime import datetime, timedelta
from threading import Thread

class OllamaSummarizer:
    def __init__(self, db_url, ollama_host="http://localhost:11434", model="llama3.2:1b"):
        self.db_url = db_url
        self.ollama_host = ollama_host
        self.model = model
        self.stop_event = False
        
        # Database connection
        self.conn = None
        self.connect_db()
        
        # Check Ollama availability
        self.check_ollama()
    
    def connect_db(self):
        """Connect to monitoring database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print("✅ Summarizer connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def check_ollama(self):
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.ollama_host}/api/version", timeout=5)
            if response.status_code == 200:
                version = response.json().get('version', 'unknown')
                print(f"✅ Ollama connected (version: {version})")
                return True
            else:
                print("❌ Ollama not responding")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to Ollama: {e}")
            return False
    
    def get_recent_activity(self, hours=1):
        """Get recent activity data for summarization"""
        try:
            cursor = self.conn.cursor()
            
            # Get activity from last N hours
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT activity_type, application, window_title, duration_seconds,
                       keystrokes, mouse_clicks, timestamp, raw_data
                FROM activity_logs 
                WHERE timestamp >= %s AND summary IS NULL
                ORDER BY timestamp DESC
                LIMIT 50
            """, (since_time,))
            
            activities = cursor.fetchall()
            cursor.close()
            
            return activities
            
        except Exception as e:
            print(f"❌ Error getting recent activity: {e}")
            return []
    
    def summarize_activities(self, activities):
        """Summarize activities using Ollama"""
        if not activities:
            return None
        
        try:
            # Prepare activity summary for Ollama
            activity_text = self.format_activities_for_ollama(activities)
            
            prompt = f"""
            Analyze and summarize the following user activity data:
            
            {activity_text}
            
            Provide a concise summary focusing on:
            1. Primary applications used and time allocation
            2. Productivity patterns and work focus
            3. Notable behaviors or patterns
            4. Overall activity level
            
            Keep the summary under 100 words and be insightful but brief.
            """
            
            response = requests.post(f"{self.ollama_host}/api/generate", 
                                  json={
                                      'model': self.model,
                                      'prompt': prompt,
                                      'stream': False,
                                      'options': {
                                          'temperature': 0.3,
                                          'top_p': 0.9
                                      }
                                  }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('response', '').strip()
                return summary
            else:
                print(f"❌ Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return None
    
    def format_activities_for_ollama(self, activities):
        """Format activities for Ollama prompt"""
        if not activities:
            return "No recent activity data available."
        
        # Group activities by application
        app_summary = {}
        total_time = 0
        total_keystrokes = 0
        total_clicks = 0
        
        for activity in activities:
            app = activity[1] or 'Unknown'
            duration = activity[3] or 0
            keystrokes = activity[4] or 0
            clicks = activity[5] or 0
            
            if app not in app_summary:
                app_summary[app] = {'time': 0, 'keystrokes': 0, 'clicks': 0, 'windows': set()}
            
            app_summary[app]['time'] += duration
            app_summary[app]['keystrokes'] += keystrokes
            app_summary[app]['clicks'] += clicks
            app_summary[app]['windows'].add(activity[2] or 'Unknown window')
            
            total_time += duration
            total_keystrokes += keystrokes
            total_clicks += clicks
        
        # Format for Ollama
        formatted = f"Activity Summary (Last {len(activities)} events):\n\n"
        
        for app, data in app_summary.items():
            formatted += f"• {app}: {data['time']}s total, {data['keystrokes']} keystrokes, {data['clicks']} clicks\n"
        
        formatted += f"\nTotal Activity: {total_time}s, {total_keystrokes} keystrokes, {total_clicks} clicks"
        formatted += f"\nTime Period: {activities[0][6]} to {activities[-1][6]}"
        
        return formatted
    
    def store_summary(self, activity_ids, summary):
        """Store summary in database"""
        try:
            cursor = self.conn.cursor()
            
            # Update activities with summary
            for activity_id in activity_ids:
                cursor.execute("""
                    UPDATE activity_logs 
                    SET summary = %s 
                    WHERE id = %s
                """, (summary, activity_id))
            
            self.conn.commit()
            cursor.close()
            
            print(f"📝 Summary stored for {len(activity_ids)} activities")
            
        except Exception as e:
            print(f"❌ Error storing summary: {e}")
            if self.conn:
                self.conn.rollback()
    
    def process_summaries(self):
        """Main processing loop for summaries"""
        print("🤖 Starting Ollama summarizer...")
        
        while not self.stop_event:
            try:
                # Get recent uns summarized activities
                activities = self.get_recent_activity(hours=1)
                
                if activities:
                    print(f"📊 Processing {len(activities)} activities for summary...")
                    
                    # Generate summary
                    summary = self.summarize_activities(activities)
                    
                    if summary:
                        # Get activity IDs
                        activity_ids = [activity[0] for activity in activities]
                        
                        # Store summary
                        self.store_summary(activity_ids, summary)
                        
                        print(f"📝 Summary generated: {summary[:100]}...")
                    else:
                        print("⚠️ Failed to generate summary")
                
                # Wait before next batch
                time.sleep(300)  # Process every 5 minutes
                
            except Exception as e:
                print(f"❌ Error in summary processing: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def start(self):
        """Start the summarizer"""
        if not self.check_ollama():
            print("❌ Ollama not available. Please start Ollama first.")
            return
        
        # Start processing in background thread
        self.process_thread = Thread(target=self.process_summaries)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        print("✅ Ollama summarizer started")
    
    def stop(self):
        """Stop the summarizer"""
        self.stop_event = True
        if hasattr(self, 'process_thread'):
            self.process_thread.join(timeout=10)
        
        if self.conn:
            self.conn.close()
        
        print("✅ Ollama summarizer stopped")

if __name__ == "__main__":
    # Load environment
    db_url = os.getenv('MONITORING_DB', 'postgresql://cbwinslow@localhost:5432/monitoring_db')
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    
    # Start summarizer
    summarizer = OllamaSummarizer(db_url, ollama_host)
    
    try:
        summarizer.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Stopping Ollama summarizer...")
        summarizer.stop()