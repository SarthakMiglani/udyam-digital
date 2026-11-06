"""Run the prototype:  python run.py   then open http://localhost:5000 (customer) and /office (back office)."""
import os
from app.main import create_app
if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
