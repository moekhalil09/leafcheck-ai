# views/history_window.py - FIXED VERSION WITH DELETE
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QMessageBox, QTextEdit,
    QSplitter, QWidget, QTabWidget, QDateEdit,
    QComboBox, QCheckBox, QLineEdit
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QBrush, QColor
from datetime import datetime, timedelta

from models.database import db_manager
from models.data_models import DiagnosisResult

class HistoryWindow(QDialog):
    """Clean History Dialog for viewing saved scans"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.scan_ids = []  # Store scan IDs for each row
        self.setup_ui()
        self.load_history()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Scan History")
        self.setGeometry(300, 200, 1000, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Filter section
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        
        # Disease filter
        filter_layout.addWidget(QLabel("Disease:"))
        self.disease_filter = QComboBox()
        self.disease_filter.addItem("All Diseases", "")
        self.disease_filter.addItem("Healthy", "Tomato_Healthy")
        self.disease_filter.addItem("Early Blight", "Tomato_Early_Blight")
        self.disease_filter.addItem("Late Blight", "Tomato_Late_Blight")
        self.disease_filter.addItem("Bacterial Spot", "Tomato_Bacterial_Spot")
        self.disease_filter.addItem("Not Recognized", "rejected")
        self.disease_filter.currentIndexChanged.connect(self.load_history)
        filter_layout.addWidget(self.disease_filter)
        
        # Date range
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.load_history)
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.load_history)
        filter_layout.addWidget(self.date_to)
        
        filter_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_history)
        filter_layout.addWidget(self.refresh_btn)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # Tabs for different views
        self.tabs = QTabWidget()
        
        # Tab 1: Table View
        self.table_tab = QWidget()
        self.setup_table_tab()
        self.tabs.addTab(self.table_tab, "📊 Table View")
        
        # Tab 2: Statistics
        self.stats_tab = QWidget()
        self.setup_stats_tab()
        self.tabs.addTab(self.stats_tab, "📈 Statistics")
        
        main_layout.addWidget(self.tabs)
        
        # Action buttons at bottom
        button_layout = QHBoxLayout()
        
        self.view_details_btn = QPushButton("👁️ View Details")
        self.view_details_btn.clicked.connect(self.view_selected_details)
        self.view_details_btn.setEnabled(False)
        button_layout.addWidget(self.view_details_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("✖️ Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # Connect table selection
        self.scan_table.itemSelectionChanged.connect(self.on_selection_changed)
    
    def setup_table_tab(self):
        """Setup the table view tab"""
        layout = QVBoxLayout(self.table_tab)
        
        # Create table
        self.scan_table = QTableWidget()
        self.scan_table.setColumnCount(7)
        self.scan_table.setHorizontalHeaderLabels([
            "Date", "Disease", "Confidence", "Image", 
            "Size", "Time (s)", "Status"
        ])
        
        # Set column widths
        header = self.scan_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Disease
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Confidence
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Image
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Status
        
        self.scan_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.scan_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.scan_table)
        
        # Info label
        self.info_label = QLabel("Select a scan to view details")
        layout.addWidget(self.info_label)
    
    def setup_stats_tab(self):
        """Setup the statistics tab"""
        layout = QVBoxLayout(self.stats_tab)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.stats_text)
        
        # Update stats button
        self.update_stats_btn = QPushButton("Update Statistics")
        self.update_stats_btn.clicked.connect(self.update_statistics)
        layout.addWidget(self.update_stats_btn)
    
    def load_history(self):
        """Load scan history with filters"""
        try:
            # Get all scans from database (include rejected)
            all_scans = db_manager.get_recent_scans(limit=100, include_rejected=True)
            
            # Apply filters
            filtered_scans = self.apply_filters(all_scans)
            
            # Clear and populate table
            self.scan_table.setRowCount(0)
            self.scan_ids = []  # Reset scan IDs list
            
            for i, scan in enumerate(filtered_scans):
                self.scan_table.insertRow(i)
                
                # Store scan ID for this row
                scan_id = scan.get("_id", "")
                self.scan_ids.append(scan_id)
                
                # Date
                timestamp = scan.get("created_at") or scan.get("diagnosis", {}).get("timestamp")
                if isinstance(timestamp, datetime):
                    date_str = timestamp.strftime("%Y-%m-%d\n%H:%M")
                else:
                    date_str = str(timestamp)[:16] if timestamp else "Unknown"
                
                self.scan_table.setItem(i, 0, QTableWidgetItem(date_str))
                
                # Disease name
                disease_data = scan.get("diagnosis", {})
                disease_name = disease_data.get("display_name", "Unknown")
                disease_item = QTableWidgetItem(disease_name)
                self.scan_table.setItem(i, 1, disease_item)
                
                # Confidence
                confidence = disease_data.get("confidence", 0)
                confidence_percent = f"{confidence * 100:.1f}%"
                confidence_item = QTableWidgetItem(confidence_percent)
                
                # Color based on confidence and rejection status
                is_rejected = disease_data.get("is_rejected", False)
                if is_rejected:
                    confidence_item.setForeground(QBrush(QColor(158, 158, 158)))  # Gray
                elif confidence >= 0.8:
                    confidence_item.setForeground(QBrush(QColor(0, 128, 0)))  # Green
                elif confidence >= 0.6:
                    confidence_item.setForeground(QBrush(QColor(255, 165, 0)))  # Orange
                else:
                    confidence_item.setForeground(QBrush(QColor(255, 0, 0)))  # Red
                
                self.scan_table.setItem(i, 2, confidence_item)
                
                # Image filename
                image_path = scan.get("image_path", "")
                if image_path:
                    from pathlib import Path
                    filename = Path(image_path).name
                else:
                    filename = "No image"
                self.scan_table.setItem(i, 3, QTableWidgetItem(filename[:20]))
                
                # Image size
                image_size = disease_data.get("image_size", (0, 0))
                if isinstance(image_size, (list, tuple)) and len(image_size) >= 2:
                    size_str = f"{image_size[0]}×{image_size[1]}"
                else:
                    size_str = "N/A"
                self.scan_table.setItem(i, 4, QTableWidgetItem(size_str))
                
                # Inference time
                inference_time = disease_data.get("inference_time", 0)
                self.scan_table.setItem(i, 5, QTableWidgetItem(f"{inference_time:.3f}"))
                
                # Status
                if is_rejected:
                    status = "❌ Rejected"
                elif disease_data.get("disease_name") == "Tomato_Healthy":
                    status = "✅ Healthy"
                else:
                    status = "⚠️ Disease"
                status_item = QTableWidgetItem(status)
                self.scan_table.setItem(i, 6, status_item)
            
            # Update info label
            self.info_label.setText(f"Showing {len(filtered_scans)} scans (Total: {len(all_scans)})")
            
            # Update statistics
            self.update_statistics()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load history: {str(e)}")
    
    def apply_filters(self, scans):
        """Apply filters to scans"""
        filtered = []
        
        # Get filter values
        selected_disease = self.disease_filter.currentData()
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        
        for scan in scans:
            # Disease filter
            if selected_disease:
                disease_name = scan.get("diagnosis", {}).get("disease_name", "")
                if disease_name != selected_disease:
                    continue
            
            # Date filter
            timestamp = scan.get("created_at") or scan.get("diagnosis", {}).get("timestamp")
            if isinstance(timestamp, datetime):
                scan_date = timestamp.date()
                if not (date_from <= scan_date <= date_to):
                    continue
            
            filtered.append(scan)
        
        return filtered
    
    def update_statistics(self):
        """Update statistics display"""
        try:
            stats = db_manager.get_scan_statistics()
            
            stats_text = "📊 SCAN STATISTICS\n"
            stats_text += "=" * 50 + "\n\n"
            
            stats_text += f"Total Scans: {stats.get('total_scans', 0)}\n"
            stats_text += f"Recent Activity (30 days): {stats.get('recent_scans', 0)}\n"
            stats_text += f"Accepted: {stats.get('accepted_scans', 0)}\n"
            stats_text += f"Rejected: {stats.get('rejected_scans', 0)}\n"
            stats_text += f"Rejection Rate: {stats.get('rejection_rate', 0):.1%}\n\n"
            
            stats_text += "📈 DISEASE DISTRIBUTION (Accepted Only)\n"
            stats_text += "-" * 40 + "\n"
            
            disease_stats = stats.get('disease_stats', [])
            if disease_stats:
                for disease in disease_stats[:10]:  # Top 10
                    disease_name = disease['_id'].replace('_', ' ').title()
                    count = disease['count']
                    stats_text += f"{disease_name:<25} {count:>4}\n"
            else:
                stats_text += "No disease data available\n"
            
            # Current filters info
            stats_text += "\n🔍 CURRENT FILTERS\n"
            stats_text += "-" * 30 + "\n"
            stats_text += f"Disease: {self.disease_filter.currentText()}\n"
            stats_text += f"Date Range: {self.date_from.date().toString('yyyy-MM-dd')} to {self.date_to.date().toString('yyyy-MM-dd')}\n"
            
            self.stats_text.setText(stats_text)
            
        except Exception as e:
            self.stats_text.setText(f"Error loading statistics: {str(e)}")
    
    def on_selection_changed(self):
        """Handle table selection change"""
        selected_rows = self.scan_table.selectionModel().selectedRows()
        
        if selected_rows:
            self.view_details_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            
            # Get selected scan data
            row = selected_rows[0].row()
            
            # Update info label
            disease = self.scan_table.item(row, 1).text() if self.scan_table.item(row, 1) else "Unknown"
            confidence = self.scan_table.item(row, 2).text() if self.scan_table.item(row, 2) else "0%"
            self.info_label.setText(f"Selected: {disease} ({confidence})")
        else:
            self.view_details_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.info_label.setText("Select a scan to view details")
    
    def view_selected_details(self):
        """View details of selected scan"""
        selected_rows = self.scan_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Get data from table
        date = self.scan_table.item(row, 0).text() if self.scan_table.item(row, 0) else "Unknown"
        disease = self.scan_table.item(row, 1).text() if self.scan_table.item(row, 1) else "Unknown"
        confidence = self.scan_table.item(row, 2).text() if self.scan_table.item(row, 2) else "0%"
        image_file = self.scan_table.item(row, 3).text() if self.scan_table.item(row, 3) else "No image"
        size = self.scan_table.item(row, 4).text() if self.scan_table.item(row, 4) else "N/A"
        inference_time = self.scan_table.item(row, 5).text() if self.scan_table.item(row, 5) else "0"
        status = self.scan_table.item(row, 6).text() if self.scan_table.item(row, 6) else "Unknown"
        
        # Create details dialog
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle("Scan Details")
        details_dialog.setGeometry(400, 300, 500, 400)
        
        layout = QVBoxLayout(details_dialog)
        
        # Details text
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details = f"🔍 SCAN DETAILS\n"
        details += "=" * 40 + "\n\n"
        details += f"📅 Date/Time: {date}\n"
        details += f"🦠 Disease: {disease}\n"
        details += f"🎯 Confidence: {confidence}\n"
        details += f"📷 Image: {image_file}\n"
        details += f"📐 Size: {size}\n"
        details += f"⏱️ Inference Time: {inference_time}s\n"
        details += f"🩺 Status: {status}\n\n"
        
        # Try to get more details from database using stored scan ID
        try:
            if row < len(self.scan_ids):
                scan_id = self.scan_ids[row]
                # Get scan from database by ID
                scan = db_manager.get_scan_by_id(scan_id)
                if scan:
                    diagnosis = scan.get("diagnosis", {})
                    details += "📝 ADDITIONAL INFO\n"
                    details += "-" * 30 + "\n"
                    if diagnosis.get("description"):
                        details += f"Description: {diagnosis.get('description', '')}\n\n"
                    if diagnosis.get("symptoms"):
                        details += "Symptoms:\n"
                        for symptom in diagnosis.get("symptoms", [])[:3]:
                            details += f"• {symptom}\n"
                        details += "\n"
                    if diagnosis.get("treatment"):
                        details += "Treatment:\n"
                        for treatment in diagnosis.get("treatment", [])[:3]:
                            details += f"• {treatment}\n"
        except:
            pass
        
        details_text.setText(details)
        layout.addWidget(details_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(details_dialog.accept)
        layout.addWidget(close_btn)
        
        details_dialog.exec_()
    
    def delete_selected(self):
        """Delete selected scan from database"""
        selected_rows = self.scan_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        
        # Get the scan ID for this row
        if row >= len(self.scan_ids):
            QMessageBox.warning(self, "Error", "Cannot delete: Scan ID not found")
            return
        
        scan_id = self.scan_ids[row]
        disease = self.scan_table.item(row, 1).text() if self.scan_table.item(row, 1) else "Unknown"
        date = self.scan_table.item(row, 0).text() if self.scan_table.item(row, 0) else "Unknown"
        
        reply = QMessageBox.question(
            self, 
            "Delete Scan",
            f"Are you sure you want to delete this scan?\n\n"
            f"Date: {date}\n"
            f"Disease: {disease}\n"
            f"ID: {scan_id[:8]}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Call database manager to delete by ID
                success = db_manager.delete_scan(scan_id)
                
                if success:
                    # Remove from table
                    self.scan_table.removeRow(row)
                    # Remove from scan_ids list
                    if row < len(self.scan_ids):
                        self.scan_ids.pop(row)
                    
                    QMessageBox.information(self, "Deleted", "Scan deleted successfully.")
                    
                    # Reload to refresh data
                    self.load_history()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete scan from database.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting scan: {str(e)}")
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.accept()
        elif event.key() == Qt.Key_F5:
            self.load_history()
        else:
            super().keyPressEvent(event)