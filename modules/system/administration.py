import subprocess
import shutil
import logging
import json
import core.shared as shared

class SystemManager:
    """
    The SystemManager class provides common Linux system management functionalities,
    such as checking the existence of binaries, executing commands, and
    handling default values and recommendations for common administrative actions.

    Attributes:
    ----------
    binary_locations : dict
        A dictionary storing the paths of verified binaries on the system.

    Methods:
    -------
    check_binary(binary_name)
        Checks if a binary exists on the system and stores its location.
        
    execute_command(command, args=None)
        Executes a command with optional arguments.
        
    show_netstat(options="-tuln")
        Displays network status information using netstat.
        
    recommend_command(usage_type="network")
        Recommends commands based on the specified usage type.

    save_binary_locations()
        Persists binary locations to the shared storage file.
        
    load_binary_locations()
        Loads binary locations from shared storage if available.
        
    show_disk_mounts()
        Shows the mounted disk partitions on the system.
        
    add_mount(device, mount_point, options=None)
        Adds a mount for a specified device to a mount point with optional mount options.
        
    show_interfaces()
        Displays network interfaces and their configurations.
        
    show_dmesg()
        Displays the kernel ring buffer messages.
        
    manage_service(service_name, action)
        Manages system services using systemctl with actions: start, stop, restart, or status.
        
    ... (other functions) ...
    """

    def __init__(self):
        """
        Initializes the SystemManager class with binary location dictionary.
        Loads previously saved binary locations if available.
        """
        self.binary_locations = {}
        self.load_binary_locations()
        logging.info("SystemManager initialized and binary locations loaded.")

    def check_binary(self, binary_name):
        """
        Checks if the specified binary exists on the system. If found,
        records the binary's path in binary_locations dictionary.
        """
        binary_path = shutil.which(binary_name)
        if binary_path:
            self.binary_locations[binary_name] = binary_path
            self.save_binary_locations()
            logging.info(f"{binary_name} found at {binary_path}")
            return True
        logging.warning(f"{binary_name} not found on the system.")
        return False

    def execute_command(self, command, args=None):
        """
        Executes a specified command with optional arguments if the binary exists.
        """
        if command not in self.binary_locations:
            if not self.check_binary(command):
                return f"Error: {command} binary not found."
        
        cmd = [self.binary_locations[command]] + (args if args else [])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logging.info(f"Executed command: {' '.join(cmd)}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Command execution failed: {e}")
            return f"Error executing command: {e}"






    def update_apt_repos(self):
        """
        Updates the APT repositories and fetches available packages list,
        storing it as a local JSON database for quick package lookup.

        Returns:
        -------
        str
            Confirmation message on successful update, or an error message.
        """
        if not self.check_binary("apt-cache"):
            return "APT cache management not available on this system."

        try:
            # Step 1: Update the APT repositories
            update_result = subprocess.run(["apt", "update"], capture_output=True, text=True, check=True)
            logging.info("APT repositories updated successfully.")
            
            # Step 2: Fetch available packages
            package_list_result = subprocess.run(
                ["apt-cache", "search", "."], capture_output=True, text=True, check=True
            )
            logging.info("Fetched package list from APT cache.")

            # Step 3: Parse the package list and create a lookup table
            packages = {}
            for line in package_list_result.stdout.splitlines():
                package_info = line.split(" - ", 1)
                if len(package_info) == 2:
                    package_name, description = package_info
                    packages[package_name.strip()] = description.strip()

            # Save the lookup table to the shared module's local database
            shared.save_data("apt_package_lookup", packages)
            logging.info("APT package lookup table created and stored.")

            return "APT repositories updated, and package lookup table created successfully."

        except subprocess.CalledProcessError as e:
            logging.error(f"Error updating APT repositories or fetching package list: {e}")
            return f"Error: {e}"

    def search_package_lookup(self, package_name):
        """
        Searches the locally stored APT package lookup table for a specified package.

        Parameters:
        ----------
        package_name : str
            The name of the package to search for.

        Returns:
        -------
        dict or str
            Information about the package if found, or a not found message.
        """
        # Load the local package lookup table from shared storage
        packages = shared.load_data("apt_package_lookup")
        
        if not packages:
            return "Package lookup table not available. Please update the APT repository first."

        # Search for the package in the lookup table
        if package_name in packages:
            return {package_name: packages[package_name]}
        else:
            return f"Package '{package_name}' not found in the lookup table."







    def create_user(self, username, options=None):
        """
        Creates a new user on the system with optional parameters.

        Parameters:
        ----------
        username : str
            The username to create.
        options : str, optional
            Additional options for user creation (default is None).
        """
        args = [username]
        if options:
            args.insert(0, options)
        return self.execute_command("useradd", args)

    def delete_user(self, username, remove_home=False):
        """
        Deletes a user from the system, optionally removing their home directory.

        Parameters:
        ----------
        username : str
            The username to delete.
        remove_home : bool, optional
            Whether to remove the user's home directory (default is False).
        """
        args = [username]
        if remove_home:
            args.insert(0, "-r")
        return self.execute_command("userdel", args)

    def add_user_to_group(self, username, group):
        """
        Adds an existing user to a specified group.

        Parameters:
        ----------
        username : str
            The username to add to the group.
        group : str
            The group to add the user to.
        """
        return self.execute_command("usermod", ["-aG", group, username])

    def show_installed_packages(self):
        """
        Lists all installed packages on the system.
        """
        if self.check_binary("dpkg"):
            return self.execute_command("dpkg", ["-l"])
        elif self.check_binary("rpm"):
            return self.execute_command("rpm", ["-qa"])
        else:
            return "Package manager not found."

    def install_package(self, package_name):
        """
        Installs a package using the available package manager (apt or yum).

        Parameters:
        ----------
        package_name : str
            The name of the package to install.
        """
        if self.check_binary("apt"):
            return self.execute_command("apt", ["install", package_name, "-y"])
        elif self.check_binary("yum"):
            return self.execute_command("yum", ["install", package_name, "-y"])
        else:
            return "Package manager not found."

    def remove_package(self, package_name):
        """
        Removes a package using the available package manager (apt or yum).

        Parameters:
        ----------
        package_name : str
            The name of the package to remove.
        """
        if self.check_binary("apt"):
            return self.execute_command("apt", ["remove", package_name, "-y"])
        elif self.check_binary("yum"):
            return self.execute_command("yum", ["remove", package_name, "-y"])
        else:
            return "Package manager not found."

    def show_system_info(self):
        """
        Displays basic system information using the 'uname' command.
        """
        return self.execute_command("uname", ["-a"])

    def show_cpu_info(self):
        """
        Shows detailed CPU information.
        """
        return self.execute_command("lscpu")

    def show_memory_info(self):
        """
        Displays detailed memory information.
        """
        return self.execute_command("cat", ["/proc/meminfo"])

    def show_disk_partitions(self):
        """
        Lists disk partitions and their details.
        """
        return self.execute_command("lsblk")

    def update_system(self):
        """
        Updates the system packages using apt or yum.
        """
        if self.check_binary("apt"):
            return self.execute_command("apt", ["update", "-y"])
        elif self.check_binary("yum"):
            return self.execute_command("yum", ["update", "-y"])
        else:
            return "Package manager not found."

    def reboot_system(self):
        """
        Reboots the system.
        """
        return self.execute_command("reboot")

    def shutdown_system(self, delay="now"):
        """
        Shuts down the system, with an optional delay.

        Parameters:
        ----------
        delay : str, optional
            Delay time for shutdown (default is 'now').
        """
        return self.execute_command("shutdown", [delay])

    def view_crontab(self, user=None):
        """
        Displays the crontab for a specific user or the current user.

        Parameters:
        ----------
        user : str, optional
            The user whose crontab to display (default is current user).
        """
        args = ["-l"]
        if user:
            args.extend(["-u", user])
        return self.execute_command("crontab", args)

    def edit_crontab(self, user=None, cron_entry=None):
        """
        Edits the crontab for a specified user, adding a new cron entry if provided.

        Parameters:
        ----------
        user : str, optional
            The user whose crontab to edit (default is current user).
        cron_entry : str, optional
            The cron job entry to add (default is None).
        """
        if cron_entry:
            cmd = f"(crontab -l 2>/dev/null; echo \"{cron_entry}\") | crontab -"
            if user:
                cmd += f" -u {user}"
            return self.execute_command("sh", ["-c", cmd])
        else:
            args = ["-e"]
            if user:
                args.extend(["-u", user])
            return self.execute_command("crontab", args)

    def check_open_ports(self):
        """
        Checks for open ports on the system using 'ss'.
        """
        return self.execute_command("ss", ["-tuln"])

    def configure_firewall_rule(self, rule):
        """
        Configures a firewall rule using iptables or firewall-cmd.

        Parameters:
        ----------
        rule : str
            The firewall rule to configure.
        """
        if self.check_binary("iptables"):
            return self.execute_command("iptables", rule.split())
        elif self.check_binary("firewall-cmd"):
            return self.execute_command("firewall-cmd", ["--permanent"] + rule.split())
        else:
            return "Firewall management tool not found."







    def show_disk_mounts(self):
        """
        Displays the mounted disk partitions on the system using the 'df' command.
        """
        return self.execute_command("df", ["-h"])

    def add_mount(self, device, mount_point, options=None):
        """
        Mounts a specified device to a given mount point with optional mount options.
        """
        args = ["-o", options] if options else []
        args.extend([device, mount_point])
        return self.execute_command("mount", args)

    def show_interfaces(self):
        """
        Displays the network interfaces and configurations using 'ip addr' command.
        """
        return self.execute_command("ip", ["addr"])

    def show_dmesg(self):
        """
        Displays the kernel ring buffer messages using 'dmesg' command.
        """
        return self.execute_command("dmesg", ["-T"])

    def manage_service(self, service_name, action="status"):
        """
        Manages system services using systemctl.
        
        Parameters:
        ----------
        service_name : str
            The name of the service to manage.
        action : str, optional
            The action to perform on the service (start, stop, restart, status).
        """
        valid_actions = {"start", "stop", "restart", "status"}
        if action not in valid_actions:
            return f"Invalid action. Choose from {valid_actions}"
        return self.execute_command("systemctl", [action, service_name])

    def show_system_logs(self, journalctl_options="-xe"):
        """
        Displays system logs using 'journalctl' with default options.

        Parameters:
        ----------
        journalctl_options : str, optional
            Options for the journalctl command (default is "-xe").
        """
        return self.execute_command("journalctl", [journalctl_options])

    def check_disk_usage(self, path="/"):
        """
        Checks disk usage for a specified path using 'du' command.
        
        Parameters:
        ----------
        path : str, optional
            The directory path to check disk usage (default is "/").
        """
        return self.execute_command("du", ["-sh", path])

    def list_directory_contents(self, directory="/"):
        """
        Lists the contents of a specified directory.
        
        Parameters:
        ----------
        directory : str, optional
            The directory path to list contents (default is root "/").
        """
        return self.execute_command("ls", ["-l", directory])

    def show_memory_usage(self):
        """
        Displays memory usage statistics using 'free' command.
        """
        return self.execute_command("free", ["-h"])

    def system_uptime(self):
        """
        Shows system uptime information.
        """
        return self.execute_command("uptime")

    def show_process_tree(self):
        """
        Displays a hierarchical tree of processes using 'pstree'.
        """
        return self.execute_command("pstree", ["-p"])

    def save_binary_locations(self):
        """
        Saves the binary locations to persistent storage using shared module.
        """
        shared.save_data("binary_locations", self.binary_locations)
        logging.info("Binary locations saved to shared storage.")

    def load_binary_locations(self):
        """
        Loads binary locations from shared storage if available.
        """
        saved_locations = shared.load_data("binary_locations")
        if saved_locations:
            self.binary_locations = saved_locations
            logging.info("Binary locations loaded from shared storage.")
