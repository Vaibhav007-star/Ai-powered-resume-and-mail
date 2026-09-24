import uvicorn
from backend.config import APP_HOST, APP_PORT

if __name__ == "__main__":
    print(f"Starting AI Job Application Assistant at http://{APP_HOST}:{APP_PORT}")
    uvicorn.run("backend.main:app", host=APP_HOST, port=APP_PORT, reload=True)

