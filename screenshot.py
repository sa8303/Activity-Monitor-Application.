import os
import time
from PIL import ImageGrab, ImageFilter

# Default settings
screenshot_interval = 10
blur_screenshot = True
capture_screenshots = True
screenshot_dir = 'screenshots'

def set_configuration(interval, blur, capture):
    global screenshot_interval, blur_screenshot, capture_screenshots
    screenshot_interval = interval
    blur_screenshot = blur
    capture_screenshots = capture

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory)

def take_screenshot(filename):
    try:
        print("Taking screenshot...")
        image = ImageGrab.grab()
        if blur_screenshot:
            print("Blurring screenshot...")
            image = image.filter(ImageFilter.GaussianBlur(5))
        image.save(filename)
        print(f"Screenshot saved to {filename}")
    except Exception as e:
        print(f"Failed to take screenshot: {e}")

def run_screenshot_module():
    global screenshot_interval, capture_screenshots
    ensure_directory_exists(screenshot_dir)
    try:
        while True:
            if capture_screenshots:
                filename = f"{screenshot_dir}/screenshot_{int(time.time())}.png"
                take_screenshot(filename)
            else:
                print("Screenshot capture is turned off.")
            time.sleep(screenshot_interval)
    except KeyboardInterrupt:
        print("Screenshot module stopped by user.")

if __name__ == "__main__":
    run_screenshot_module()