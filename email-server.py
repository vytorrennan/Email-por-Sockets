import socket
import threading
import json
import time
import bcrypt
import os
from datetime import datetime


class EmailServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.users = {}  # Armazena informações dos usuários: {username: {'nome': str, 'senha': str}}
        self.emails = {}  # Armazena emails: {username_destinatario: [emails]}
        self.running = False
        self.lock = threading.Lock()

    def hash_password(self, password):
        """Gera hash da senha usando bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def start(self):
        """Inicia o servidor de email"""
        try:
            self.server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[INFO] Servidor iniciado em {self.host}:{self.port}")

            while self.running:
                client_socket, client_address = self.server_socket.accept()
                print(
                    f"[INFO] Nova conexão de {client_address[0]}:{client_address[1]}")

                # Inicia uma nova thread para lidar com o cliente
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()

        except Exception as e:
            print(f"[ERRO] Falha ao iniciar o servidor: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
                print("[INFO] Servidor encerrado")

    def handle_client(self, client_socket, client_address):
        """Gerencia a comunicação com um cliente específico"""
        client_username = None
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break

                request = json.loads(data.decode('utf-8'))
                operation = request.get('operation')
                response = {'status': 'error',
                            'message': 'Operação desconhecida'}

                # Log da operação recebida
                print(
                    f"[INFO] Operação recebida de {client_address[0]}:{client_address[1]} - {operation}")

                if operation == 'check_connection':
                    response = {'status': 'success',
                                'message': 'Serviço Disponível'}

                elif operation == 'register':
                    response = self.register_user(request.get(
                        'nome'), request.get('username'), request.get('senha'))

                elif operation == 'login':
                    result, nome = self.authenticate_user(
                        request.get('username'), request.get('senha'))
                    if result:
                        client_username = request.get('username')
                        response = {
                            'status': 'success', 'message': 'Login realizado com sucesso', 'nome': nome}
                    else:
                        response = {'status': 'error',
                                    'message': 'Credenciais inválidas'}

                elif operation == 'send_email':
                    if client_username:
                        response = self.send_email(
                            client_username,
                            request.get('destinatario'),
                            request.get('assunto'),
                            request.get('corpo')
                        )
                    else:
                        response = {'status': 'error',
                                    'message': 'Usuário não autenticado'}

                elif operation == 'receive_emails':
                    if client_username:
                        emails, response = self.get_emails(client_username)
                        response['emails'] = emails
                    else:
                        response = {'status': 'error',
                                    'message': 'Usuário não autenticado'}

                elif operation == 'logout':
                    client_username = None
                    response = {'status': 'success',
                                'message': 'Logout realizado com sucesso'}

                # Envia a resposta ao cliente
                client_socket.send(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(
                f"[ERRO] Erro ao processar solicitação do cliente {client_address}: {e}")
        finally:
            print(
                f"[INFO] Conexão encerrada com {client_address[0]}:{client_address[1]}")
            client_socket.close()

    def register_user(self, nome, username, senha):
        """Registra um novo usuário no sistema"""
        with self.lock:
            if not username or not nome or not senha:
                return {'status': 'error', 'message': 'Todos os campos são obrigatórios'}

            if username in self.users:
                return {'status': 'error', 'message': 'Nome de usuário já existe'}

            # Armazena o novo usuário
            hashed_password = self.hash_password(senha)
            self.users[username] = {'nome': nome, 'senha': hashed_password}
            self.emails[username] = []  # Inicializa a caixa de entrada vazia

            print(f"[INFO] Novo usuário registrado: {username} ({nome})")
            return {'status': 'success', 'message': 'Usuário registrado com sucesso'}

    def authenticate_user(self, username, senha):
        """Autentica um usuário usando bcrypt"""
        with self.lock:
            if username not in self.users:
                return False, None

            stored_user = self.users[username]
            # Verifica se a senha corresponde ao hash armazenado
            if bcrypt.checkpw(senha.encode('utf-8'), stored_user['senha'].encode('utf-8')):
                print(f"[INFO] Login bem-sucedido: {username}")
                return True, stored_user['nome']
            else:
                print(f"[INFO] Tentativa de login falhou: {username}")
                return False, None

    def send_email(self, remetente, destinatario, assunto, corpo):
        """Envia um email de um usuário para outro"""
        with self.lock:
            # Verifica se o destinatário existe
            if destinatario not in self.users:
                return {'status': 'error', 'message': 'Destinatário Inexistente'}

            # Cria o email
            email = {
                'remetente': remetente,
                'remetente_nome': self.users[remetente]['nome'],
                'destinatario': destinatario,
                'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                'assunto': assunto,
                'corpo': corpo
            }

            # Adiciona à caixa de entrada do destinatário
            self.emails[destinatario].append(email)

            print(
                f"[INFO] E-mail enviado: De {remetente} para {destinatario} - Assunto: {assunto}")
            return {'status': 'success', 'message': 'E-mail enviado com sucesso'}

    def get_emails(self, username):
        """Recupera e remove emails da caixa de entrada de um usuário"""
        with self.lock:
            if username not in self.emails:
                return [], {'status': 'success', 'message': '0 e-mails recebidos'}

            # Recupera os emails
            user_emails = self.emails[username]
            count = len(user_emails)

            # Limpa a caixa de entrada após recuperação
            self.emails[username] = []

            print(f"[INFO] {count} e-mails entregues para {username}")
            return user_emails, {'status': 'success', 'message': f'{count} e-mails recebidos'}

    def stop(self):
        """Encerra o servidor"""
        self.running = False
        # Criando uma conexão para desbloquear accept()
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
                (self.host, self.port))
        except:
            pass


if __name__ == "__main__":
    # Solicitar configurações do servidor
    host = input(
        "Endereço IP do servidor [default: localhost]: ") or "localhost"
    try:
        port = int(input("Porta do servidor [default: 8080]: ") or "8080")
    except ValueError:
        port = 8080
        print("Porta inválida. Usando porta 8080.")

    server = EmailServer(host, port)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INFO] Encerrando servidor...")
        server.stop()
