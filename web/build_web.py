"""
Pygbag build script for Declare.
Run: python build_web.py
Then serve the build/ directory with any web server.
"""
import subprocess
import sys
import os

def main():
    # Run from project root so pygbag finds main.py and assets/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("Building Declare for Web...")
    print("This may take several minutes on first run.")

    try:
        subprocess.run([
            sys.executable, "-m", "pygbag",
            "--build", "--title", "Declare",
            "--ume_block", "0",
            "--width", "2560", "--height", "1440",
            "--template", "web/declare.tmpl",
            "."
        ])
        print("\nBuild complete! The 'build/' directory contains the web app.")
        print("To test locally, serve the build directory:")
        print("  python -m http.server 8000 -d build/web")
        print("Then open http://localhost:8000 in your browser.")
    except Exception as e:
        print(f"Build failed: {e}")
        print("Make sure pygbag is installed: pip install pygbag")

if __name__ == "__main__":
    main()