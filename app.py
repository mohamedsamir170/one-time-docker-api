import os
import json
import sys
import shutil
import subprocess
from flask import Flask, request, jsonify, make_response
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

class Container(BaseModel):
    name: str

def delete_api_files():
    """
    Delete the API files after successful container deletion
    """
    try:
        # Get the current directory
        current_dir = os.getcwd()
        
        # First delete individual files to ensure we clean up even if rmtree fails
        files_to_delete = [
            'app.py',
            'requirements.txt',
            '.env',
            '.env.template',
            'README.md',
            '.gitignore'
        ]
        
        # Delete each file if it exists
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}")
        
        # Get parent directory to delete the entire folder
        parent_dir = os.path.dirname(current_dir)
        folder_name = os.path.basename(current_dir)
        
        print(f"Attempting to delete entire folder: {current_dir}")
        
        # Change to parent directory so we're not in the directory we're trying to delete
        os.chdir(parent_dir)
        
        # Delete the entire folder with all its contents
        if os.path.exists(os.path.join(parent_dir, folder_name)):
            shutil.rmtree(os.path.join(parent_dir, folder_name))
            print(f"Deleted entire folder: {folder_name}")
            
        print("API files and folder deleted successfully")
        # Use os._exit which immediately terminates the process without calling cleanup handlers
        os._exit(0)
    except Exception as e:
        print(f"Error deleting API files and folder: {str(e)}")
        # Still terminate the process
        os._exit(1)

@app.route("/delete-container/", methods=["POST"])
def delete_container():
    """
    Delete a Docker container on the local server by name and then delete the API.
    """
    try:
        # Get container name from request JSON
        data = request.get_json()
        if not data or 'name' not in data:
            return make_response(jsonify({"error": "Container name is required"}), 400)
        
        container_name = data['name']
        
        # Command to delete container
        result = subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True
        )
        
        # Check if there was an error
        if result.returncode != 0:
            return make_response(jsonify({"error": f"Error deleting container: {result.stderr}"}), 400)
        
        # Create a response
        response = make_response(jsonify({
            "message": f"Container '{container_name}' successfully deleted",
            "output": result.stdout,
            "note": "API will be deleted after this response"
        }))
        
        # Schedule API shutdown using a separate process to ensure the response is sent
        import threading
        def shutdown_api():
            import time
            # Give Flask time to send the response
            time.sleep(2)
            # Then delete API files and exit
            # delete_api_files()
            
        # Start the shutdown process in a separate thread
        shutdown_thread = threading.Thread(target=shutdown_api)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return response
    
    except Exception as e:
        return make_response(jsonify({"error": f"An error occurred: {str(e)}"}), 500)

@app.route("/", methods=["GET"])
def root():
    """
    Root endpoint for API health check.
    """
    return jsonify({"status": "online", "message": "Docker Container Deletion API is running"})

if __name__ == "__main__":
    # Check if this is the main process and not a reloader subprocess
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("Starting Docker Container Deletion API")
    app.run(host='0.0.0.0', port=5000, debug=False) 