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
    except Exception as e:
        print(f"Error deleting API files: {str(e)}")

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
        
        # Delete API files after successful container deletion
        delete_api_files()
        
        # Return success response
        response = jsonify({
            "message": f"Container '{container_name}' successfully deleted",
            "output": output,
            "note": "API will be deleted after this response"
        })        
    
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
    app.run(host='0.0.0.0', port=5000, debug=True) 