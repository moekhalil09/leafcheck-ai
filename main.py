# main.py
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from views.main_window import MainWindow
from config import APP_NAME

def main():
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()