import uvicorn

if __name__ == "__main__":
    print("Starting the Email Assistant service...")
    print("服Once started, please visit http://localhost:8000/static/index.html to use the web interface")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 