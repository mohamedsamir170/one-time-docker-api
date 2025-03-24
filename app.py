import os
import json
import sys
import shutil
from flask import Flask, request, jsonify, make_response
from pydantic import BaseModel
import paramiko
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Configuration for remote server
REMOTE_HOST = os.getenv("REMOTE_HOST")
REMOTE_PORT = int(os.getenv("REMOTE_PORT", "22"))
REMOTE_USERNAME = os.getenv("REMOTE_USERNAME")
REMOTE_PASSWORD = os.getenv("REMOTE_PASSWORD")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")

class Container(BaseModel):
    name: str

def delete_api_files():
    """
    Delete the API files after successful container deletion
    """
    try:
        # List of files to delete
        files_to_delete = [
            'app.py',
            'requirements.txt',
            '.env',
            '.env.template',
            'README.md'
        ]
        
        # Delete each file if it exists
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}")
        
        # Delete the directory if it's empty
        if not os.listdir('.'):
            os.rmdir('.')
            
        print("API files deleted successfully")
        # Use os._exit which immediately terminates the process without calling cleanup handlers
        os._exit(0)
    except Exception as e:
        print(f"Error deleting API files: {str(e)}")
        # Still terminate the process
        os._exit(1)

@app.route("/delete-container/", methods=["POST"])
def delete_container():
    """
    Delete a Docker container on the remote server by name and then delete the API.
    """
    try:
        # Get container name from request JSON
        data = request.get_json()
        if not data or 'name' not in data:
            return make_response(jsonify({"error": "Container name is required"}), 400)
        
        container_name = data['name']
        
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to remote server using either password or SSH key
        if SSH_KEY_PATH and os.path.exists(SSH_KEY_PATH):
            private_key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
            ssh.connect(
                hostname=REMOTE_HOST,
                port=REMOTE_PORT,
                username=REMOTE_USERNAME,
                pkey=private_key
            )
        else:
            ssh.connect(
                hostname=REMOTE_HOST,
                port=REMOTE_PORT,
                username=REMOTE_USERNAME,
                password=REMOTE_PASSWORD
            )
        
        # Command to delete container
        command = f"docker rm -f {container_name}"
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Get command output
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        # Close SSH connection
        ssh.close()
        
        # Check if there was an error
        if error:
            return make_response(jsonify({"error": f"Error deleting container: {error}"}), 400)
        
        # Create a response
        response = make_response(jsonify({
            "message": f"Container '{container_name}' successfully deleted",
            "output": output,
            "note": "API will be deleted after this response"
        }))
        
        # Schedule API shutdown using a separate process to ensure the response is sent
        import threading
        def shutdown_api():
            import time
            # Give Flask time to send the response
            time.sleep(2)
            # Then delete API files and exit
            delete_api_files()
            
        # Start the shutdown process in a separate thread
        shutdown_thread = threading.Thread(target=shutdown_api)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return response
    
    except paramiko.AuthenticationException:
        return make_response(jsonify({"error": "Authentication failed"}), 401)
    except paramiko.SSHException as e:
        return make_response(jsonify({"error": f"SSH connection failed: {str(e)}"}), 500)
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