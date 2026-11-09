"""Arranca MatchPoint:  python run.py   (luego abre http://127.0.0.1:5000)"""
from app import create_app

if __name__ == "__main__":
    create_app().run(debug=True)
