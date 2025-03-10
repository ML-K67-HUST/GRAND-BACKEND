from config import settings
def run_app_server():
    from uvicorn import run


    run(
        "app:app",
        host="0.0.0.0",
        port=5050,
        # workers=int(settings.WORKERS),
        workers=1,
        # reload=True,
        # reload=os.getenv("RELOADS", "0") == "1"
    )

if __name__ == "__main__":
    run_app_server()