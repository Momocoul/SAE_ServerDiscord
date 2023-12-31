import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QInputDialog,
    QLabel, QLineEdit, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog

import socket
import threading
import mysql.connector


class AdminAuthDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Admin Authentication")
        self.setGeometry(200, 200, 400, 200)

        layout = QVBoxLayout()

        self.label_username = QLabel("Admin Username:", self)
        self.entry_username = QLineEdit(self)
        layout.addWidget(self.label_username)
        layout.addWidget(self.entry_username)

        self.label_password = QLabel("Admin Password:", self)
        self.entry_password = QLineEdit(self)
        self.entry_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.label_password)
        layout.addWidget(self.entry_password)

        button_authenticate = QPushButton("Authenticate", self)
        button_authenticate.clicked.connect(self.authenticate)
        layout.addWidget(button_authenticate)

        self.setLayout(layout)

    def authenticate(self):
        entered_username = self.entry_username.text()
        entered_password = self.entry_password.text()

        # Vérification de l'authentification admin dans la base de données
        db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="toto",
            database="sae"
        )
        cursor = db_connection.cursor()
        query = "SELECT * FROM clients WHERE username=%s AND password=%s AND admin=%s"
        cursor.execute(query, (entered_username, entered_password, 1))
        admin_data = cursor.fetchone()

        if admin_data:
            self.accept()
        else:
            QMessageBox.critical(
                self, "Authentication Error", "Invalid admin username or password."
            )


class Server(QMainWindow):
    def __init__(self):
        super().__init__()
        self.clients = {}
        self.server_socket = None
        self.server_running = False
        self.db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="toto",
            database="sae",
        )
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(
            '''
                      CREATE TABLE IF NOT EXISTS clients (
                          id INT AUTO_INCREMENT PRIMARY KEY,
                          username VARCHAR(255),
                          password VARCHAR(255),

                          ip_address VARCHAR(15),
                          kick_expiry DATETIME,
                          ban_expiry DATETIME,
                          admin BOOLEAN DEFAULT False,
                          kicked BOOLEAN DEFAULT False,
                          banned BOOLEAN DEFAULT False
                      )
                  '''
        )

        self.db_cursor.execute(
            '''
           CREATE TABLE IF NOT EXISTS message (
               id INT AUTO_INCREMENT PRIMARY KEY,
               clients VARCHAR(255),
               message_text TEXT,
               timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )
       '''
        )

        self.db_connection.commit()
        self.init_ui()

        self.kick_timer = QTimer(self)
        self.kick_timer.timeout.connect(self.kick_timer_expired)
        self.kick_duration = 0

        self.ban_timer = QTimer(self)
        self.ban_timer.timeout.connect(self.ban_timer_expired)
        self.ban_duration = 0

    def authenticate_admin(self):
        dialog = AdminAuthDialog()
        result = dialog.exec_()
        self.admin_authenticated = result == QDialog.Accepted

    def show_interface(self):
        self.setWindowTitle("Server Chat")
        self.setGeometry(100, 100, 600, 400)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.client_list_label = QLabel("Clients connectés:", self)
        self.client_list_label.setAlignment(Qt.AlignCenter)

        self.start_button = QPushButton("Start Server", self)
        self.start_button.clicked.connect(self.start_server)

        self.stop_button = QPushButton("Stop Server", self)
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)

        self.kick_button = QPushButton("Kick clients", self)
        self.kick_button.clicked.connect(self.kick_user)
        self.kick_button.setEnabled(False)

        self.ban_button = QPushButton("Ban clients", self)
        self.ban_button.clicked.connect(self.ban_user)
        self.ban_button.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.client_list_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.kick_button)
        layout.addWidget(self.ban_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Afficher la fenêtre principale après l'authentification réussie
        self.show()

    def init_ui(self):
        self.authenticate_admin()
        if not self.admin_authenticated:
            sys.exit()

        # Déplacer la création de la fenêtre principale ici
        self.show_interface()

        self.setStyleSheet("""
                    QDialog {
                        background-color: #2C3E50;
                    }
                    QLabel {
                        color: #ECF0F1;
                        font-size: 16px;
                        margin-bottom: 5px;
                    }
                    QLineEdit {
                        background-color: #34495E;
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

    def start_server(self):
        # Appelle d'abord la méthode authenticate_admin
        self.authenticate_admin()

        # Si l'authentification est réussie, continue avec le démarrage du serveur
        if self.admin_authenticated:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('0.0.0.0', 10000))
            self.server_socket.listen()

            self.server_running = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.kick_button.setEnabled(True)
            self.ban_button.setEnabled(True)

            self.print_message("Le serveur est en attente de connexions...")

            server_thread = threading.Thread(target=self.accept_connections)
            server_thread.start()

        else:
            # Si l'authentification échoue, tu peux afficher un message ou prendre une autre action.
            QMessageBox.critical(self, "Authentication échoué")

    def stop_server(self):
        self.server_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.kick_button.setEnabled(False)
        self.ban_button.setEnabled(False)
        if self.server_socket:
            self.server_socket.close()
        self.print_message("Le serveur a été arrêté.")

    def accept_connections(self):
        while self.server_running:
            client_socket, client_address = self.server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client, args=(client_socket, client_address)
            )
            client_thread.start()

    def handle_client(self, client_socket, client_address):
        try:
            client_username = client_socket.recv(1024).decode()
            self.insert_client(client_username, client_address[0])
            self.clients[client_username] = {
                "socket": client_socket,
                "kicked": False,
                "banned": False,
            }
            self.broadcast(f"{client_username} a réjoint la conversation.\n")
            while self.server_running:
                message = client_socket.recv(1024)
                if not message:
                    break
                self.broadcast(f"{client_username}: {message.decode()}")
                self.insert_message(client_username, message.decode())
                self.update_client_list()
        except Exception as e:
            self.print_message(f"Erreur client {client_address}: {e}")
        finally:
            if client_username in self.clients:
                del self.clients[client_username]
                self.broadcast(f"{client_username} a quitté la conversation.\n")
                self.update_client_list()
            client_socket.close()

    def insert_client(self, username, ip_address):
        self.db_cursor.execute(
            "INSERT INTO clients (username, ip_address) VALUES (%s, %s)",
            (username, ip_address),
        )
        self.db_connection.commit()

    def insert_message(self, sender_username, message_text):
        self.db_cursor.execute(
            "INSERT INTO message (clients, message_text) VALUES (%s, %s)",
            (sender_username, message_text),
        )
        self.db_connection.commit()

    def kick_user(self):
        selected_user, ok = QInputDialog.getItem(
            self,
            "Kick User",
            "Sélectionnez le client connecté :",
            self.clients.keys(),
            0,
            False,
        )
        if ok:
            duration, ok = QInputDialog.getInt(
                self,
                "Kick Duration",
                "Entrez la durée du kick en secondes:",
                30,
                1,
                3600,
                1,
            )
            if ok:
                self.kick_duration = duration * 1000
                client_info = self.clients.get(selected_user)
                if client_info and not client_info["kicked"]:
                    client_socket = client_info["socket"]
                    kick_message = "Vous ne pouvez pas envoyer de messages avant un moment."
                    client_socket.send(kick_message.encode())
                    self.clients[selected_user]["kicked"] = True
                    self.kick_timer.singleShot(
                        self.kick_duration, lambda: self.unblock_user(selected_user)
                    )

    def unblock_user(self, username):
        if username in self.clients:
            self.clients[username]["kicked"] = False
            self.broadcast(f"{username} est autorisé à envoyer des messages.\n")

    def kick_timer_expired(self):
        self.kick_timer.stop()
        self.broadcast("Le temps d'expulsion est écoulé.\n")

    def disconnect_user(self, username):
        if username in self.clients:
            client_socket = self.clients[username]["socket"]
            client_socket.close()
            del self.clients[username]
            self.broadcast(
                f"{username} a été banni et déconnecté par le serveur.\n"
            )
            self.update_client_list()

    def broadcast(self, message):
        for client_info in self.clients.values():
            try:
                client_socket = client_info["socket"]
                if not client_info["kicked"] and not client_info["banned"]:
                    client_socket.send(message.encode())
            except socket.error:
                pass

    def print_message(self, message):
        self.text_edit.append(message)

    def update_client_list(self):
        client_list = ", ".join(
            client
            for client, info in self.clients.items()
            if not info["kicked"] and not info["banned"]
        )
        self.client_list_label.setText(f"Clients connectés: {client_list}")

    def ban_user(self):
        selected_user, ok = QInputDialog.getItem(
            self,
            "Ban User",
            "Sélectionnez le client :",
            self.clients.keys(),
            0,
            False,
        )
        if ok:
            duration, ok = QInputDialog.getInt(
                self,
                "Ban Duration",
                "Entrez la durée du ban en secondes:",

                3600000,

            )
            if ok:
                self.ban_duration = duration * 1000
                client_info = self.clients.get(selected_user)
                if client_info and not client_info["banned"]:
                    client_socket = client_info["socket"]
                    ban_message = "Vous avez été banni par le serveur."
                    client_socket.send(ban_message.encode())
                    self.clients[selected_user]["banned"] = True
                    self.ban_timer.singleShot(
                        self.ban_duration,
                        lambda: self.disconnect_user(selected_user),
                    )

    def ban_timer_expired(self):
        self.ban_timer.stop()
        self.broadcast("Le temps de bannissement est écoulé.\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Server()
    window.show()
    sys.exit(app.exec_())
