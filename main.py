import os
import threading
import time
import csv
from datetime import datetime
from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
import tkinter as tk
from tkinter import messagebox, simpledialog
import requests
import sys
import queue
from PIL import ImageGrab, ImageFilter
import boto3
import aws_s3
import shutil
import gzip


# Constants
SCREENSHOT_INTERVAL_DEFAULT = 15
UPLOAD_INTERVAL = 120  # 2 minutes
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for uploading
INSTANCE_LOCK_FILE = 'app.lock'
SCREENSHOT_DIRECTORY = 'screenshots'
KEYBOARD_LOG_FILE = 'keyboard_activity_log.csv'
MOUSE_LOG_FILE = 'mouse_activity_log.csv'
AWS_BUCKET_NAME = ''

# Globals
stop_threads = threading.Event()

class InstanceManager:
   
    def create_instance_lock():
        if os.path.exists(INSTANCE_LOCK_FILE):
            print("Another instance of the application is already running.")
            sys.exit(1)
        with open(INSTANCE_LOCK_FILE, 'w') as file:
            file.write("Lock file to prevent multiple instances.")

    
    def remove_instance_lock():
        if os.path.exists(INSTANCE_LOCK_FILE):
            os.remove(INSTANCE_LOCK_FILE)

class FileManager:
    def archive_old_files(directory, max_age_days=30):
        now = time.time()
        cutoff = now - (max_age_days * 86400)  # Convert days to seconds
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
                archive_path = f"{file_path}.gz"
                with open(file_path, 'rb') as f_in, gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(file_path)
                print(f"Archived old file: {file_path}")
  
    def ensure_directory_exists(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    
    def initialize_files():
        if not os.path.exists(KEYBOARD_LOG_FILE):
            with open(KEYBOARD_LOG_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Timestamp', 'Key Pressed', 'Unusual Activity'])

        if not os.path.exists(MOUSE_LOG_FILE):
            with open(MOUSE_LOG_FILE, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Timestamp', 'Mouse Movement', 'Unusual Activity'])

class ScreenshotManager:
    def __init__(self, interval=SCREENSHOT_INTERVAL_DEFAULT, blur=True, capture=True):
        self.screenshot_interval = interval
        self.blur_screenshots = blur
        self.capture_screenshots = capture
        FileManager.ensure_directory_exists(SCREENSHOT_DIRECTORY)

    def take_screenshot_auto(self):
        try:
            image = ImageGrab.grab()
            if self.blur_screenshots:
                image = image.filter(ImageFilter.GaussianBlur(5))
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            screenshot_path = f'{SCREENSHOT_DIRECTORY}/screenshot_{timestamp}.png'
            image.save(screenshot_path)
            print(f"Screenshot taken: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"Failed to take screenshot: {e}")
            return None

    def run_screenshot_module(self):
        try:
            while not stop_threads.is_set():
                if self.capture_screenshots:
                    screenshot_path = self.take_screenshot_auto()
                    if screenshot_path:
                        FileUploader.upload_file(screenshot_path, AWS_BUCKET_NAME)
                stop_threads.wait(self.screenshot_interval)
        except Exception as e:
            print(f"Screenshot module error: {e}")

class ActivityLogger:
    
    def save_keyboard_activity(timestamp, key, unusual_activity):
        with open(KEYBOARD_LOG_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'), str(key), unusual_activity])
        print(f"Keyboard activity saved: {key}")

    
    def save_mouse_activity(timestamp, movement, unusual_activity):
        with open(MOUSE_LOG_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'), movement, unusual_activity])
        print(f"Mouse activity saved: {movement}")

class FileUploader:
    upload_queue = queue.Queue()

   
    def check_internet_connection():
        try:
            requests.get("https://www.google.com", timeout=5)
            return True
        except requests.ConnectionError:
            return False
        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")
            return False

    
    def upload_with_retry(file_path, bucket_name):
        while True:
            if FileUploader.check_internet_connection():
                try:
                    if aws_s3.upload_to_s3(file_path, bucket_name):
                        print(f"Successfully uploaded {file_path}")
                        return
                    else:
                        print(f"Failed to upload {file_path}. Retrying...")
                except Exception as e:
                    print(f"Error during upload: {e}")
            else:
                print(f"No internet connection. Retrying in 30 seconds...")
            stop_threads.wait(30)

    
    def upload_file(file_path, bucket_name):
        if FileUploader.check_internet_connection():
            FileUploader.upload_with_retry(file_path, bucket_name)
        else:
            FileUploader.upload_queue.put((file_path, bucket_name))
            print(f"No internet. Queued file: {file_path}")

   
    def process_upload_queue():
        while not stop_threads.is_set():
            if not FileUploader.upload_queue.empty() and FileUploader.check_internet_connection():
                file_path, bucket_name = FileUploader.upload_queue.get()
                FileUploader.upload_with_retry(file_path, bucket_name)
            stop_threads.wait(10)

class Application:
    def __init__(self):
        self.screenshot_manager = ScreenshotManager()
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.mouse_thread = threading.Thread(target=self.mouse_listener, daemon=True)
        self.screenshot_thread = threading.Thread(target=self.screenshot_manager.run_screenshot_module, daemon=True)
        self.upload_thread = threading.Thread(target=FileUploader.process_upload_queue, daemon=True)
        self.save_thread = threading.Thread(target=self.save_and_upload_files, daemon=True)
        
    def create_app(self):
        root = tk.Tk()
        root.title("Activity Monitor")

        # Set font for clear text display
        font = ("Arial", 12)

        def update_screenshot_interval():
            try:
                interval = simpledialog.askinteger("Input", "Enter screenshot interval in seconds:", parent=root)
                if interval is not None and interval > 0:
                    self.screenshot_manager.screenshot_interval = interval
                    print(f"Screenshot interval set to {interval} seconds.")
            except Exception as e:
                print(f"An error occurred: {e}")

        def toggle_capture_screenshots():
            self.screenshot_manager.capture_screenshots = not self.screenshot_manager.capture_screenshots
            status = "enabled" if self.screenshot_manager.capture_screenshots else "disabled"
            messagebox.showinfo("Screenshot Capture", f"Screenshot capture is now {status}.")

        def toggle_blur_screenshots():
            self.screenshot_manager.blur_screenshots = not self.screenshot_manager.blur_screenshots
            status = "blurred" if self.screenshot_manager.blur_screenshots else "unblurred"
            messagebox.showinfo("Screenshot Blurring", f"Screenshots will now be {status}.")

        def take_screenshot_now():
            screenshot_path = self.screenshot_manager.take_screenshot_auto()
            if screenshot_path:
                FileUploader.upload_file(screenshot_path, AWS_BUCKET_NAME)

        def on_exit():
            print("Stopping all threads and exiting the application...")
            stop_threads.set()

            # Attempt to join threads with a timeout
            app.keyboard_thread.join(timeout=5)
            app.mouse_thread.join(timeout=5)
            app.screenshot_thread.join(timeout=5)
            app.upload_thread.join(timeout=5)
            app.save_thread.join(timeout=5)

            # Check if threads are still alive, force exit if needed
            if any(thread.is_alive() for thread in [
                app.keyboard_thread, 
                app.mouse_thread, 
                app.screenshot_thread, 
                app.upload_thread, 
                app.save_thread
            ]):
                print("Forcing termination of remaining threads...")
                # Remove the instance lock and exit gracefully
                InstanceManager.remove_instance_lock()
                os._exit(1)  # Forcefully terminate the program

            sys.exit(0)

        root.protocol("WM_DELETE_WINDOW", on_exit)

        screenshot_button = tk.Button(root, text="Take Screenshot", font=font, command=take_screenshot_now)
        screenshot_button.pack(pady=10)

        interval_button = tk.Button(root, text="Set Screenshot Interval", font=font, command=update_screenshot_interval)
        interval_button.pack(pady=10)

        capture_button = tk.Button(root, text="Toggle Screenshot Capture", font=font, command=toggle_capture_screenshots)
        capture_button.pack(pady=10)

        blur_button = tk.Button(root, text="Toggle Screenshot Blurring", font=font, command=toggle_blur_screenshots)
        blur_button.pack(pady=10)

        exit_button = tk.Button(root, text="Exit", font=font, command=on_exit)
        exit_button.pack(pady=10)

        root.protocol("WM_DELETE_WINDOW", on_exit)
        root.mainloop()

    def keyboard_listener(self):
        def on_press(key):
            timestamp = time.time()
            try:
                ActivityLogger.save_keyboard_activity(timestamp, key.char, '')
            except AttributeError:
                ActivityLogger.save_keyboard_activity(timestamp, key, '')

        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    def mouse_listener(self):
        def on_move(x, y):
            timestamp = time.time()
            ActivityLogger.save_mouse_activity(timestamp, f"Moved to ({x}, {y})", '')

        def on_click(x, y, button, pressed):
            timestamp = time.time()
            ActivityLogger.save_mouse_activity(timestamp, f"Clicked at ({x}, {y}) with {button}", '')

        with pynput_mouse.Listener(on_move=on_move, on_click=on_click) as listener:
            listener.join()

    def save_and_upload_files(self):
        while not stop_threads.is_set():
            time.sleep(UPLOAD_INTERVAL)
            FileUploader.upload_file(KEYBOARD_LOG_FILE, AWS_BUCKET_NAME)
            FileUploader.upload_file(MOUSE_LOG_FILE, AWS_BUCKET_NAME)

    def start(self):
        InstanceManager.create_instance_lock()
        FileManager.initialize_files()
        self.keyboard_thread.start()
        self.mouse_thread.start()
        self.screenshot_thread.start()
        self.upload_thread.start()
        self.save_thread.start()
        self.create_app()

    def stop(self):
        stop_threads.set()
        self.keyboard_thread.join()
        self.mouse_thread.join()
        self.screenshot_thread.join()
        self.upload_thread.join()
        self.save_thread.join()
        InstanceManager.remove_instance_lock()

if __name__ == "__main__":
    app = Application()
    try:
        app.start()
    except KeyboardInterrupt:
        print("Application stopped by user.")
    finally:
        app.stop()
