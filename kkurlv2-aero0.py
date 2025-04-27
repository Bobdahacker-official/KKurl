import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QHBoxLayout, QPushButton, QDockWidget,
    QListWidget, QCheckBox, QListWidgetItem, QInputDialog
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

# Custom WebEngineView to set USER AGENT
class CustomWebEngineView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        profile = self.page().profile()
        profile.setHttpUserAgent(
            "KKURL/1.0, KKURLVM/1.0, QtWebEngine/1.0 (KKURLVM; KKURL ONE Browse; Custom Agent)"
        )

    def createWindow(self, type):
        if type == QWebEnginePage.WebBrowserTab:
            return self
        return super().createWindow(type)

# Extension Management Class
class Extension:
    def __init__(self, name, path, manifest):
        self.name = name
        self.path = path
        self.manifest = manifest
        self.enabled = False
        self.background_script = os.path.join(self.path, "background.js")
        self.content_script = os.path.join(self.path, "content.js")

    def enable(self, browser):
        if not self.enabled:
            if os.path.exists(self.background_script):
                with open(self.background_script, "r") as script_file:
                    background_script = script_file.read()
                browser.webview.page().runJavaScript(background_script)
            if os.path.exists(self.content_script):
                with open(self.content_script, "r") as script_file:
                    content_script = script_file.read()
                browser.webview.page().runJavaScript(content_script)
            self.enabled = True
            print(f"Enabled extension: {self.name}")

    def disable(self, browser):
        self.enabled = False
        print(f"Disabled extension: {self.name}")

    def update_code(self, background_code, content_code):
        with open(self.background_script, 'w') as f:
            f.write(background_code)
        with open(self.content_script, 'w') as f:
            f.write(content_code)
        print(f"Updated extension {self.name} with new code.")

# Main Browser Class
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KKURL BROWSER")
        self.setGeometry(100, 100, 1200, 800)

        self.cache_folder = os.path.join(os.getenv("USERPROFILE"), "Documents", "QtWebEngine", "Cache")
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

        profile = QWebEngineProfile.defaultProfile()
        profile.setCachePath(self.cache_folder)

        self.main_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_widget)

        # URL bar and navigation buttons
        self.url_bar = QLineEdit(self)
        self.url_bar.returnPressed.connect(self.load_url_from_input)
        self.url_layout = QHBoxLayout()
        self.url_layout.addWidget(self.url_bar)

        self.back_button = QPushButton("Back", self)
        self.back_button.clicked.connect(self.navigate_back)
        self.forward_button = QPushButton("Forward", self)
        self.forward_button.clicked.connect(self.navigate_forward)
        self.reload_button = QPushButton("Reload", self)
        self.reload_button.clicked.connect(self.reload_page)
        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh_page)

        self.nav_layout = QHBoxLayout()
        self.nav_layout.addWidget(self.back_button)
        self.nav_layout.addWidget(self.forward_button)
        self.nav_layout.addWidget(self.reload_button)
        self.nav_layout.addWidget(self.refresh_button)

        self.main_layout.addLayout(self.nav_layout)
        self.main_layout.addLayout(self.url_layout)

        # WebView
        self.webview = CustomWebEngineView(self)
        self.webview.setUrl(QUrl("https://google.com"))
        self.webview.loadFinished.connect(self.update_url)
        self.main_layout.addWidget(self.webview)

        self.setCentralWidget(self.main_widget)

        # STYLESHEET DARK HACKER VIBES
        self.setStyleSheet("""
        QMainWindow {
            background-color: black;
            background-image: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #0f0f0f, stop:0.5 #1f1f1f, stop:1 #0f0f0f
            );
        }
        QPushButton {
            background-color: #1e1e1e;
            color: #00ff99;
            border: 2px solid #00ff99;
            border-radius: 15px;
            padding: 8px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
        }
        QPushButton:hover {
            background-color: #00ff99;
            color: black;
        }
        QLineEdit {
            background-color: #1e1e1e;
            color: #00ff99;
            border: 2px solid #00ff99;
            border-radius: 10px;
            padding: 6px;
            font-family: 'Courier New', monospace;
        }
        QDockWidget {
            background-color: #121212;
            border: 2px solid #00ff99;
        }
        QListWidget {
            background-color: #121212;
            color: #00ff99;
            font-family: 'Courier New', monospace;
        }
        """)

        # Extension Manager
        self.extension_manager = QDockWidget("Extensions", self)
        self.extension_list = QListWidget(self)
        self.extension_manager.setWidget(self.extension_list)
        self.addDockWidget(1, self.extension_manager)
        self.setDockOptions(QMainWindow.AllowNestedDocks)

        self.extensions_dir = os.path.join(os.getcwd(), "extensions")
        if not os.path.exists(self.extensions_dir):
            os.makedirs(self.extensions_dir)

        self.load_extensions()

        # Add Extension Button
        self.add_extension_button = QPushButton("Add Extension", self)
        self.add_extension_button.clicked.connect(self.add_extension)
        self.main_layout.addWidget(self.add_extension_button)

        # Extension Manager Button
        self.extension_manager_button = QPushButton("Extension Manager", self)
        self.extension_manager_button.clicked.connect(self.show_extension_manager)
        self.main_layout.addWidget(self.extension_manager_button)

        self.show()

    def load_extensions(self):
        self.extensions = []
        self.extension_list.clear()
        for ext_name in os.listdir(self.extensions_dir):
            ext_path = os.path.join(self.extensions_dir, ext_name)
            if os.path.isdir(ext_path):
                manifest_path = os.path.join(ext_path, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as manifest_file:
                        manifest = json.load(manifest_file)
                    extension = Extension(ext_name, ext_path, manifest)
                    self.extensions.append(extension)

                    item = QListWidgetItem(ext_name)
                    checkbox = QCheckBox(f"Enable {ext_name}")
                    checkbox.stateChanged.connect(lambda state, ext=extension: self.toggle_extension(state, ext))
                    self.extension_list.addItem(item)
                    self.extension_list.setItemWidget(item, checkbox)

    def add_extension(self):
        extension_name, ok = QInputDialog.getText(self, "Extension Name", "Enter the name of the new extension:")
        if ok and extension_name:
            extension_path = os.path.join(self.extensions_dir, extension_name)
            if not os.path.exists(extension_path):
                os.makedirs(extension_path)

                manifest = {
                    "name": extension_name,
                    "version": "1.0",
                    "description": f"Custom extension for {extension_name}",
                    "permissions": ["tabs"],
                    "background": {"scripts": ["background.js"]},
                    "content_scripts": [
                        {"matches": ["<all_urls>"], "js": ["content.js"]}
                    ]
                }

                with open(os.path.join(extension_path, "manifest.json"), "w") as f:
                    json.dump(manifest, f, indent=4)

                with open(os.path.join(extension_path, "background.js"), "w") as f:
                    f.write("console.log('Background script running...');")

                with open(os.path.join(extension_path, "content.js"), "w") as f:
                    f.write("console.log('Content script injected...'); document.body.style.backgroundColor = 'yellow';")

                print(f"Extension {extension_name} created successfully!")
                self.load_extensions()

    def toggle_extension(self, state, extension):
        if state == 2:
            extension.enable(self)
        else:
            extension.disable(self)

    def load_url_from_input(self):
        url = self.url_bar.text()
        if url.startswith("kkurl://ext"):
            self.show_extension_manager()
        elif not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        self.webview.setUrl(QUrl(url))

    def show_extension_manager(self):
        html_content = """
        <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Extension Manager</title></head><body>
        <h1 style="color: lime;">Extension Manager</h1><p>Manage your extensions here.</p></body></html>
        """
        self.webview.setHtml(html_content)

    def read_code(self, path):
        if os.path.exists(path):
            with open(path, 'r') as file:
                return file.read()
        return ""

    def update_url(self):
        self.url_bar.setText(self.webview.url().toString())

    def navigate_back(self):
        if self.webview.history().canGoBack():
            self.webview.back()

    def navigate_forward(self):
        if self.webview.history().canGoForward():
            self.webview.forward()

    def reload_page(self):
        self.webview.reload()

    def refresh_page(self):
        self.webview.reload()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Browser()
    sys.exit(app.exec_())
