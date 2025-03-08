import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout, QPushButton, QDockWidget, QListWidget, QCheckBox, QListWidgetItem, QInputDialog, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, QFile, QTextStream, QDir, pyqtSignal
from PyQt5.QtGui import QIcon

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
        """ Update the extension's code on disk. """
        with open(self.background_script, 'w') as f:
            f.write(background_code)
        
        with open(self.content_script, 'w') as f:
            f.write(content_code)
        
        print(f"Updated extension {self.name} with new code.")

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

        # Custom WebEngine View with overridden URL handling
        self.webview = CustomWebEngineView(self)
        self.webview.setUrl(QUrl("http://www.google.com"))

        # Connecting the loadFinished signal correctly
        self.webview.loadFinished.connect(self.update_url)

        self.main_layout.addWidget(self.webview)
        self.setCentralWidget(self.main_widget)

        # Extension Management - Dockable Panel
        self.extension_manager = QDockWidget("Extensions", self)
        self.extension_list = QListWidget(self)
        self.extension_manager.setWidget(self.extension_list)

        self.addDockWidget(1, self.extension_manager)  # Dock on the left side
        self.setDockOptions(QMainWindow.AllowNestedDocks)

        # Load extensions from local directory
        self.extensions_dir = os.path.join(os.getcwd(), "extensions")
        if not os.path.exists(self.extensions_dir):
            os.makedirs(self.extensions_dir)

        self.load_extensions()

        # Button to add a new extension
        self.add_extension_button = QPushButton("Add Extension", self)
        self.add_extension_button.clicked.connect(self.add_extension)
        self.main_layout.addWidget(self.add_extension_button)

        # Button to show Extension Manager (new button)
        self.extension_manager_button = QPushButton("Extension Manager", self)
        self.extension_manager_button.clicked.connect(self.show_extension_manager)
        self.main_layout.addWidget(self.extension_manager_button)

        self.show()

    def load_extensions(self):
        """ Load extensions from the local 'extensions' directory. """
        self.extensions = []
        self.extension_list.clear()  # Clear the list before reloading

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
        """ Adds a new extension by creating necessary files (manifest, content, background). """
        extension_name, ok = QInputDialog.getText(self, "Extension Name", "Enter the name of the new extension:")
        if ok and extension_name:
            extension_path = os.path.join(self.extensions_dir, extension_name)
            if not os.path.exists(extension_path):
                os.makedirs(extension_path)

                # Create a default manifest.json
                manifest = {
                    "name": extension_name,
                    "version": "1.0",
                    "description": f"Custom extension for {extension_name}",
                    "permissions": ["tabs"],
                    "background": {
                        "scripts": ["background.js"]
                    },
                    "content_scripts": [
                        {
                            "matches": ["<all_urls>"],
                            "js": ["content.js"]
                        }
                    ]
                }

                manifest_path = os.path.join(extension_path, "manifest.json")
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=4)

                # Create a default background.js
                background_js = """
console.log('Background script running...');
"""
                background_js_path = os.path.join(extension_path, "background.js")
                with open(background_js_path, "w") as f:
                    f.write(background_js)

                # Create a default content.js
                content_js = """
console.log('Content script injected...');
document.body.style.backgroundColor = 'yellow';
"""
                content_js_path = os.path.join(extension_path, "content.js")
                with open(content_js_path, "w") as f:
                    f.write(content_js)

                print(f"Extension {extension_name} created successfully!")
                self.load_extensions()

    def toggle_extension(self, state, extension):
        """ Enable/Disable an extension based on checkbox state. """
        if state == 2:  # Checked
            extension.enable(self)
        else:
            extension.disable(self)

    def load_url_from_input(self):
        """ Load URL from the input bar. """
        url = self.url_bar.text()
        if url.startswith("kkurl://ext"):
            self.show_extension_manager()  # Load extension manager when kkurl://ext is entered
        elif not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        self.webview.setUrl(QUrl(url))

    def show_extension_manager(self):
        """ Show the extension management UI. """
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Extension Management</title>
            <style>
                body { font-family: Arial, sans-serif; }
                .extension-list { margin-top: 20px; }
                .extension { margin-bottom: 10px; }
                .code-editor { width: 100%; height: 200px; }
            </style>
        </head>
        <body>
            <h1>Manage Extensions</h1>
            <div class="extension-list">
        """
        
        for ext in self.extensions:
            html_content += f"""
                <div class="extension">
                    <label>{ext.name}</label>
                    <input type="checkbox" id="checkbox_{ext.name}" onclick="toggleExtension('{ext.name}')" />
                    <textarea id="background_{ext.name}" class="code-editor">{self.read_code(ext.background_script)}</textarea>
                    <textarea id="content_{ext.name}" class="code-editor">{self.read_code(ext.content_script)}</textarea>
                    <button onclick="updateCode('{ext.name}')">Save Changes</button>
                </div>
            """

        html_content += """
            </div>
            <script>
                function toggleExtension(extensionName) {
                    // Call backend to enable/disable extension (this part would be handled in a real browser)
                    alert(extensionName + " toggled!");
                }
                function updateCode(extensionName) {
                    var backgroundCode = document.getElementById("background_" + extensionName).value;
                    var contentCode = document.getElementById("content_" + extensionName).value;
                    // Call backend to save code and apply changes
                    alert("Updating " + extensionName);
                    // Make a request to save the updated code to the server or backend
                }
            </script>
        </body>
        </html>
        """

        self.webview.setHtml(html_content)

    def read_code(self, path):
        """ Read and return the code from a file. """
        if os.path.exists(path):
            with open(path, 'r') as file:
                return file.read()
        return ""

    def update_url(self):
        """ Update the URL bar after the page has loaded. """
        current_url = self.webview.url().toString()
        self.url_bar.setText(current_url)

    def navigate_back(self):
        """ Navigate back in history. """
        if self.webview.history().canGoBack():
            self.webview.back()

    def navigate_forward(self):
        """ Navigate forward in history. """
        if self.webview.history().canGoForward():
            self.webview.forward()

    def reload_page(self):
        """ Reload the page. """
        self.webview.reload()

    def refresh_page(self):
        """ Refresh the page. """
        self.webview.reload()

class CustomWebEngineView(QWebEngineView):
    def __init__(self, parent):
        super().__init__(parent)

    def createWindow(self, type):
        if type == QWebEnginePage.WebBrowserTab:
            return self
        return super().createWindow(type)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Browser()
    sys.exit(app.exec_())


