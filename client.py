import sys
import socket
import threading
import re

import mysql
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTextBrowser, \
    QMessageBox
from PyQt5.QtCore import pyqtSignal, QThread


class Client(QThread):
    stop_signal = False
    message_received = pyqtSignal(str)

    def __init__(self, socket):
        super().__init__()
        self.client_socket = socket

    def run(self):
        while not self.stop_signal:
            try:
                message = self.client_socket.recv(1024).decode()
                self.message_received.emit(message)
            except OSError:
                break

    def stop(self):
        self.stop_signal = True

    def __init__(self, socket):
        super().__init__()
        self.client_socket = socket


class LoginWidget(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        label_username = QLabel("login:")
        self.entry_username = QLineEdit()
        layout.addWidget(label_username)
        layout.addWidget(self.entry_username)

        label_password = QLabel("Mot de passe:")
        self.entry_password = QLineEdit()
        self.entry_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(label_password)
        layout.addWidget(self.entry_password)

        label_alias = QLabel("Alias:")
        self.entry_alias = QLineEdit()
        layout.addWidget(label_alias)
        layout.addWidget(self.entry_alias)

        button_login = QPushButton("Se connecter")
        button_login.clicked.connect(self.login)
        layout.addWidget(button_login)
        # pas de bouton enregistrement, les clients sont déja dans ma base de donnée
        self.setLayout(layout)

        self.setStyleSheet("""
                            QDialog {
                                background-color: #2C3E50;
                            }
                            QLabel {
                                color: #000000;
                                font-size: 16px;
                                margin-bottom: 5px;
                            }
                            QLineEdit {
                                background-color: #3498DB;
                                color: #ECF0F1;
                                border: 1px solid #2C3E50;
                                border-radius: 4px;
                                padding: 8px;
                                margin-bottom: 10px;
                            }
                            QPushButton {
                                background-color: #3498DB;
                                color: #ECF0F1;
                                border: none;
                                padding: 10px;
                                border-radius: 4px;
                                cursor: pointer;
                            }
                            QPushButton:hover {
                                background-color: #2980B9;
                            }
                        """)

    def check_user_exists(self, username, password=None, db_connection=None):
        accounts = {
            "jean": "123",
            "paul": "paulii",
            "alpha": "test1",
            "beta": "terri1",
            "omega": "test3"}
        #  for username, password in accounts.items():
        # Requête d'insertion
        #     insert_query = "INSERT INTO clients (username, password) VALUES (%s, %s)"
        #     data = (username, password)

        # Exécution de la requête
        #      cursor = db_connection.cursor()
        #      cursor.execute(insert_query, data)
        #     db_connection.commit()

        # Fermeture du curseur et de la connexion
        #   cursor.close()
        # db_connection.close()

        if username in accounts:
            if password and password == accounts[username]:
                return True
            elif not password:
                return True

        return False

    # elif username in accounts:
    # if password == accounts[username]:
    #    client_conn[conn] = login
    def login(self):
        username = self.entry_username.text()
        password = self.entry_password.text()
        alias = self.entry_alias.text()

        user_exists = self.check_user_exists(username, password)

        if not user_exists:
            QMessageBox.critical(self, "Erreur", "Nom d'utilisateur ou mot de passe incorrect.")
            return

        registration_data = f"{alias}"
        self.client.client_socket.send(registration_data.encode())
        self.client.request_join_channel("Général")
        self.client.show_main_window()
        self.close()

    def authenticate(self):
        username = self.entry_username.text()
        password = self.entry_password.text()
        alias = self.entry_alias.text()

        # Vérification de l'authentification admin dans la base de données
        db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="toto",
            database="sae"
        )
        cursor = db_connection.cursor()
        query = "SELECT * FROM clients WHERE username=%s AND password=%s "
        cursor.execute(query, (username, password))
        admin_data = cursor.fetchone()

        if admin_data:
            self.accept()

        else:
            QMessageBox.critical(
                self, "Authentication Error", "Invalid users username or password."
            )
        registration_data = f"{alias}"
        self.client.client_socket.send(registration_data.encode())
        self.client.request_join_channel("Général")
        self.client.show_main_window()
        self.close()


class ChannelChatWindow(QWidget):
    def __init__(self, client, channel_name):
        super().__init__()
        self.client = client
        self.channel_name = channel_name
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Salon {self.channel_name}")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout()

        self.label_current_channel = QLabel(f"Salon actuel: {self.channel_name}")
        self.layout.addWidget(self.label_current_channel)

        self.label_users = QLabel("Utilisateurs connectés:")
        self.layout.addWidget(self.label_users)

        self.text_browser = QTextBrowser()
        self.layout.addWidget(self.text_browser)

        self.entry_message = QLineEdit()
        self.entry_message.returnPressed.connect(self.send_message)
        self.layout.addWidget(self.entry_message)

        self.button_send = QPushButton("Envoyer")
        self.button_send.clicked.connect(self.send_message)
        self.layout.addWidget(self.button_send)

        self.button_disconnect = QPushButton("Déconnexion")
        self.button_disconnect.clicked.connect(self.disconnect)
        self.layout.addWidget(self.button_disconnect)

        self.setLayout(self.layout)

        self.setStyleSheet("""
                                   QDialog {
                                       background-color: #2C3E50;
                                   }
                                   QLabel {
                                       color: #000000;
                                       font-size: 16px;
                                       margin-bottom: 5px;
                                   }
                                   QLineEdit {
                                       background-color: #3498DB;
                                       color: #ECF0F1;
                                       border: 1px solid #2C3E50;
                                       border-radius: 4px;
                                       padding: 8px;
                                       margin-bottom: 10px;
                                   }
                                   QPushButton {
                                       background-color: #3498DB;
                                       color: #ECF0F1;
                                       border: none;
                                       padding: 10px;
                                       border-radius: 4px;
                                       cursor: pointer;
                                   }
                                   QPushButton:hover {
                                       background-color: #2980B9;
                                   }
                               """)

    def send_message(self):
        message = self.entry_message.text()
        print(f"Sending message: {message}")  # Ajoute cette ligne pour déboguer
        if message:
            self.client.client_socket.send(f"{message}".encode())
            self.entry_message.clear()

    def handle_message(self, message):
        if message.startswith("USERS|"):
            _, users = message.split("|")
            users_list = users.split(",")
            self.update_users_label(users_list)
        else:
            self.text_browser.append(message)

    def update_users_label(self, users_list):
        users_text = ", ".join(users_list)
        self.label_users.setText(f"Utilisateurs connectés: {users_text}")

    def disconnect(self):
        self.client.disconnect_from_server()


class ClientChat(QWidget):
    def __init__(self):
        super().__init__()

        self.username = None
        self.current_channel_name = "Général"
        self.channels = ["Général", "Blabla", "Comptabilité", "Informatique", "Marketing"]
        self.channel_windows = {}
        self.current_channel_window = None

        self.init_ui()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(('127.0.0.1', 10000))

        self.client_thread = Client(self.client_socket)
        self.client_thread.message_received.connect(self.handle_message)
        self.client_thread.start()

        self.login_widget = LoginWidget(self)

    def init_ui(self):
        layout = QVBoxLayout()

        label_channel = QLabel("Choisir un salon:")
        self.combo_box_channel = QComboBox()
        self.combo_box_channel.addItems(self.channels)
        self.combo_box_channel.currentIndexChanged.connect(self.change_channel)
        layout.addWidget(label_channel)
        layout.addWidget(self.combo_box_channel)

        show_channel_button = QPushButton("Afficher le salon")
        show_channel_button.clicked.connect(self.show_channel)
        layout.addWidget(show_channel_button)

        self.button_disconnect = QPushButton("Déconnexion")
        self.button_disconnect.clicked.connect(self.disconnect_from_server)
        layout.addWidget(self.button_disconnect)

        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #2C3E50;
                color: #ECF0F1;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QLabel {
                color: #ECF0F1;
                font-size: 14px;
            }
            QComboBox, QPushButton {
                background-color: #3498DB;
                color: #ECF0F1;
                border: none;
                padding: 50px;
                border-radius: 10px;
            }
            QComboBox:hover, QPushButton:hover {
                background-color: #2980B9;
            }
        """)

    def show_main_window(self):
        self.login_widget.close()
        self.show()

    def change_channel(self):
        selected_channel = self.combo_box_channel.currentText()
        self.current_channel_name = selected_channel
        if selected_channel not in self.channel_windows:
            self.channel_windows[selected_channel] = ChannelChatWindow(self, selected_channel)
        for channel_name, window in self.channel_windows.items():
            if channel_name == self.current_channel_name:
                window.show()
            else:
                window.hide()

    def show_channel(self):
        pass

    def request_join_channel(self, channel):
        join_request = f"JOIN|{channel}|{self.username}"
        self.client_socket.send(join_request.encode())

    def handle_message(self, message):
        if message.startswith("USERS|"):
            _, users = message.split("|")
            users_list = users.split(",")
            if self.current_channel_name in self.channel_windows:
                self.channel_windows[self.current_channel_name].handle_message(message)
                self.channel_windows[self.current_channel_name].update_users_label(users_list)
        elif self.current_channel_name in self.channel_windows:
            self.channel_windows[self.current_channel_name].handle_message(message)

    def disconnect_from_server(self):
        self.client_thread.terminate()
        self.client_socket.close()
        sys.exit(app.exec_())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = ClientChat()
    client.login_widget.show()
    sys.exit(app.exec_())
