import os
import json
import mmap
import shutil
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pathlib import Path
from typing import Optional, List

class CertificateManager:
    """
    Handles certificate issuance, renewal, revocation, and configuration management for mTLS authentication,
    streamlining secure connections for external users.

    Uses shared memory to manage certificate metadata and configuration variables across concurrent processes.
    """

    SHARED_MEM_SIZE = 1024  # Define a fixed size for shared memory
    REQUIRED_VARS = ["common_name", "country_name", "validity_days"]

    def __init__(self, project_dir: str = "./ipncidr", shared_mem_file: str = "/dev/shm/cert_manager_shared"):
        """
        Initializes the CertificateManager with paths for the project directory and shared memory file.
        Creates the project directory if it does not exist.

        Args:
            project_dir (str): Path to the directory containing CA certificates and keys.
            shared_mem_file (str): Path to the shared memory file. Defaults to "/dev/shm/cert_manager_shared".
        """
        self.required_binaries = ["openssl"]
        self.project_dir = Path(project_dir)
        self.shared_mem_file = shared_mem_file
        self.ca_key = None
        self.ca_cert = None
        self.shared_memory = None

        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._load_shared_memory()
        self.ensure_vars()  # Ensures all required variables are set

        try:
            self.load_project_directory()
        except FileNotFoundError:
            print("CA certificate or key files missing; generating new CA.")
            self.create_ca()

    def set_project_dir(self, new_project_dir: str):
        """
        Sets a new project directory and initializes it if necessary.

        Args:
            new_project_dir (str): The new path for the project directory.
        """
        self.project_dir = Path(new_project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        print(f"Project directory set to: {self.project_dir}")

    def create_default_vars(self):
        """
        Creates a default `vars.json` file in the project directory with essential configuration variables.
        """
        default_vars = {
            "common_name": "Default CA",
            "country_name": "US",
            "validity_days": 365
        }
        vars_file = self.project_dir / "vars.json"
        
        with open(vars_file, "w") as f:
            json.dump(default_vars, f, indent=4)
        print(f"Default vars file created at: {vars_file}")

    def view_vars(self):
        """
        Prints all currently set configuration variables.
        """
        data = self._read_shared_memory()
        config = data.get("config", {})
        print("Current Configuration Variables:")
        for key, value in config.items():
            print(f"  {key}: {value}")

    def _load_shared_memory(self):
        """
        Loads or creates a shared memory file for certificate information access.

        Ensures the file is initialized to the fixed size and maps it to shared memory.
        """
        # Step 1: Create the file if it does not exist, and set the size
        with open(self.shared_mem_file, 'a+b') as f:
            f.seek(0, os.SEEK_END)
            current_size = f.tell()

            # Set the file size to SHARED_MEM_SIZE if it’s smaller than expected
            if current_size < self.SHARED_MEM_SIZE:
                f.truncate(self.SHARED_MEM_SIZE)

            # Initialize with default JSON structure if the file is empty
            if current_size == 0:
                initial_data = json.dumps({"certificates": [], "config": {}}).encode('utf-8')
                f.write(initial_data.ljust(self.SHARED_MEM_SIZE, b'\0'))
                f.flush()
        
        # Step 2: Map the file to shared memory
        with open(self.shared_mem_file, 'r+b') as f:
            self.shared_memory = mmap.mmap(f.fileno(), self.SHARED_MEM_SIZE)

    def _read_shared_memory(self):
        """
        Reads and decodes JSON data from the shared memory, stripping any padding.

        Returns:
            dict: The JSON data from shared memory.
        """
        self.shared_memory.seek(0)
        raw_data = self.shared_memory.read(self.SHARED_MEM_SIZE).rstrip(b'\0')
        return json.loads(raw_data.decode('utf-8'))

    def _write_shared_memory(self, data):
        """
        Encodes and writes JSON data to the shared memory, padding to fit the allocated size.

        Args:
            data (dict): The JSON-serializable data to write.
        """
        self.shared_memory.seek(0)
        json_data = json.dumps(data).encode('utf-8')
        padded_data = json_data.ljust(self.SHARED_MEM_SIZE, b'\0')
        self.shared_memory.write(padded_data)

    def ensure_vars(self):
        """
        Ensures that required configuration variables are set in shared memory. If any are missing,
        default values are set, or the user is prompted for input if no defaults are available.
        """
        data = self._read_shared_memory()
        config = data.get("config", {})

        for var in self.REQUIRED_VARS:
            if var not in config:
                # Set default values or prompt for user input if necessary
                if var == "common_name":
                    config[var] = "Default CA"
                elif var == "country_name":
                    config[var] = "US"
                elif var == "validity_days":
                    config[var] = 365  # Default to 1 year validity

        # Update shared memory with the ensured config
        data["config"] = config
        self._write_shared_memory(data)

    def get_var(self, key: str) -> Optional[str]:
        """
        Retrieves a configuration variable from shared memory.

        Args:
            key (str): The configuration key to retrieve.

        Returns:
            str or None: The value associated with the key, or None if not found.
        """
        data = self._read_shared_memory()
        return data.get("config", {}).get(key)

    def store_vars(self, key: str, value: str):
        """
        Stores a configuration variable in the shared memory file.

        Args:
            key (str): The configuration key.
            value (str): The value associated with the key.
        """
        data = self._read_shared_memory()
        data["config"][key] = value
        self._write_shared_memory(data)

    def load_project_directory(self):
        """
        Identifies and loads the CA certificates and keys from the specified project directory.

        Raises:
            FileNotFoundError: If CA certificate or key files are missing.
        """
        ca_key_files = list(self.project_dir.glob("ca.key"))
        ca_cert_files = list(self.project_dir.glob("ca.pem"))

        if ca_key_files and ca_cert_files:
            self.ca_key = ca_key_files[0]
            self.ca_cert = ca_cert_files[0]
        else:
            raise FileNotFoundError("CA certificate or key files missing in the project directory.")

    def create_ca(self, common_name: Optional[str] = None, country_name: Optional[str] = None, validity_days: Optional[int] = None):
        """
        Creates a new CA key and certificate for managing mTLS, prompting for any missing arguments.

        Args:
            common_name (str): Common Name (CN) for the CA certificate.
            country_name (str): Country Name (C) for the CA certificate.
            validity_days (int): Certificate validity in days. Default is 365 days.
        """
        # Prompt for missing arguments
        common_name = common_name or input("Enter the Common Name (CN) for the CA certificate [Default CA]: ") or "Default CA"
        country_name = country_name or input("Enter the Country Name (C) for the CA certificate [US]: ") or "US"
        validity_days = validity_days or int(input("Enter the validity period in days [365]: ") or "365")

        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_cert = self._generate_cert(ca_key, common_name, country_name, is_ca=True, validity_days=validity_days)

        ca_key_path = self.project_dir / "ca.key"
        ca_cert_path = self.project_dir / "ca.pem"

        with open(ca_key_path, "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(encoding=serialization.Encoding.PEM))

        self.ca_key = ca_key_path
        self.ca_cert = ca_cert_path

    def issue_certificate(self, common_name: Optional[str] = None, additional_hostnames: Optional[List[str]] = None, validity_days: Optional[int] = None):
        """
        Issues a certificate for a given common name, with optional hostnames and validity period.

        Args:
            common_name (str): Common Name (CN) for the certificate.
            additional_hostnames (List[str], optional): Additional DNS names for the certificate.
            validity_days (int): Certificate validity in days. Default is 365 days.

        Returns:
            str: Path to the issued certificate file.
        """
        # Prompt for missing arguments
        common_name = common_name or input("Enter the Common Name (CN) for the certificate: ")
        validity_days = validity_days or int(input("Enter the validity period in days [365]: ") or "365")
        
        # Additional hostnames are optional, but prompt if none provided
        if not additional_hostnames:
            hostnames = input("Enter additional DNS names, separated by commas, or press Enter to skip: ")
            additional_hostnames = [host.strip() for host in hostnames.split(",")] if hostnames else []

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert = self._generate_cert(
            key, common_name, "", additional_hostnames=additional_hostnames, validity_days=validity_days
        )

        cert_path = self.project_dir / f"{common_name}.pem"
        key_path = self.project_dir / f"{common_name}.key"

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(encoding=serialization.Encoding.PEM))

        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        self._update_shared_memory(cert_path)
        return str(cert_path)

    def _generate_cert(self, key, common_name, country_name, is_ca=False, additional_hostnames=None, validity_days=365):
        """
        Helper function to generate a certificate.

        Args:
            key (PrivateKey): Private key to sign the certificate.
            common_name (str): Common Name (CN) for the certificate.
            country_name (str): Country Name (C) for the certificate.
            is_ca (bool): If the certificate is a CA. Default is False.
            additional_hostnames (List[str], optional): Additional DNS names.
            validity_days (int): Certificate validity in days.

        Returns:
            x509.Certificate: Generated certificate object.
        """
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, country_name),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        builder = x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        builder = builder.serial_number(x509.random_serial_number()).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )

        if is_ca:
            builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)

        if additional_hostnames:
            san_list = [x509.DNSName(name) for name in additional_hostnames]
            builder = builder.add_extension(x509.SubjectAlternativeName(san_list), critical=False)

        return builder.sign(private_key=key, algorithm=hashes.SHA256())

    def _update_shared_memory(self, cert_path):
        """
        Updates the shared memory with new certificate information.

        Args:
            cert_path (str): Path to the certificate to add.
        """
        data = self._read_shared_memory()
        data["certificates"].append({"cert_path": cert_path, "issued": True})
        self._write_shared_memory(data)
