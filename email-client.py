import socket
import json
import os
import bcrypt
import time
import sys
from datetime import datetime


class EmailClient:
    def __init__(self):
        self.server_host = None
        self.server_port = None
        self.socket = None
        self.current_user = None
        self.current_user_name = None

    def clear_screen(self):
        """Limpa a tela do terminal"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def hash_password(self, password):
        """Gera hash da senha usando bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def connect_to_server(self):
        """Conecta ao servidor de email"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            print(f"Erro ao conectar com o servidor: {e}")
            return False

    def send_request(self, request_data):
        """Envia uma solicitação ao servidor e recebe a resposta"""
        try:
            if not self.socket:
                if not self.connect_to_server():
                    return {'status': 'error', 'message': 'Não foi possível conectar ao servidor'}

            # Envia solicitação
            self.socket.send(json.dumps(request_data).encode('utf-8'))

            # Recebe resposta
            response = self.socket.recv(8192)
            return json.loads(response.decode('utf-8'))
        except Exception as e:
            print(f"Erro na comunicação com o servidor: {e}")
            # Tenta reconectar
            self.socket = None
            return {'status': 'error', 'message': f'Erro na comunicação: {e}'}

    def check_server_connection(self):
        """Verifica se o servidor está disponível"""
        return self.send_request({'operation': 'check_connection'})

    def register_user(self):
        """Registra um novo usuário no serviço de email"""
        self.clear_screen()
        print("===== CADASTRO DE NOVA CONTA =====")

        nome = input("Nome completo: ")
        while not nome:
            print("Nome é obrigatório!")
            nome = input("Nome completo: ")

        username = input("Nome de usuário (sem espaços): ")
        while not username or ' ' in username:
            print("Nome de usuário inválido!")
            username = input("Nome de usuário (sem espaços): ")

        senha = input("Senha: ")
        while not senha:
            print("Senha é obrigatória!")
            senha = input("Senha: ")

        # Envia solicitação de registro para o servidor
        response = self.send_request({
            'operation': 'register',
            'nome': nome,
            'username': username,
            'senha': senha
        })

        print(f"\n{response['message']}")
        input("\nPressione Enter para continuar...")

    def login(self):
        """Realiza login no serviço de email"""
        self.clear_screen()
        print("===== LOGIN =====")

        username = input("Nome de usuário: ")
        senha = input("Senha: ")

        # Envia solicitação de login para o servidor
        response = self.send_request({
            'operation': 'login',
            'username': username,
            'senha': senha
        })

        if response['status'] == 'success':
            self.current_user = username
            self.current_user_name = response['nome']
            return True
        else:
            print(f"\n{response['message']}")
            input("\nPressione Enter para continuar...")
            return False

    def logout(self):
        """Realiza logout do serviço de email"""
        response = self.send_request({'operation': 'logout'})
        self.current_user = None
        self.current_user_name = None
        print(f"\n{response['message']}")
        input("\nPressione Enter para continuar...")

    def send_email(self):
        """Envia um novo email"""
        self.clear_screen()
        print("===== ENVIAR E-MAIL =====")

        destinatario = input("Destinatário (username): ")
        assunto = input("Assunto: ")
        print("Corpo do e-mail (termine com uma linha contendo apenas '.'): ")

        lines = []
        while True:
            line = input()
            if line == '.':
                break
            lines.append(line)

        corpo = '\n'.join(lines)

        # Envia solicitação para enviar email
        response = self.send_request({
            'operation': 'send_email',
            'destinatario': destinatario,
            'assunto': assunto,
            'corpo': corpo
        })

        print(f"\n{response['message']}")
        input("\nPressione Enter para continuar...")

    def receive_emails(self):
        """Recebe emails da caixa de entrada"""
        self.clear_screen()
        print("===== RECEBER E-MAILS =====")
        print("Recebendo E-mails...")

        # Solicita emails ao servidor
        response = self.send_request({'operation': 'receive_emails'})

        if response['status'] == 'success':
            emails = response.get('emails', [])
            count = len(emails)

            print(f"{count} e-mails recebidos:")

            if count > 0:
                # Exibe lista de emails
                for i, email in enumerate(emails, 1):
                    print(f"[{i}] {email['remetente_nome']}: {email['assunto']}")

                # Permite leitura de um email específico
                try:
                    choice = int(
                        input("\nQual e-mail deseja ler (0 para voltar): "))
                    if 1 <= choice <= count:
                        email = emails[choice-1]
                        self.clear_screen()
                        print("=" * 50)
                        print(
                            f"De: {email['remetente_nome']} ({email['remetente']})")
                        print(f"Para: {self.current_user}")
                        print(f"Data/Hora: {email['data_hora']}")
                        print(f"Assunto: {email['assunto']}")
                        print("=" * 50)
                        print(f"\n{email['corpo']}")
                        print("\n" + "=" * 50)
                except ValueError:
                    pass
        else:
            print(f"Erro: {response['message']}")

        input("\nPressione Enter para continuar...")

    def configure_server(self):
        """Configura o endereço e porta do servidor"""
        self.clear_screen()
        print("===== CONFIGURAR SERVIDOR =====")

        self.server_host = input(
            "Endereço IP do servidor [default: localhost]: ") or "localhost"

        try:
            port = input("Porta do servidor [default: 8080]: ") or "8080"
            self.server_port = int(port)
        except ValueError:
            self.server_port = 8080
            print("Porta inválida. Usando porta 8080.")

        # Testa a conexão com o servidor
        print("\nTestando conexão...")
        response = self.check_server_connection()

        if response['status'] == 'success':
            print(f"Status: {response['message']}")
        else:
            print(f"Erro: {response['message']}")

        input("\nPressione Enter para continuar...")

    def main_menu(self):
        """Exibe o menu principal do cliente"""
        self.clear_screen()
        print("===== Cliente E-mail Service BSI Online =====")
        print("1) Apontar Servidor")

        # Habilita outras opções apenas se o servidor estiver configurado
        if self.server_host and self.server_port:
            print("2) Cadastrar Conta")
            print("3) Acessar E-mail")

        print("0) Sair")

        choice = input("\nEscolha uma opção: ")

        if choice == '1':
            self.configure_server()
        elif choice == '2' and self.server_host and self.server_port:
            self.register_user()
        elif choice == '3' and self.server_host and self.server_port:
            if self.login():
                self.logged_in_menu()
        elif choice == '0':
            print("Encerrando o programa...")
            if self.socket:
                self.socket.close()
            sys.exit(0)
        else:
            print("Opção inválida!")
            time.sleep(1)

    def logged_in_menu(self):
        """Exibe o menu de usuário logado"""
        while self.current_user:
            self.clear_screen()
            print(f"Seja Bem Vindo {self.current_user_name}")
            print("4) Enviar E-mail")
            print("5) Receber E-mails")
            print("6) Logout")
            print("0) Sair")

            choice = input("\nEscolha uma opção: ")

            if choice == '4':
                self.send_email()
            elif choice == '5':
                self.receive_emails()
            elif choice == '6':
                self.logout()
                break
            elif choice == '0':
                print("Encerrando o programa...")
                if self.socket:
                    self.socket.close()
                sys.exit(0)
            else:
                print("Opção inválida!")
                time.sleep(1)

    def run(self):
        """Inicia a execução do cliente de email"""
        try:
            while True:
                self.main_menu()
        except KeyboardInterrupt:
            print("\nEncerrando o programa...")
            if self.socket:
                self.socket.close()
            sys.exit(0)


if __name__ == "__main__":
    client = EmailClient()
    client.run()
