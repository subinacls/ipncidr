import subprocess
import os

class WireGuardManager:
    """
    A class to handle the administration, configuration, and management of WireGuard servers.
    Supports creating interfaces, configuring peers, generating configurations, and starting/stopping
    the WireGuard service with direct 'wg' commands.
    """

    def __init__(self):
        """
        Initializes the WireGuardManager class with default values. 
        No arguments are required at initialization.
        """
        self.interface_name = "wg0"
        self.default_config_path = "/etc/wireguard"
        self.peers = []

    def edit_arguments(self, method_name):
        """
        Interactive prompt to edit method arguments.
        
        Parameters:
            method_name (str): The name of the method whose arguments are being edited.
        """
        method = getattr(self, method_name)
        arg_spec = method.__annotations__
        args = {arg: getattr(self, arg, None) for arg in arg_spec}
        
        while True:
            print("\nArgument Table:")
            for i, (arg, arg_type) in enumerate(arg_spec.items(), 1):
                print(f"{i}    {arg:15} {arg_type.__name__:10} {args[arg]}")
            choice = input("\nSelect an argument by number to edit, or enter '99' to finish: ")
            if choice == "99":
                break
            try:
                arg = list(arg_spec.keys())[int(choice) - 1]
                value = input(f"Enter new value for {arg} ({arg_spec[arg].__name__}): ")
                args[arg] = value
            except (IndexError, ValueError):
                print("Invalid selection. Please try again.")
        
        # Apply changes to the instance variables
        for arg, value in args.items():
            setattr(self, arg, value)

    def create_interface(self, name: str = "wg0"):
        """
        Creates a WireGuard interface using the specified name and generates configuration.
        
        Parameters:
            name (str): The name of the WireGuard interface. Defaults to 'wg0'.
        """
        self.interface_name = name
        config_path = os.path.join(self.default_config_path, f"{self.interface_name}.conf")
        
        # Generate interface configuration file if it doesn't exist
        if not os.path.exists(config_path):
            self.generate_configuration(config_path=config_path)
        
        subprocess.run(["wg", "setconf", self.interface_name, config_path], check=True)

    def configure_peer(self, public_key: str, allowed_ips: str, endpoint: str = None, persistent_keepalive: int = 25):
        """
        Configures a peer with the specified details.
        
        Parameters:
            public_key (str): The public key of the peer.
            allowed_ips (str): The IP range that this peer is allowed to use.
            endpoint (str, optional): The endpoint address for the peer. Defaults to None.
            persistent_keepalive (int, optional): Keepalive interval in seconds. Defaults to 25.
        """
        peer = {
            "public_key": public_key,
            "allowed_ips": allowed_ips,
            "endpoint": endpoint,
            "persistent_keepalive": persistent_keepalive
        }
        self.peers.append(peer)
        self._update_configuration()

    def _update_configuration(self):
        """
        Updates the WireGuard configuration file based on the current peer list.
        """
        config_content = f"[Interface]\nPrivateKey = {self._get_private_key()}\nAddress = 10.0.0.1/24\n\n"
        for peer in self.peers:
            config_content += f"[Peer]\nPublicKey = {peer['public_key']}\nAllowedIPs = {peer['allowed_ips']}\n"
            if peer["endpoint"]:
                config_content += f"Endpoint = {peer['endpoint']}\n"
            config_content += f"PersistentKeepalive = {peer['persistent_keepalive']}\n\n"
        
        config_path = os.path.join(self.default_config_path, f"{self.interface_name}.conf")
        with open(config_path, "w") as config_file:
            config_file.write(config_content)

    def start_service(self):
        """
        Brings up the WireGuard interface using the current configuration.
        """
        config_path = os.path.join(self.default_config_path, f"{self.interface_name}.conf")
        subprocess.run(["wg", "setconf", self.interface_name, config_path], check=True)

    def stop_service(self):
        """
        Brings down the WireGuard interface by removing the configuration.
        """
        subprocess.run(["ip", "link", "del", self.interface_name], check=True)

    def list_peers(self):
        """
        Lists all configured peers for the WireGuard interface.
        
        Returns:
            list: A list of configured peers.
        """
        result = subprocess.run(["wg", "show", self.interface_name], capture_output=True, text=True)
        return result.stdout.splitlines()

    def delete_peer(self, public_key):
        """
        Deletes a peer from the WireGuard configuration.
        
        Parameters:
            public_key (str): The public key of the peer to be deleted.
        """
        self.peers = [peer for peer in self.peers if peer["public_key"] != public_key]
        self._update_configuration()

    def generate_configuration(self, config_path=None):
        """
        Generates a WireGuard configuration file at the specified path.
        
        Parameters:
            config_path (str, optional): The path to save the configuration file. 
                                         Defaults to the class's default configuration path.
        """
        config_path = config_path or self.default_config_path
        self._update_configuration()

    def get_status(self):
        """
        Retrieves the current status of the WireGuard interface.
        
        Returns:
            str: The status output of the WireGuard interface.
        """
        result = subprocess.run(["wg", "show", self.interface_name], capture_output=True, text=True)
        return result.stdout

    def _get_private_key(self):
        """
        Retrieves the server's private key.
        
        Returns:
            str: The server's private key.
        """
        private_key_path = os.path.join(self.default_config_path, f"{self.interface_name}.key")
        if not os.path.exists(private_key_path):
            result = subprocess.run(["wg", "genkey"], capture_output=True, text=True)
            with open(private_key_path, "w") as key_file:
                key_file.write(result.stdout.strip())
        with open(private_key_path, "r") as key_file:
            return key_file.read().strip()
