import numpy as np
import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
import requests
import json
import time
import logging
import ssl
import hashlib
import hmac
import websockets
import asyncio


class Scanner:
    def __init__(self, server_url, station_code):
        self.server_url = server_url
        self.station_code = station_code
        self.last_scan = 0
        self.scan_cooldown = 2
        self.soketi_config = {}
        self.ws = None

    async def init_websocket(self):
        soketi = self.soketi_config
        protocol = "wss" if soketi.get("use_ssl", True) else "ws"
        ws_url = f"{protocol}://{soketi.get('host')}:{soketi.get('port')}/app/{soketi.get('key')}?protocol=7&client=py&version=4.5.0"

        try:
            if soketi.get("use_ssl", True):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                self.ws = await websockets.connect(
                    ws_url, ssl=ssl_context, close_timeout=5, ping_timeout=5
                )
            else:
                self.ws = await websockets.connect(
                    ws_url, close_timeout=5, ping_timeout=5
                )

            socket_id = await self.get_socket_id()
            auth_signature = self.get_auth_signature(socket_id, "attendance")
            await self.subscribe(auth_signature)

        except Exception as e:
            logging.error(f"WebSocket connection failed: {e}")
            print(f"Connection error: {e}")

    async def get_socket_id(self):
        message = await self.ws.recv()
        data = json.loads(message)
        if data.get("event") == "pusher:connection_established":
            return json.loads(data["data"])["socket_id"]

    def get_auth_signature(self, socket_id, channel):
        secret = self.soketi_config.get("secret", "")
        string_to_sign = f"{socket_id}:{channel}"
        signature = hmac.new(
            secret.encode(), string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        return f"{self.soketi_config.get('key')}:{signature}"

    async def subscribe(self, auth_signature):
        subscribe_payload = {
            "event": "pusher:subscribe",
            "data": {"channel": "attendance", "auth": auth_signature},
        }
        await self.ws.send(json.dumps(subscribe_payload))

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
            # codes = decode(gray)
            codes = decode(gray, symbols=[ZBarSymbol.QRCODE])  # Restrict to QR only
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

    # async def connect_websocket(self):
    #    soketi = self.soketi_config
    #    ws_url = f"ws://{soketi.get('host', 'localhost')}:{soketi.get('port', '6001')}/app/{soketi.get('key', '')}"

    #    self.ws = await websockets.connect(ws_url)

    #   await self.ws.send(json.dumps({"event": "subscribe", "channel": "attendance"}))
