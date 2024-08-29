import time
import csv
import threading
import pynput.mouse as mouse
import pynput.keyboard as keyboard
import boto3
from botocore.exceptions import NoCredentialsError

# Configuration
movement_threshold = 50  # Minimum movement in pixels to consider as unusual
inactivity_threshold = 10  # Seconds of inactivity to consider as unusual
upload_interval = 120  # 2 minutes
chunk_size = 1024 * 1024  # 1MB chunks for uploading

# Global variables
last_mouse_position = (0, 0)
last_activity_time = time.time()
is_typing = False

mouse_activity_data = []
keyboard_activity_data = []

mouse_log_file = "mouse_activity_log.csv"
keyboard_log_file = "keyboard_activity_log.csv"

# AWS S3 configuration
s3_bucket = "your-bucket-name"
s3_client = boto3.client('s3', aws_access_key_id='your-access-key', aws_secret_access_key='your-secret-key')

def on_move(x, y):
    global last_mouse_position, last_activity_time, mouse_activity_data
    current_position = (x, y)
    distance = ((current_position[0] - last_mouse_position[0])**2 + (current_position[1] - last_mouse_position[1])**2)**0.5
    if distance > movement_threshold:
        print(f"Unusual mouse movement detected: Moved {distance:.2f} pixels.")
    mouse_activity_data.append([time.time(), "move", x, y])
    last_mouse_position = current_position
    last_activity_time = time.time()

def on_click(x, y, button, pressed):
    global last_activity_time, mouse_activity_data
    if pressed:
        print(f"Mouse clicked at ({x}, {y}) with {button}")
        mouse_activity_data.append([time.time(), "click", x, y])
    last_activity_time = time.time()

def on_scroll(x, y, dx, dy):
    global last_activity_time, mouse_activity_data
    mouse_activity_data.append([time.time(), "scroll", x, y])
    last_activity_time = time.time()

def on_press(key):
    global last_activity_time, is_typing, keyboard_activity_data
    try:
        print(f"Key pressed: {key.char}")
        keyboard_activity_data.append([time.time(), "press", key.char])
    except AttributeError:
        print(f"Special key pressed: {key}")
        keyboard_activity_data.append([time.time(), "press", str(key)])
    last_activity_time = time.time()
    is_typing = True

def on_release(key):
    global last_activity_time, is_typing, keyboard_activity_data
    try:
        keyboard_activity_data.append([time.time(), "release", key.char])
    except AttributeError:
        keyboard_activity_data.append([time.time(), "release", str(key)])
    last_activity_time = time.time()
    is_typing = False
    if key == keyboard.Key.esc:
        # Stop listener
        return False

def monitor_activity():
    global last_activity_time, is_typing
    while True:
        current_time = time.time()
        if current_time - last_activity_time > inactivity_threshold:
            if not is_typing:
                print("Unusual activity detected: No recent mouse or keyboard activity.")
        time.sleep(1)  # Check every second

def save_logs():
    global mouse_activity_data, keyboard_activity_data

    with open(mouse_log_file, 'a', newline='') as mouse_file:
        writer = csv.writer(mouse_file)
        writer.writerows(mouse_activity_data)
    
    with open(keyboard_log_file, 'a', newline='') as keyboard_file:
        writer = csv.writer(keyboard_file)
        writer.writerows(keyboard_activity_data)
    
    # Clear the in-memory data after saving
    mouse_activity_data.clear()
    keyboard_activity_data.clear()

    print("Your 5-minute activity has been saved to the CSV files.")
    upload_logs_to_s3(mouse_log_file)
    upload_logs_to_s3(keyboard_log_file)

def upload_logs_to_s3(file_name):
    try:
        with open(file_name, 'rb') as data:
            file_size = 0
            part_number = 1
            multipart_upload = s3_client.create_multipart_upload(Bucket=s3_bucket, Key=file_name)
            while True:
                chunk = data.read(chunk_size)
                if not chunk:
                    break
                s3_client.upload_part(
                    Bucket=s3_bucket,
                    Key=file_name,
                    PartNumber=part_number,
                    UploadId=multipart_upload['UploadId'],
                    Body=chunk
                )
                part_number += 1
                file_size += len(chunk)

            s3_client.complete_multipart_upload(
                Bucket=s3_bucket,
                Key=file_name,
                UploadId=multipart_upload['UploadId'],
                MultipartUpload={
                    'Parts': [{'ETag': 'etag', 'PartNumber': i + 1} for i in range(part_number - 1)]
                }
            )
            print(f"{file_name} uploaded successfully to S3 in {part_number - 1} parts.")

    except FileNotFoundError:
        print(f"{file_name} not found.")
    except NoCredentialsError:
        print("Credentials not available for AWS S3.")

def start_uploading_logs():
    while True:
        time.sleep(upload_interval)
        save_logs()

def start_mouse_and_keyboard_monitoring():
    global last_mouse_position
    last_mouse_position = (0, 0)
    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    mouse_listener.start()
    keyboard_listener.start()

    upload_thread = threading.Thread(target=start_uploading_logs)
    upload_thread.daemon = True
    upload_thread.start()

    monitor_activity()

if __name__ == "__main__":
    start_mouse_and_keyboard_monitoring()
