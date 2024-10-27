import os
import pwd
import subprocess
import zipfile
import logging
from pathlib import Path

## Configure logging for diagnostics
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SSHKeyManager:
    """
    A class to manage SSH key creation, signing, and packaging for users.

        Attributes:
            ca_key_path (str): Path to the CA signing key.
            download_dir (str): Directory where user packages are stored for download.
    """

    def __init__(self, ca_key_path, download_dir="downloads"):
        """
        Initialize the SSHKeyManager with a CA key and a download directory.

            Parameters:
                ca_key_path (str): Path to the CA key for signing SSH keys.
                download_dir (str): Path to the directory where user packages are stored for download.
        """
        self.ca_key_path = ca_key_path
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.user = user or pwd.getpwuid(os.getuid()).pw_name
        self.home_dir = pwd.getpwnam(self.user).pw_dir
        self.ssh_dir = os.path.join(self.home_dir, ".ssh")

    def generate_ssh_keypair(self, username):
        """
        Generate an SSH key pair for a user.

            Parameters:
                username (str): Username for whom the SSH key pair will be generated.

            Returns:
                dict: A dictionary with paths to the generated private and public keys.

            Raises:
                RuntimeError: If SSH key generation fails.
        """
        user_key_dir = self.download_dir / username
        user_key_dir.mkdir(exist_ok=True)
        private_key_path = user_key_dir / "id_rsa"
        public_key_path = private_key_path.with_suffix(".pub")

        try:
            subprocess.run(
                ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", str(private_key_path), "-N", ""],
                check=True
            )
            logging.info("Generated SSH key pair for %s", username)
            return {
                "private_key": private_key_path,
                "public_key": public_key_path
            }
        except subprocess.CalledProcessError as e:
            logging.error("Failed to generate SSH key pair: %s", e)
            raise RuntimeError("SSH key generation failed") from e

    def sign_ssh_key(self, public_key_path, username):
        """
        Sign an SSH public key for a user with the CA key.

            Parameters:
                public_key_path (Path): Path to the user's public key.
                username (str): Username for identification in the signed certificate.

            Returns:
                Path: Path to the signed public key.

            Raises:
                RuntimeError: If signing fails.
        """
        signed_key_path = public_key_path.with_name(f"{public_key_path.stem}-cert.pub")

        try:
            subprocess.run(
                ["ssh-keygen", "-s", self.ca_key_path, "-I", username, "-n", username, "-V", "+52w", "-z", "1", "-f", str(signed_key_path), str(public_key_path)],
                check=True
            )
            logging.info("Signed SSH key for %s", username)
            return signed_key_path
        except subprocess.CalledProcessError as e:
            logging.error("Failed to sign SSH key: %s", e)
            raise RuntimeError("SSH key signing failed") from e

    def create_user_package(self, username):
        """
        Create a zip package containing the SSH keys for a user.

            Parameters:
                username (str): Username whose package will be created.

            Returns:
                Path: Path to the created ZIP package.

            Raises:
                RuntimeError: If zipping fails.
        """
        user_key_dir = self.download_dir / username
        zip_path = self.download_dir / f"{username}_ssh_keys.zip"

        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file in user_key_dir.iterdir():
                    zipf.write(file, arcname=file.name)
            logging.info("Created ZIP package for %s", username)
            return zip_path
        except Exception as e:
            logging.error("Failed to create ZIP package: %s", e)
            raise RuntimeError("ZIP package creation failed") from e

    def _run_ipset_cmd(self, cmd):
        """
        Run an ipset command.

            Parameters:
                - cmd (list): List of command arguments for ipset.

                Raises:
                    - RuntimeError: If the ipset command fails.

                Example:
                    self._run_ipset_cmd(["add", "my_ipset_group", "192.168.1.1"])
        """
        try:
            subprocess.run(["ipset"] + cmd, check=True)
            logging.info("Successfully ran ipset command: %s", cmd)
        except subprocess.CalledProcessError as e:
            logging.error("ipset command failed: %s", e)
            raise RuntimeError("ipset command failed") from e

    def manage_user_package(self, username):
        """
        Generate, sign, and package SSH keys for a user.

            Parameters:
                username (str): Username to create and package SSH keys for.

            Returns:
                Path: Path to the final ZIP package for download.
        """
        key_paths = self.generate_ssh_keypair(username)
        self.sign_ssh_key(key_paths['public_key'], username)
        zip_path = self.create_user_package(username)
        logging.info("User package for %s is ready at %s", username, zip_path)
        return zip_path


    def show_known_hosts(self):
        """
        Display the known hosts file for the user.

            Returns:
                - str: Contents of the known_hosts file.
        """
        known_hosts_path = os.path.join(self.ssh_dir, "known_hosts")
        return self._read_file(known_hosts_path, "known_hosts")

    def show_private_and_public_keys(self):
        """
        Display the private and public SSH keys for the user.

            Returns:
                - dict: Dictionary containing private and public keys and their content.
        """
        keys = {}
        for file_name in os.listdir(self.ssh_dir):
            if file_name.endswith(".pub"):  # Public key
                keys[file_name] = self._read_file(os.path.join(self.ssh_dir, file_name), file_name)
            elif "id_" in file_name:  # Private key (commonly named "id_rsa", "id_ecdsa", etc.)
                keys[file_name] = self._read_file(os.path.join(self.ssh_dir, file_name), file_name)
        return keys

    def show_authorized_keys(self):
        """
        Display the authorized_keys file for the user.

            Returns:
                - str: Contents of the authorized_keys file.
        """
        authorized_keys_path = os.path.join(self.ssh_dir, "authorized_keys")
        return self._read_file(authorized_keys_path, "authorized_keys")

    def _read_file(self, file_path, description):
        """
        Helper function to read a file and handle errors if the file does not exist.

            Parameters:
                - file_path (str): Path of the file to read.
                - description (str): Description of the file for error messages.

            Returns:
                - str: Contents of the file or error message if file not found.
        """
        try:
            with open(file_path, "r") as file:
                return file.read()
        except FileNotFoundError:
            return f"{description.capitalize()} file not found for user '{self.user}' at {file_path}."

'''
# Example Usage
ssh_manager = SSHManager()  # For current user
print("Known Hosts:")
print(ssh_manager.show_known_hosts())

print("\nPrivate and Public Keys:")
print(ssh_manager.show_private_and_public_keys())

print("\nAuthorized Keys:")
print(ssh_manager.show_authorized_keys())

# For a specific user
ssh_manager = SSHManager(user="someuser")
print("\nAuthorized Keys for specific user:")
print(ssh_manager.show_authorized_keys())



# Example usage:
manager = SSHKeyManager(ca_key_path="/path/to/ca_key")
package_path = manager.manage_user_package("testuser")
print(f"Package ready for download: {package_path}")
'''
