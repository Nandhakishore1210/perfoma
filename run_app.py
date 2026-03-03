import os
import sys
import multiprocessing

# Add backend directory to path so app can be imported
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    # Try current folder for backend first, then 'internal'
    paths_to_check = [
        os.path.join(base_path, "backend"),
        os.path.join(base_path, "internal"),
        base_path
    ]
    backend_dir = base_path
    for p in paths_to_check:
        if os.path.exists(os.path.join(p, "app")):
            backend_dir = p
            break
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(current_dir, "backend")

sys.path.append(backend_dir)

if __name__ == "__main__":
    # Required for freeze support on Windows
    multiprocessing.freeze_support()
    
    import uvicorn
    from app.main import app
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")

    # Start browser after a short delay
    Timer(2.0, open_browser).start()

    # Run the server
    print("Starting Perfoma System...")
    print("The application will open in your browser automatically.")
    print("URL: http://127.0.0.1:8000")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
