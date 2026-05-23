#!/usr/bin/env python3
"""
Simple Python client for Daedalus REST API + WebSocket.
"""

import requests
import json
from typing import Optional, Dict, List

class DaedalusClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base = base_url.rstrip("/")

    def list_algorithms(self) -> Dict:
        return requests.get(f"{self.base}/api/algorithms").json()

    def generate_maze(self, generator_id: str, rows: int = 30, cols: int = 30, seed: Optional[int] = None) -> Dict:
        payload = {"generatorId": generator_id, "rows": rows, "cols": cols}
        if seed:
            payload["seed"] = seed
        return requests.post(f"{self.base}/api/maze/generate", json=payload).json()

    def get_maze(self, maze_id: str) -> Dict:
        return requests.get(f"{self.base}/api/maze/{maze_id}").json()

    def solve_maze(self, maze_id: str, solver_id: str) -> Dict:
        return requests.post(f"{self.base}/api/maze/{maze_id}/solve/{solver_id}").json()

    def open_session(self, maze_id: str, player: str = "python-bot") -> Dict:
        return requests.post(f"{self.base}/api/maze/{maze_id}/session", params={"player": player}).json()

    def move(self, session_id: str, to_row: int, to_col: int) -> bool:
        return requests.post(f"{self.base}/api/session/{session_id}/move", 
                           json={"to": {"row": to_row, "col": to_col}}).json()

    def get_leaderboard(self, n: int = 10) -> List[Dict]:
        return requests.get(f"{self.base}/api/leaderboard", params={"n": n}).json()

    def list_plugins(self) -> List[Dict]:
        return requests.get(f"{self.base}/api/plugins").json()

if __name__ == "__main__":
    client = DaedalusClient()
    print("Daedalus Python Client ready.")
    print("Generators:", [g["id"] for g in client.list_algorithms()["generators"][:5]])