# Docker Container Deletion API

A Flask-based API to delete Docker containers on a remote server.

## Features

- REST API for deleting Docker containers by name
- Authentication to remote server via password or SSH key
- Error handling for common issues

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on the `.env.template`:
   ```
   cp .env.template .env
   ```
4. Edit the `.env` file and provide your remote server details:
   - `REMOTE_HOST`: IP address or hostname of the remote server
   - `REMOTE_PORT`: SSH port (usually 22)
   - `REMOTE_USERNAME`: SSH username
   - `REMOTE_PASSWORD`: SSH password
   - `SSH_KEY_PATH`: (Optional) Path to SSH private key file

## Running the API

Start the API server in development mode:

```bash
python app.py
```

Or in production with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The API will be available at `http://localhost:5000`

## Using the API

### Delete a container

**Endpoint**: `POST /delete-container/`

**Request body**:
```json
{
  "name": "container_name"
}
```

**Example using curl**:
```bash
curl -X POST "http://localhost:5000/delete-container/" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-container"}'
```

## Security Notes

- The API currently has no authentication. If deployed in production, add API authentication.
- Consider using SSH key authentication instead of password authentication for better security. 