"""Main launcher for AI Crime Scene Detection System."""

import sys
from app import create_app

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    print(f"[*] Forensic AI Command Center launching on http://127.0.0.1:{port}")
    app = create_app()
    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
else:
    app = create_app()
