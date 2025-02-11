import sys
import cv2
import asyncio
import websockets
import json
import requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from scanner import Scanner
import pygame
import pyttsx3
import logging
from datetime import datetime
import os


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scanner Settings")
        self.setModal(True)
        self.resize(400, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Server settings
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        self.server_url = QLineEdit()
        self.station_code = QLineEdit()
        server_layout.addRow("Server URL:", self.server_url)
        server_layout.addRow("Station Code:", self.station_code)
        server_group.setLayout(server_layout)

        # Soketi settings
        soketi_group = QGroupBox("Real-time Settings")
        soketi_layout = QFormLayout()
        self.soketi_host = QLineEdit()
        self.soketi_port = QLineEdit()
        self.soketi_key = QLineEdit()
        self.soketi_secret = QLineEdit()
        self.soketi_appid = QLineEdit()
        self.test_soketi = QPushButton("Test Connection")
        self.test_soketi.clicked.connect(self.test_soketi_connection)
        soketi_layout.addRow("Host:", self.soketi_host)
        soketi_layout.addRow("Port:", self.soketi_port)
        soketi_layout.addRow("Key:", self.soketi_key)
        soketi_layout.addRow("Secret:", self.soketi_secret)
        soketi_layout.addRow("App ID:", self.soketi_appid)
        soketi_layout.addRow("", self.test_soketi)
        soketi_group.setLayout(soketi_layout)

        # Camera settings
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QFormLayout()

        self.camera_select = QComboBox()
        self.camera_select.addItems(
            [f"Camera {i}" for i in range(self.count_cameras())]
        )

        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(0, 100)
        self.brightness.setValue(50)

        self.contrast = QSlider(Qt.Horizontal)
        self.contrast.setRange(0, 100)
        self.contrast.setValue(50)

        self.timeout = QSpinBox()
        self.timeout.setRange(1, 60)
        self.timeout.setValue(5)
        self.timeout.setSuffix(" minutes")

        camera_layout.addRow("Camera:", self.camera_select)
        camera_layout.addRow("Brightness:", self.brightness)
        camera_layout.addRow("Contrast:", self.contrast)
        camera_layout.addRow("Auto-stop after:", self.timeout)
        camera_group.setLayout(camera_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel, Qt.Horizontal
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(server_group)
        layout.addWidget(soketi_group)
        layout.addWidget(camera_group)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def count_cameras(self):
        max_cameras = 5
        available = 0
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available += 1
                cap.release()
        return available

    def load_settings(self, config):
        self.server_url.setText(config.get("server_url", ""))
        self.station_code.setText(config.get("station_code", ""))

        soketi = config.get("soketi", {})
        self.soketi_host.setText(soketi.get("host", ""))
        self.soketi_port.setText(str(soketi.get("port", "")))
        self.soketi_key.setText(soketi.get("key", ""))
        self.soketi_secret.setText(soketi.get("secret", ""))
        self.soketi_appid.setText(soketi.get("app_id", ""))

        camera = config.get("camera", {})
        camera_config = config.get("camera", {})
        if isinstance(camera, str):
            camera = {"camera": camera_config}
        self.camera_select.setCurrentText(camera.get("camera", "Camera 0"))
        self.brightness.setValue(camera.get("brightness", 50))
        self.contrast.setValue(camera.get("contrast", 50))
        self.timeout.setValue(config.get("timeout", 5))

    def save_settings(self):
        return {
            "server_url": self.server_url.text(),
            "station_code": self.station_code.text(),
            "soketi": {
                "host": self.soketi_host.text(),
                "port": self.soketi_port.text(),
                "key": self.soketi_key.text(),
                "secret": self.soketi_secret.text(),
                "app_id": self.soketi_appid.text(),
            },
            "camera": {
                "camera": self.camera_select.currentText(),
                "brightness": self.brightness.value(),
                "contrast": self.contrast.value(),
            },
            "timeout": self.timeout.value(),
        }

    def test_soketi_connection(self, event=None):
        try:

            async def test_connection():
                uri = f"ws://{self.soketi_host.text()}:{self.soketi_port.text()}/app/{self.soketi_key.text()}"
                print(f"Connecting to: {uri}")

                try:
                    async with websockets.connect(uri) as ws:
                        auth_data = {
                            "event": "pusher:subscribe",
                            "data": {
                                "auth": f"{self.soketi_key.text()}:{self.soketi_secret.text()}",
                                "channel": "attendance",
                                "app_id": self.soketi_appid.text(),
                            },
                        }
                        print(f"Sending auth: {auth_data}")
                        await ws.send(json.dumps(auth_data))

                        # Wait for auth response
                        auth_response = await ws.recv()
                        print(f"Auth response: {auth_response}")

                        # Send ping
                        ping = {"event": "pusher:ping", "data": {}}
                        print("Sending ping")
                        await ws.send(json.dumps(ping))

                        # Wait for pong
                        response = await ws.recv()
                        print(f"Received: {response}")
                        data = json.loads(response)
                        return (
                            data.get("event") == "pusher:pong"
                            or data.get("event")
                            == "pusher_internal:subscription_succeeded"
                        )

                except Exception as e:
                    print(f"Connection error: {e}")
                    return False

            result = asyncio.run(test_connection())
            if result:
                QMessageBox.information(
                    self, "Success", "Soketi connection successful!"
                )
            else:
                QMessageBox.warning(self, "Error", "Soketi connection failed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {str(e)}")


class ScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scanner = None
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.inactivity_timer = QTimer()
        self.inactivity_timer.timeout.connect(self.handle_inactivity)
        self.last_activity_time = QDateTime.currentDateTime()
        # self.tts_engine = pyttsx3.init()
        pygame.mixer.init()
        self.setup_audio()
        self.load_config()
        self.init_ui()
        self.setup_logging()

    def init_ui(self):
        self.setWindowTitle("TrillED Attendance Scanner")
        self.setGeometry(100, 100, 1024, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Preview area
        preview_group = QGroupBox("Scanner Preview")
        preview_layout = QVBoxLayout()
        self.preview = QLabel()
        self.preview.setMinimumSize(800, 400)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background-color: #f0f0f0;")
        preview_layout.addWidget(self.preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Student info
        info_group = QGroupBox("Student Information")
        info_layout = QHBoxLayout()
        self.student_photo = QLabel()
        self.student_photo.setFixedSize(150, 150)
        info_layout.addWidget(self.student_photo)
        self.student_info = QLabel("No scan yet")
        self.student_info.setTextFormat(Qt.RichText)
        info_layout.addWidget(self.student_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Control buttons
        control_group = QHBoxLayout()
        self.start_button = QPushButton("Start Scanner")
        self.start_button.clicked.connect(self.start_scanner)
        self.stop_button = QPushButton("Stop Scanner")
        self.stop_button.clicked.connect(self.stop_scanner)
        self.stop_button.setEnabled(False)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_settings)

        control_group.addWidget(self.start_button)
        control_group.addWidget(self.stop_button)
        control_group.addWidget(self.settings_button)
        layout.addLayout(control_group)

        self.statusBar().showMessage("Ready")

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = self.get_default_config()

    def get_default_config(self):
        return {
            "server_url": "",
            "station_code": "",
            "soketi": {
                "host": "localhost",
                "port": "6001",
                "key": "",
                "secret": "",
                "app_id": "",
            },
            "camera": {"camera": "Camera 0", "brightness": 50, "contrast": 50},
            "timeout": 5,
        }

    def save_config(self):
        with open("config.json", "w") as f:
            json.dump(self.config, f)

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.load_settings(self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.save_settings()
            self.save_config()
            self.apply_settings()

    def apply_settings(self):
        if self.scanner:
            self.scanner.update_config(self.config)
        self.inactivity_timer.setInterval(self.config["timeout"] * 60 * 1000)

    def setup_audio(self):
        self.use_tts = True
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty("rate", 150)
            self.tts_engine.setProperty("volume", 1.0)
            voices = self.tts_engine.getProperty("voices")
            if len(voices) > 1:
                self.tts_engine.setProperty("voice", voices[1].id)
        except:
            self.use_tts = False
            print("TTS not available, falling back to audio files")

    def setup_logging(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(
            log_dir, f"scanner_{datetime.now().strftime('%Y%m%d')}.log"
        )
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # Keep only last 7 days of logs
        self.cleanup_old_logs(log_dir, days=7)

    def cleanup_old_logs(self, log_dir, days):
        current_time = datetime.now()
        for file in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file)
            if (
                current_time - datetime.fromtimestamp(os.path.getctime(file_path))
            ).days > days:
                os.remove(file_path)

    def setup_logging(self):
        if getattr(sys, "frozen", False):
            # Running as compiled exe
            log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
        else:
            # Running as script
            log_dir = "logs"

    def handle_exception(exc_type, exc_value, exc_traceback):
        logging.error(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
        )
        sys.exit(1)

    sys.excepthook = handle_exception

    def start_scanner(self):
        camera_config = self.config.get("camera", {})
        camera_id = int(camera_config.get("camera", "Camera 0").split()[-1])

        # camera_id = int(self.config["camera"]["camera"].split()[-1])
        self.camera = cv2.VideoCapture(camera_id)

        if not self.camera.isOpened():
            QMessageBox.critical(self, "Error", "Could not open camera")
            return

        self.scanner = Scanner(self.config["server_url"], self.config["station_code"])
        self.timer.start(30)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("Scanner running")
        self.last_activity_time = QDateTime.currentDateTime()

    def stop_scanner(self):
        self.timer.stop()
        if self.camera:
            self.camera.release()
        self.clear_preview()
        self.reset_display()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("Scanner stopped")

    def reset_display(self):
        self.student_info.setText("No scan yet")
        self.set_default_photo()

    def clear_preview(self):
        empty_image = QImage(800, 400, QImage.Format_RGB888)
        empty_image.fill(QColor("#f0f0f0"))
        self.preview.setPixmap(QPixmap.fromImage(empty_image))

    def handle_inactivity(self):
        if self.camera and (
            QDateTime.currentDateTime().secsTo(self.last_activity_time) > 300
        ):
            self.stop_scanner()
            self.statusBar().showMessage("Scanner stopped due to inactivity")

    def update_frame(self):
        self.last_activity_time = QDateTime.currentDateTime()
        ret, frame = self.camera.read()
        if not ret:
            return

        frame = cv2.convertScaleAbs(
            frame,
            alpha=self.config["camera"]["contrast"] / 50.0,
            beta=self.config["camera"]["brightness"],
        )

        if self.scanner:
            scan_data, frame = self.scanner.decode_frame(frame)
            if scan_data:
                self.handle_scan(scan_data)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_image = image.scaled(800, 400, Qt.KeepAspectRatio)
        self.preview.setPixmap(QPixmap.fromImage(scaled_image))

    def set_status_message(self, message, status_type="info"):
        colors = {"success": "#28a745", "error": "#dc3545", "info": "#17a2b8"}
        style = f"QStatusBar {{ color: {colors[status_type]}; font-weight: bold; }}"
        self.statusBar().setStyleSheet(style)
        self.statusBar().showMessage(message)

    def handle_scan(self, scan_data):
        result = self.scanner.process_scan(scan_data)

        if result["status"] == "success":
            self.set_status_message("Scan successful", "success")
            self.speak_message("Successfully scanned")
            self.update_student_info(result["data"])
        else:
            message = result.get("message", "Unknown error")
            self.set_status_message(f"Error: {message}", "error")
            self.speak_message(message)

    def speak_message(self, message):
        if self.use_tts:
            try:
                threading.Thread(target=self._speak_async, args=(message,)).start()
            except:
                self.play_status_sound(message)
        else:
            self.play_status_sound(message)

    def _speak_async(self, message):
        self.tts_engine.say(message)
        self.tts_engine.runAndWait()

    def play_status_sound(self, message):
        sound_map = {
            "Successfully scanned": "successfully-scanned.mp3",
            "Please wait before scanning out": "pleasewait.mp3",
            "Invalid scan": "invalid-scan.mp3",
            "Attendance already completed for today": "attendance-completed.mp3",
            "No active schedule for current time": "no-active-schedule.mp3",
            "No schedule found for today": "no-schedule-found.mp3",
            "Invalid station code": "invalid-station.mp3",
            # Add more mappings
        }
        sound_file = sound_map.get(message, "success.mp3")
        pygame.mixer.music.load(f"sounds/{sound_file}")
        pygame.mixer.music.play()

    def update_student_info(self, data):
        status_style = {
            "P": "color: green; font-weight: bold; font-size: 16pt;",
            "L": "color: orange; font-weight: bold; font-size: 16pt;",
            "A": "color: red; font-weight: bold; font-size: 16pt;",
        }

        info_text = f"""
        <div style='font-size: 14pt;'>
            <p><b>Name:</b> {data['student_name']}</p>
            <p><b>Class:</b> {data['class']}</p>
            <p><b>Time:</b> {data['scan_time']}</p>
            <p><b>Status:</b> <span style='{status_style.get(data["attendance_status"], "")}'>
                {data["attendance_status"]}</span></p>
            <p><b>Type:</b> {data['scan_type']}</p>
        </div>
        """
        self.student_info.setText(info_text)
        self.load_student_photo(data.get("photo_url"))

    def load_student_photo(self, photo_url):
        if not photo_url:
            self.set_default_photo()
            return

        try:
            response = requests.get(photo_url, timeout=5)
            image = QImage()
            success = image.loadFromData(response.content)

            if not success:
                self.set_default_photo()
                return

            scaled_image = image.scaled(
                150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.student_photo.setPixmap(QPixmap.fromImage(scaled_image))
        except Exception as e:
            print(f"Error loading photo: {e}")
            self.set_default_photo()

    def set_default_photo(self):
        default_image = QImage(150, 150, QImage.Format_RGB888)
        default_image.fill(Qt.lightGray)
        self.student_photo.setPixmap(QPixmap.fromImage(default_image))

    def play_success_sound(self):
        pygame.mixer.music.load("sounds/thank-you.mp3")
        pygame.mixer.music.play()

    def play_error_sound(self):
        pygame.mixer.music.load("sounds/error-occured.mp3")
        pygame.mixer.music.play()

    def closeEvent(self, event):
        self.stop_scanner()
        self.save_config()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = ScannerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
