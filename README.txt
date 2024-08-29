Activity Monitor Application

Welcome to the Activity Monitor Application! This program tracks keyboard and mouse activity, takes screenshots, and uploads logs and screenshots to AWS S3. Follow the steps below to get started.

Requirements

1. Python 3.x: Make sure you have Python 3 installed on your computer.
2. Libraries: The program uses several Python libraries. You can install them using pip:
   pip install pynput pillow boto3 requests
3. AWS S3: Ensure you have access to an AWS S3 bucket where the logs and screenshots will be uploaded.

Setup

1. Clone or Download: Download or clone the code repository to your local machine.

2. Configuration:
   - Open main.py and make sure the AWS_BUCKET_NAME constant is set to your S3 bucket name.

Running the Program

1. Run the Program:
   - Open a terminal or command prompt.
   - Navigate to the directory where main.py is located.
   - Run the following command:
     python main.py

2. Using the GUI:
   - A window will open with options to:
     - Take Screenshot: Capture a screenshot immediately.
     - Set Screenshot Interval: Change how often screenshots are taken.
     - Toggle Screenshot Capture: Turn screenshot capturing on or off.
     - Toggle Screenshot Blurring: Enable or disable blurring of screenshots.
     - Exit: Close the application and stop all tracking.

3. Stopping the Program:
   - To stop the program, close the GUI window or press Ctrl+C in the terminal.
   - The application will stop tracking activity, saving, and uploading logs.

Important Files

- app.lock: This file prevents multiple instances of the application from running at the same time.
- keyboard_activity_log.csv: Contains logs of keyboard activity.
- mouse_activity_log.csv: Contains logs of mouse activity.
- screenshots/: Directory where screenshots are saved.

Troubleshooting

- No Internet Connection: The application will retry uploading files if the internet connection is lost.
- Lock File Issue: If you see a message about another instance running, ensure no other instance of the application is active.

