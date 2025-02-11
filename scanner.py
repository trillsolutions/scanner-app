import numpy as np
import cv2
from pyzbar.pyzbar import decode
import requests
import json
import time
from datetime import datetime
import websockets


class Scanner:
    def __init__(self, server_url, station_code):
        self.server_url = server_url
        self.station_code = station_code
        self.last_scan = 0
        self.scan_cooldown = 2  # seconds
        self.soketi_config = {}

    def update_config(self, config):
        self.server_url = config.get("server_url")
        self.station_code = config.get("station_code")
        self.soketi_config = config.get("soketi", {})

    def draw_boundary(self, frame, points):
        if len(points) > 4:
            hull = cv2.convexHull(
                np.array([point for point in points], dtype=np.float32)
            )
            points = hull

        if len(points) == 4:
            cv2.polylines(frame, [np.array(points, np.int32)], True, (0, 255, 0), 2)

    def decode_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        try:
            codes = decode(gray)
            if codes:
                for code in codes:
                    data = code.data.decode("utf-8")
                    # Add format validation here
                    if not self.is_valid_barcode_format(data):
                        continue

                    if self.is_valid_scan():
                        self.draw_boundary(frame, code.polygon)
                        return data, frame

            return None, frame

        except Exception as e:
            # print(f"Error decoding frame: {e}")
            logging.error(f"Scan error: {str(e)}", exc_info=True)
            return None, frame

    def is_valid_barcode_format(self, data):
        return len(data) >= 4 and len(data) <= 10

    def is_valid_scan(self):
        current_time = time.time()
        if current_time - self.last_scan < self.scan_cooldown:
            return False
        self.last_scan = current_time
        return True

    def process_scan(self, scan_data):
        try:
            response = requests.post(
                f"{self.server_url}/api/scan",
                data={"scan_data": scan_data, "station_code": self.station_code},
            )

            # print(f"Response: {response.text}")  # Debug
            # print(f"Status code: {response.status_code}")  # Debug
            # print(f"Server: {self.server_url}")  # Debug
            # print(f"Station code: {self.station_code}")  # Debug
            # print(f"Scan data: {scan_data}")  # Debug
            return response.json()

        except Exception as e:
            # print(f"Full error: {str(e)}")
            return {"status": "error", "message": str(e)}

    def enhance_frame(self, frame, brightness=1.0, contrast=1.0):
        """Enhance frame quality for better scanning"""
        # Convert to float for calculations
        frame = frame.astype(float)

        # Apply brightness
        frame = frame * brightness

        # Apply contrast
        frame = frame * contrast

        # Clip values to valid range
        frame = np.clip(frame, 0, 255)

        # Convert back to uint8
        return frame.astype(np.uint8)

    async def connect_websocket(self):
        soketi = self.soketi_config
        ws_url = f"ws://{soketi.get('host', 'localhost')}:{soketi.get('port', '6001')}/app/{soketi.get('key', '')}"

        self.ws = await websockets.connect(ws_url)

        await self.ws.send(json.dumps({"event": "subscribe", "channel": "attendance"}))
