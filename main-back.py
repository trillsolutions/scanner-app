import sys
import cv2
import json
import requests
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from scanner import Scanner
import pygame


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
        pygame.mixer.init()
        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("Attendance Scanner")
        self.setGeometry(100, 100, 1024, 600)

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top section with settings and controls side by side
        top_container = QHBoxLayout()

        # Settings group (left)
        settings_group = QGroupBox("Settings")
        settings_layout = QFormLayout()
        settings_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.server_url = QLineEdit()
        self.station_code = QLineEdit()
        self.camera_select = QComboBox()
        self.camera_select.addItems(
            [f"Camera {i}" for i in range(self.count_cameras())]
        )

        settings_layout.addRow("Server URL:", self.server_url)
        settings_layout.addRow("Station Code:", self.station_code)
        settings_layout.addRow("Camera:", self.camera_select)
        settings_group.setLayout(settings_layout)

        # Camera controls group (right)
        controls_group = QGroupBox("Camera Controls")
        controls_layout = QFormLayout()

        self.brightness = QSlider(Qt.Horizontal)
        self.brightness.setRange(0, 100)
        self.brightness.setValue(50)

        self.contrast = QSlider(Qt.Horizontal)
        self.contrast.setRange(0, 100)
        self.contrast.setValue(50)

        controls_layout.addRow("Brightness:", self.brightness)
        controls_layout.addRow("Contrast:", self.contrast)
        controls_group.setLayout(controls_layout)

        # Add both groups to top container
        top_container.addWidget(settings_group)
        top_container.addWidget(controls_group)
        main_layout.addLayout(top_container)

        # Preview area
        preview_group = QGroupBox("Scanner Preview")
        preview_layout = QVBoxLayout()
        self.preview = QLabel()
        self.preview.setMinimumSize(800, 250)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background-color: #f0f0f0;")
        preview_layout.addWidget(self.preview)
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # Student info
        info_group = QGroupBox("Student Information")
        info_layout = QHBoxLayout()

        self.student_photo = QLabel()
        self.student_photo.setFixedSize(150, 150)
        info_layout.addWidget(self.student_photo)

        self.student_info = QLabel("No scan yet")
        info_layout.addWidget(self.student_info)

        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Scanner")
        self.start_button.clicked.connect(self.start_scanner)
        self.stop_button = QPushButton("Stop Scanner")
        self.stop_button.clicked.connect(self.stop_scanner)
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        # Initialize inactivity timer (5 minutes)
        self.inactivity_timer.start(300000)

    def clear_preview(self):
        empty_image = QImage(800, 600, QImage.Format_RGB888)
        empty_image.fill(QColor("#f0f0f0"))
        self.preview.setPixmap(QPixmap.fromImage(empty_image))

    def handle_inactivity(self):
        if self.camera and (
            QDateTime.currentDateTime().secsTo(self.last_activity_time) > 300
        ):
            self.stop_scanner()
            self.statusBar().showMessage("Scanner stopped due to inactivity")

    def count_cameras(self):
        max_cameras = 5
        available = 0
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available += 1
                cap.release()
        return available

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                self.server_url.setText(config.get("server_url", ""))
                self.station_code.setText(config.get("station_code", ""))
                self.camera_select.setCurrentText(config.get("camera", "Camera 0"))
        except FileNotFoundError:
            pass

    def save_config(self):
        config = {
            "server_url": self.server_url.text(),
            "station_code": self.station_code.text(),
            "camera": self.camera_select.currentText(),
        }
        with open("config.json", "w") as f:
            json.dump(config, f)

    def start_scanner(self):
        camera_id = int(self.camera_select.currentText().split()[-1])
        self.camera = cv2.VideoCapture(camera_id)

        if not self.camera.isOpened():
            QMessageBox.critical(self, "Error", "Could not open camera")
            return

        self.scanner = Scanner(self.server_url.text(), self.station_code.text())
        self.timer.start(30)  # 30ms = ~33 fps

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar().showMessage("Scanner running")
        self.last_activity_time = QDateTime.currentDateTime()

    def stop_scanner(self):
        self.timer.stop()
        if self.camera:
            self.camera.release()
        self.clear_preview()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("Scanner stopped")

    def update_frame(self):
        self.last_activity_time = QDateTime.currentDateTime()
        ret, frame = self.camera.read()
        if not ret:
            return

        frame = cv2.convertScaleAbs(
            frame, alpha=self.contrast.value() / 50.0, beta=self.brightness.value()
        )

        if self.scanner:
            scan_data, frame = self.scanner.decode_frame(frame)
            if scan_data:
                self.handle_scan(scan_data)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        scaled_image = image.scaled(800, 600, Qt.KeepAspectRatio)
        self.preview.setPixmap(QPixmap.fromImage(scaled_image))

    def handle_scan(self, scan_data):
        result = self.scanner.process_scan(scan_data)

        if result["status"] == "success":
            self.play_success_sound()
            self.update_student_info(result["data"])
        else:
            self.play_error_sound()
            self.statusBar().showMessage(
                f"Error: {result.get('message', 'Unknown error')}"
            )

    def update_student_info(self, data):

        # Style for larger text
        status_style = {
            "P": "color: green; font-weight: bold; font-size: 14pt;",
            "L": "color: orange; font-weight: bold; font-size: 14pt;",
            "A": "color: red; font-weight: bold; font-size: 14pt;",
        }

        info_text = f"""
        <div style='font-size: 12pt;'>
        <p><b>Name:</b> {data['student_name']}</p>
        <p><b>Class:</b> {data['class']}</p>
        <p><b>Time:</b> {data['scan_time']}</p>
        <p><b>Status:</b> <span style='{status_style.get(data["attendance_status"], "")}'>
            {data["attendance_status"]}</span></p>
        <p><b>Type:</b> {data['scan_type']}</p>
        </div>
        """
        self.student_info.setText(info_text)
        self.student_info.setTextFormat(Qt.RichText)

        self.load_student_photo(data.get("photo_url"))
        # self.load_student_photo(
        #    f"{self.server_url}/uploads/images/student/" + (data.get("photo") or "")
        # )

    def load_student_photo(self, photo_url):
        if not photo_url:
            self.set_default_photo()
            return

        try:
            print(f"Loading photo from: {photo_url}")  # Debug URL
            response = requests.get(
                photo_url, verify=False
            )  # Add verify=False for local testing
            print(f"Response status: {response.status_code}")  # Debug response
            print(f"Content length: {len(response.content)}")  # Debug content

            # Try direct image loading
            image = QImage()
            success = image.loadFromData(response.content)
            print(f"Image load success: {success}")  # Debug image loading

            if not success:
                # Set default image
                image = QImage(150, 150, QImage.Format_RGB888)
                image.fill(Qt.gray)

            scaled_image = image.scaled(
                150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.student_photo.setPixmap(QPixmap.fromImage(scaled_image))
        except Exception as e:
            print(f"Error loading photo: {e}")
            traceback.print_exc()  # Full stack trace

    def set_default_photo(self):
        default_image = QImage(150, 150, QImage.Format_RGB888)
        default_image.fill(Qt.lightGray)
        self.student_photo.setPixmap(QPixmap.fromImage(default_image))

    def play_success_sound(self):
        pygame.mixer.music.load("sounds/success.mp3")
        pygame.mixer.music.play()

    def play_error_sound(self):
        pygame.mixer.music.load("sounds/error.mp3")
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
