import paramiko
import logging
import time
import re

logging.basicConfig(level=logging.INFO)

class SSH_Connection_Handler:
    def __init__(self, hostname, username, password=None, pkey_path=None, port=22, jump_servers=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.pkey_path = pkey_path
        self.port = port
        self.jump_servers = jump_servers or []
        self.client = None
        self.jump_clients = []
        self.sudo_channel = None

    def _load_pkey(self):
        """Load the private key from the provided path if available."""
        if self.pkey_path:
            try:
                logging.info(f"Loading private key from {self.pkey_path}")
                return paramiko.RSAKey.from_private_key_file(self.pkey_path)
            except Exception as e:
                logging.error(f"Failed to load private key: {e}")
                return None
        return None

    def _connect_to_jump_server(self, jump_host, jump_user, jump_password, jump_port, sock):
        """Attempt connection to a single jump server."""
        jump_client = paramiko.SSHClient()
        jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logging.info(f"Attempting connection to jump server {jump_host} as {jump_user}")
        try:
            jump_client.connect(
                jump_host,
                username=jump_user,
                password=jump_password,
                port=jump_port,
                sock=sock,
                banner_timeout=30,
                auth_timeout=30
            )
            logging.info(f"Successfully connected to jump server {jump_host}")
            return jump_client
        except paramiko.AuthenticationException as auth_err:
            logging.error(f"Authentication failed for {jump_host}: {auth_err}")
            return None
        except Exception as e:
            logging.error(f"Error connecting to jump server {jump_host}: {e}")
            return None

    def _connect_jump_chain(self):
        """Establishes a chain of SSH connections through multiple jump servers."""
        sock = None
        for index, jump_server in enumerate(self.jump_servers):
            jump_host, jump_user, jump_password, jump_port = jump_server
            jump_client = self._connect_to_jump_server(jump_host, jump_user, jump_password, jump_port, sock)

            if jump_client is None:
                logging.error(f"Failed to connect to jump server {jump_host}. Stopping chain.")
                break

            self.jump_clients.append(jump_client)

            # Open a direct TCP connection to the next server in the chain
            target = (self.hostname, self.port) if index == len(self.jump_servers) - 1 else (self.jump_servers[index + 1][0], self.jump_servers[index + 1][3])
            logging.info(f"Setting up channel from {jump_host} to target {target}")

            try:
                sock = jump_client.get_transport().open_channel("direct-tcpip", target, ("127.0.0.1", 0))
            except Exception as e:
                logging.error(f"Failed to open channel from {jump_host} to {target}: {e}")
                break

        return sock

    def connect(self):
        """Establish the SSH connection through multiple jump servers and elevate to root with 'sudo su'."""
        try:
            sock = self._connect_jump_chain() if self.jump_servers else None

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.pkey_path:
                pkey = self._load_pkey()
                logging.info("Using private key authentication for final connection.")
                self.client.connect(
                    self.hostname,
                    username=self.username,
                    pkey=pkey,
                    sock=sock,
                    banner_timeout=30
                )
            else:
                logging.info("Using password authentication for final connection.")
                self.client.connect(
                    self.hostname,
                    username=self.username,
                    password=self.password,
                    sock=sock,
                    banner_timeout=30
                )
            logging.info("Connected successfully to the target server.")

            # Start a root session using `sudo su` and then `/bin/bash` for an interactive session
            self.sudo_channel = self.client.invoke_shell()
            time.sleep(1)
            self.sudo_channel.send("sudo su -\n")
            time.sleep(1)

            # Handle sudo password prompt if detected
            output = ""
            start_time = time.time()
            while time.time() - start_time < 10:
                if self.sudo_channel.recv_ready():
                    output += self.sudo_channel.recv(1024).decode()

                if "password" in output.lower():
                    logging.info("Password prompt detected, sending password.")
                    self.sudo_channel.send(self.password + "\n")
                    time.sleep(2)
                    output = self.sudo_channel.recv(1024).decode()

                time.sleep(1)

            # Confirm root elevation
            self.sudo_channel.send("whoami\n")
            time.sleep(1)
            whoami_output = self.sudo_channel.recv(1024).decode().strip()
            if "root" in whoami_output:
                logging.info("Confirmed elevation: running as root.")
                self.sudo_channel.send("/bin/bash\n")  # Start an actual bash shell
                time.sleep(1)
            else:
                logging.error("Failed to elevate to root.")
                self.disconnect()
                raise Exception("Failed to elevate to root.")

        except paramiko.AuthenticationException as e:
            logging.error(f"Authentication failed on final target server: {e}")
            self.disconnect()
            raise
        except Exception as e:
            logging.error(f"SSH connection failed: {e}")
            self.disconnect()
            raise

    def interactive_shell(self):
        """Provide a persistent interactive shell directly with /bin/bash on the remote server."""
        logging.info("Starting an interactive bash shell session on the target server.")
        ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])|(?:\[\d{2}:\d{2}:\d{2}\])|(?:[^\s]*\$)')

        try:
            while True:
                user_command = input("root@target# ")

                if user_command.lower() in ["exit", "quit"]:
                    logging.info("Exiting interactive shell.")
                    break

                self.sudo_channel.send(user_command + "\n")
                time.sleep(1)

                output = ""
                start_time = time.time()
                while time.time() - start_time < 10:
                    if self.sudo_channel.recv_ready():
                        output += self.sudo_channel.recv(4096).decode()
                    if output.endswith("# ") or output.endswith("$ "):
                        break
                    time.sleep(0.5)

                cleaned_output = "\n".join(
                    line for line in output.splitlines()
                    if not ansi_escape.search(line) and line.strip() != user_command
                ).strip()
                print(cleaned_output)

        except Exception as e:
            logging.error(f"Error during interactive shell session: {e}")

    def disconnect(self):
        """Close all SSH connections."""
        if self.client:
            self.client.close()
        for jump_client in self.jump_clients:
            jump_client.close()
        self.jump_clients = []

# Example usage
if __name__ == "__main__":
    checker = SSH_Connection_Handler(
        # Supports IPv4 and 6 addresses as well as FQDN/DNS
        hostname="target_ip(4|6) addresses supported",
        username="target_username",
        password="target_password",
        port=22,
        # Add more Jump Servers to the chain as needed
        # You can also use the path to your key in place of the passwd
        # ("5.6.7.8", "keyeduser","~/path/to/key.pem")
        jump_servers=[
            ("4.3.2.1", "myuserA", "BLAW!", 22),
            ("1.2.3.4", "myuserB", "BLAW!", 22)
        ]
    )
    checker.connect()
    try:
        checker.interactive_shell()
    finally:
        checker.disconnect()
