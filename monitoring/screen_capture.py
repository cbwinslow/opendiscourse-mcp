#!/usr/bin/env python3

"""
Screen Capture System - Automated screenshot capture with analysis
"""

import time
import os
import json
import psycopg2
from datetime import datetime
from mss import mss
from PIL import Image
import requests

class ScreenCapture:
    def __init__(self, db_url, capture_interval=30, output_dir="./screenshots"):
        self.db_url = db_url
        self.capture_interval = capture_interval
        self.output_dir = output_dir
        self.stop_event = False
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Database connection
        self.conn = None
        self.connect_db()
        
        # Screen capture object
        self.sct = mss()
    
    def connect_db(self):
        """Connect to monitoring database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print("✅ Screen capture connected to database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def capture_screen(self):
        """Capture and save screenshot"""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/screen_{timestamp}.png"
            
            # Capture screen
            screenshot = self.sct.shot(output=filename)
            
            # Get file info
            file_size = os.path.getsize(filename)
            
            # Get screen resolution
            with Image.open(filename) as img:
                resolution = f"{img.width}x{img.height}"
            
            # Analyze screenshot with Ollama (basic analysis)
            analysis = self.analyze_screenshot(filename)
            
            # Store in database
            self.store_screen_capture(filename, file_size, resolution, analysis)
            
            print(f"📸 Screenshot captured: {filename} ({file_size} bytes)")
            return filename
            
        except Exception as e:
            print(f"❌ Error capturing screen: {e}")
            return None
    
    def analyze_screenshot(self, image_path):
        """Analyze screenshot with Ollama"""
        try:
            # For now, we'll do basic analysis based on time and patterns
            # In future, can integrate vision models
            
            current_hour = datetime.now().hour
            
            # Basic context based on time
            if 9 <= current_hour <= 17:
                context = "Work hours - likely productive activity"
            elif 18 <= current_hour <= 22:
                context = "Evening - could be work or leisure"
            else:
                context = "Late night - possibly personal time"
            
            # Try to get Ollama analysis if available
            try:
                prompt = f"""
                Analyze this screenshot context based on timestamp {datetime.now()}.
                
                {context}
                
                Provide a brief analysis (under 30 words) about likely user activity.
                Focus on: work vs leisure, productivity level, general context.
                """
                
                response = requests.post('http://localhost:11434/api/generate', 
                                      json={
                                          'model': 'llama3.2:1b',
                                          'prompt': prompt,
                                          'stream': False
                                      }, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', context)
                    
            except Exception as e:
                print(f"Ollama analysis failed: {e}")
            
            return context
            
        except Exception as e:
            print(f"❌ Error analyzing screenshot: {e}")
            return "Screenshot captured successfully"
    
    def store_screen_capture(self, filename, file_size, resolution, analysis):
        """Store screenshot information in database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO screen_captures 
                (file_path, file_size, resolution, analysis_result, summary)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                filename,
                file_size,
                resolution,
                analysis,
                analysis[:100]  # Summary is truncated analysis
            ))
            
            self.conn.commit()
            cursor.close()
            
        except Exception as e:
            print(f"❌ Error storing screenshot data: {e}")
            if self.conn:
                self.conn.rollback()
    
    def start_capture(self):
        """Start continuous screen capture"""
        print(f"📸 Starting screen capture every {self.capture_interval} seconds...")
        
        try:
            while not self.stop_event:
                self.capture_screen()
                
                # Sleep in small intervals to allow quick stop
                for _ in range(self.capture_interval):
                    if self.stop_event:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n⏹️ Stopping screen capture...")
        finally:
            if self.conn:
                self.conn.close()
            print("✅ Screen capture stopped")
    
    def stop(self):
        """Stop screen capture"""
        self.stop_event = True

if __name__ == "__main__":
    import os
    
    # Load environment
    db_url = os.getenv('MONITORING_DB', 'postgresql://cbwinslow@localhost:5432/monitoring_db')
    capture_interval = int(os.getenv('SCREEN_CAPTURE_INTERVAL', '30'))
    output_dir = os.getenv('SCREENSHOT_DIR', './screenshots')
    
    # Start screen capture
    capturer = ScreenCapture(db_url, capture_interval, output_dir)
    
    try:
        capturer.start_capture()
    except KeyboardInterrupt:
        capturer.stop()