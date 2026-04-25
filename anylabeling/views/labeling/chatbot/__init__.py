# Stub module for chatbot functionality
# Chatbot features are not available in web service mode

from PyQt6.QtWidgets import QDialog

class ChatbotDialog(QDialog):
    """Stub chatbot dialog for compatibility"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chatbot (Not available in web mode)")

from .style import ChatbotDialogStyle
