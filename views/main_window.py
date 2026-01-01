# views/main_window.py - MINIMAL UPDATE FOR NEW MODEL
import sys
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QGroupBox, QFrame, QProgressBar, QTextEdit,
    QSplitter, QSizePolicy, QApplication, QComboBox,
    QAction, QMenu, QStatusBar, QDialog, QSlider  # Added QDialog and QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor

from models.ai_model import LeafDiseaseModel
from models.data_models import DiagnosisResult, DiseaseCategory
from utils.image_utils import load_image_to_pixmap, is_valid_image
from config import APP_NAME, APP_VERSION, SUPPORTED_EXTENSIONS, DEFAULT_CONFIDENCE_THRESHOLD
from models.database import db_manager
from views.history_window import HistoryWindow

class PredictionThread(QThread):
    """Thread for running model predictions without freezing GUI"""
    prediction_finished = pyqtSignal(DiagnosisResult)
    prediction_error = pyqtSignal(str)
    
    def __init__(self, model, image_path):
        super().__init__()
        self.model = model
        self.image_path = image_path
    
    def run(self):
        try:
            result = self.model.predict(self.image_path)
            self.prediction_finished.emit(result)
        except Exception as e:
            self.prediction_error.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.current_image_path = None
        self.prediction_thread = None
        self.last_result = None
        self.settings = QSettings("LeafCheckAI", "App")
        
        self.init_ui()
        self.load_model()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(100, 100, 1200, 700)
        
        # Create menu bar first
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Image upload and preview
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel - Results and information
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Set styles
        self.set_styles()
        
        # Set status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Scan", self)
        new_action.triggered.connect(self.new_scan)
        file_menu.addAction(new_action)
        
        save_action = QAction("Save Results", self)
        save_action.triggered.connect(self.save_results)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # History menu
        history_menu = menubar.addMenu("History")
        
        view_history_action = QAction("View History", self)
        view_history_action.triggered.connect(self.open_history)
        history_menu.addAction(view_history_action)
        
        stats_action = QAction("Statistics", self)
        stats_action.triggered.connect(self.show_statistics)
        history_menu.addAction(stats_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        model_info_action = QAction("Model Information", self)
        model_info_action.triggered.connect(self.show_model_info)
        tools_menu.addAction(model_info_action)
        
        # Add threshold adjustment to Tools menu
        threshold_action = QAction("Adjust Confidence Threshold", self)
        threshold_action.triggered.connect(self.adjust_threshold)
        tools_menu.addAction(threshold_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_left_panel(self):
        """Create left panel with image upload and preview"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Upload section
        upload_group = QGroupBox("Image Upload")
        upload_layout = QVBoxLayout()
        
        # Upload button
        self.upload_btn = QPushButton("Select Image")
        self.upload_btn.clicked.connect(self.select_image)
        self.upload_btn.setMinimumHeight(40)
        upload_layout.addWidget(self.upload_btn)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(300)
        self.image_label.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.image_label.setText("No image selected")
        self.image_label.setStyleSheet("background-color: #f0f0f0;")
        upload_layout.addWidget(self.image_label)
        
        # Image info
        self.image_info_label = QLabel("")
        self.image_info_label.setWordWrap(True)
        upload_layout.addWidget(self.image_info_label)
        
        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)
        
        # Add simple threshold indicator
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Min Confidence:"))
        self.threshold_label = QLabel(f"{DEFAULT_CONFIDENCE_THRESHOLD:.0%}")
        threshold_layout.addWidget(self.threshold_label)
        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)
        
        # Analyze button
        self.analyze_btn = QPushButton("Analyze Leaf")
        self.analyze_btn.clicked.connect(self.analyze_image)
        self.analyze_btn.setMinimumHeight(50)
        self.analyze_btn.setEnabled(False)
        layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Save Results button
        self.save_btn = QPushButton("Save to History")
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """Create right panel with results and disease info"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Results section
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        # Disease name
        self.disease_label = QLabel("No analysis yet")
        self.disease_label.setAlignment(Qt.AlignCenter)
        self.disease_label.setFont(QFont("Arial", 16, QFont.Bold))
        results_layout.addWidget(self.disease_label)
        
        # Confidence
        self.confidence_label = QLabel("")
        self.confidence_label.setAlignment(Qt.AlignCenter)
        self.confidence_label.setFont(QFont("Arial", 12))
        results_layout.addWidget(self.confidence_label)
        
        # Confidence bar
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setTextVisible(True)
        results_layout.addWidget(self.confidence_bar)
        
        # Status indicator
        self.status_indicator = QLabel("")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setMinimumHeight(30)
        results_layout.addWidget(self.status_indicator)
        
        # Inference time
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.time_label)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Disease information section
        info_group = QGroupBox("Disease Information")
        info_layout = QVBoxLayout()
        
        # Description
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        info_layout.addWidget(self.description_label)
        
        # Symptoms
        self.symptoms_label = QLabel("")
        self.symptoms_label.setWordWrap(True)
        info_layout.addWidget(self.symptoms_label)
        
        # Treatment
        self.treatment_label = QLabel("")
        self.treatment_label.setWordWrap(True)
        info_layout.addWidget(self.treatment_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Other predictions
        other_group = QGroupBox("Other Possible Diseases")
        other_layout = QVBoxLayout()
        
        self.other_predictions_label = QLabel("")
        self.other_predictions_label.setWordWrap(True)
        other_layout.addWidget(self.other_predictions_label)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)
        
        layout.addStretch()
        return panel
    
    def set_styles(self):
        """Set widget styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLabel {
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
    
    def load_model(self):
        """Load the ML model"""
        try:
            # Load saved threshold or use default
            saved_threshold = self.settings.value("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD, type=float)
            self.model = LeafDiseaseModel(threshold=saved_threshold)
            
            # Update threshold label
            self.threshold_label.setText(f"{saved_threshold:.0%}")
            
            # Update status
            model_info = self.model.get_model_info()
            self.statusBar().showMessage(
                f"Model: {model_info['architecture']} | "
                f"Device: {model_info['device']} | "
                f"Threshold: {model_info['confidence_threshold']:.0%}", 
                5000
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Model Load Error",
                f"Failed to load model:\n{str(e)}"
            )
            sys.exit(1)
    
    def select_image(self):
        """Open file dialog to select image"""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter(
            f"Images ({' '.join(['*' + ext for ext in SUPPORTED_EXTENSIONS])})"
        )
        
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            
            if is_valid_image(file_path):
                self.current_image_path = file_path
                self.display_image(file_path)
                self.analyze_btn.setEnabled(True)
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Image",
                    "Please select a valid image file."
                )
    
    def display_image(self, image_path: str):
        """Display selected image"""
        pixmap = load_image_to_pixmap(image_path)
        
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
            
            # Update image info
            from PIL import Image
            with Image.open(image_path) as img:
                info = f"File: {Path(image_path).name}\n"
                info += f"Size: {img.size[0]} × {img.size[1]} px\n"
                info += f"Format: {img.format or 'Unknown'}"
                self.image_info_label.setText(info)
        else:
            self.image_label.setText("Failed to load image")
            self.image_info_label.setText("")
    
    def analyze_image(self):
        """Analyze the selected image"""
        if not self.current_image_path or not self.model:
            return
        
        # Disable buttons during analysis
        self.analyze_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear previous results
        self.clear_results()
        
        # Create and start prediction thread
        self.prediction_thread = PredictionThread(self.model, self.current_image_path)
        self.prediction_thread.prediction_finished.connect(self.on_prediction_complete)
        self.prediction_thread.prediction_error.connect(self.on_prediction_error)
        self.prediction_thread.start()
    
    def clear_results(self):
        """Clear previous analysis results"""
        self.disease_label.setText("Analyzing...")
        self.confidence_label.setText("")
        self.confidence_bar.setValue(0)
        self.status_indicator.setText("")
        self.time_label.setText("")
        self.description_label.setText("")
        self.symptoms_label.setText("")
        self.treatment_label.setText("")
        self.other_predictions_label.setText("")
    
    def on_prediction_complete(self, result: DiagnosisResult):
        """Handle completed prediction"""
        # Store the result
        self.last_result = result
        
        # Re-enable buttons
        self.analyze_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Update results display
        self.update_results_display(result)
    
    def on_prediction_error(self, error_message: str):
        """Handle prediction error"""
        # Re-enable buttons
        self.analyze_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Show error
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"Failed to analyze image:\n{error_message}"
        )
        
        self.disease_label.setText("Analysis Failed")
        self.status_indicator.setText("Error")
        self.status_indicator.setStyleSheet("background-color: #ffcccc; color: #cc0000;")
    
    def update_results_display(self, result: DiagnosisResult):
        """Update GUI with prediction results"""
        disease = result.disease
        
        # Disease name
        self.disease_label.setText(disease.display_name)
        
        # Confidence
        confidence_percent = int(result.confidence * 100)
        self.confidence_label.setText(f"Confidence: {confidence_percent}%")
        self.confidence_bar.setValue(confidence_percent)
        
        # Set confidence bar color based on confidence
        if confidence_percent >= 80:
            color = "#4CAF50"  # Green
        elif confidence_percent >= 60:
            color = "#FF9800"  # Orange
        elif confidence_percent >= 40:
            color = "#F44336"  # Red
        else:
            color = "#9E9E9E"  # Gray for low confidence
        
        self.confidence_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """)
        
        # Status indicator
        if result.is_rejected:
            self.status_indicator.setText("REJECTED - Low Confidence")
            self.status_indicator.setStyleSheet(
                "background-color: #f5f5f5; color: #757575; font-weight: bold;"
            )
        elif result.is_healthy():
            self.status_indicator.setText("HEALTHY")
            self.status_indicator.setStyleSheet(
                "background-color: #4CAF50; color: white; font-weight: bold;"
            )
        else:
            self.status_indicator.setText("DISEASE DETECTED")
            self.status_indicator.setStyleSheet(
                "background-color: #F44336; color: white; font-weight: bold;"
            )
        
        # Inference time
        self.time_label.setText(f"Analysis time: {result.inference_time:.3f} seconds")
        
        # Disease information
        self.description_label.setText(
            f"<b>Description:</b><br>{disease.description}"
        )
        
        if disease.symptoms:
            symptoms_text = "<b>Symptoms:</b><br>" + "<br>• ".join([""] + disease.symptoms)
            self.symptoms_label.setText(symptoms_text)
        
        if disease.treatment:
            treatment_text = "<b>Treatment:</b><br>" + "<br>• ".join([""] + disease.treatment)
            self.treatment_label.setText(treatment_text)
        
        # Other predictions
        if len(result.top_predictions) > 1:
            other_text = "<b>Other possibilities:</b><br>"
            for i, pred in enumerate(result.top_predictions[1:], 1):
                other_disease = pred['disease']
                other_conf = int(pred['confidence'] * 100)
                other_text += f"{i}. {other_disease.display_name}: {other_conf}%<br>"
            self.other_predictions_label.setText(other_text)
    
    # ========== MENU BAR FUNCTIONS ==========
    
    def new_scan(self):
        """Start a new scan (clear current)"""
        self.current_image_path = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("No image selected")
        self.image_info_label.setText("")
        self.analyze_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.clear_results()
        self.statusBar().showMessage("New scan started")
    
    def save_results(self):
        """Save current results to database"""
        if not self.last_result:
            QMessageBox.warning(self, "No Results", "No results to save. Analyze an image first.")
            return
        
        try:
            # Save scan record
            scan_record = self.create_scan_record()
            scan_id = db_manager.save_scan_record(scan_record)
            
            if scan_id:
                self.statusBar().showMessage(f"Results saved successfully (ID: {scan_id})", 3000)
                self.save_btn.setEnabled(False)  # Disable save button after saving
            else:
                QMessageBox.warning(self, "Save Error", "Failed to save results.")
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Error saving results: {e}")
    
    def create_scan_record(self):
        """Create a ScanRecord from current result"""
        from models.data_models import ScanRecord
        
        return ScanRecord(
            plant_type="tomato",
            image_path=self.current_image_path or "",
            diagnosis=self.last_result,
            user_notes="",
            location=None
        )
    
    def open_history(self):
        """Open history window"""
        try:
            self.history_window = HistoryWindow(self)
            self.history_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open history: {e}")
    
    def show_statistics(self):
        """Show scan statistics"""
        try:
            stats = db_manager.get_scan_statistics()
            
            stats_text = f"Total Scans: {stats.get('total_scans', 0)}\n"
            stats_text += f"Recent Activity (30 days): {stats.get('recent_scans', 0)}\n"
            stats_text += f"Accepted: {stats.get('accepted_scans', 0)}\n"
            stats_text += f"Rejected: {stats.get('rejected_scans', 0)}\n"
            stats_text += f"Rejection Rate: {stats.get('rejection_rate', 0):.1%}\n"
            
            db_size = stats.get('database_size', 0)
            if db_size < 1024:
                size_text = f"{db_size} bytes"
            elif db_size < 1024 * 1024:
                size_text = f"{db_size / 1024:.1f} KB"
            else:
                size_text = f"{db_size / (1024 * 1024):.1f} MB"
            
            stats_text += f"\nDatabase Size: {size_text}\n"
            
            QMessageBox.information(self, "Statistics", stats_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load statistics: {e}")
    
    def show_model_info(self):
        """Show model information"""
        if not self.model:
            QMessageBox.warning(self, "No Model", "Model not loaded.")
            return
        
        info = self.model.get_model_info()
        
        info_text = f"Architecture: {info['architecture']}\n"
        info_text += f"Device: {info['device']}\n"
        info_text += f"Total Parameters: {info['total_parameters']:,}\n"
        info_text += f"Number of Classes: {info['num_classes']}\n"
        info_text += f"Image Size: {info['image_size'][0]}×{info['image_size'][1]}\n"
        info_text += f"Threshold: {info['confidence_threshold']:.0%}\n"
        info_text += f"Model Path: {info['model_path']}"
        
        QMessageBox.information(self, "Model Information", info_text)
    
    def adjust_threshold(self):
        """Open threshold adjustment dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Adjust Confidence Threshold")
        dialog.setGeometry(500, 300, 400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Current threshold display
        current = self.model.threshold if self.model else DEFAULT_CONFIDENCE_THRESHOLD
        current_label = QLabel(f"Current Threshold: {current:.0%}")
        current_label.setFont(QFont("Arial", 12, QFont.Bold))
        current_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(current_label)
        
        # Slider for adjustment
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("10%"))
        
        threshold_slider = QSlider(Qt.Horizontal)
        threshold_slider.setRange(10, 90)
        threshold_slider.setValue(int(current * 100))
        slider_layout.addWidget(threshold_slider)
        
        slider_layout.addWidget(QLabel("90%"))
        layout.addLayout(slider_layout)
        
        # Value display
        value_label = QLabel(f"Set to: {current:.0%}")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        # Update label when slider moves
        def update_value_label(value):
            value_label.setText(f"Set to: {value/100:.0%}")
        
        threshold_slider.valueChanged.connect(update_value_label)
        
        # Description
        desc_label = QLabel("Lower threshold = more detections (more false positives)\n"
                          "Higher threshold = fewer detections (more accurate)")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(desc_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply")
        def apply_threshold():
            new_threshold = threshold_slider.value() / 100.0
            if self.model:
                self.model.set_threshold(new_threshold)
                self.threshold_label.setText(f"{new_threshold:.0%}")
                self.settings.setValue("confidence_threshold", new_threshold)
                dialog.accept()
        
        apply_btn.clicked.connect(apply_threshold)
        button_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
        LeafCheckAI v{APP_VERSION}
        
        Plant Disease Detection Application
        
        Features:
        • AI-powered leaf disease detection with attention mechanism
        • Support for 8 tomato diseases
        • Confidence threshold for reliable predictions
        • Local inference (no internet required)
        • Scan history tracking
        • Disease information and treatment advice
        
        Model: Attentive MobileNetV2
        Framework: PyTorch + TIMM
        GUI: PyQt5
        Database: MongoDB
        
        For educational and research purposes.
        """
        
        QMessageBox.about(self, f"About {APP_NAME}", about_text)