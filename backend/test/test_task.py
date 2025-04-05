import sys
import os

# add the current directory to the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tasks.tasks import process_document

if __name__ == "__main__":
    # Send a test task
    task = process_document.delay(
        document_id="00000000-0000-0000-0000-000000000000",
        file_path="test_file.pdf"
    )
    print(f"Task sent with ID: {task.id}")
    print("Check Flower (http://localhost:5566) to see the task status") 