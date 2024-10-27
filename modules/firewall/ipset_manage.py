import subprocess

class IPSetManager:
    def __init__(self):
        """
        Initialize the IPSetManager instance.
        """
        pass

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
        full_cmd = ["ipset"] + cmd
        try:
            result = subprocess.run(full_cmd, check=True, capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"IPSet command failed: {e.stderr}")

    def create_set(self, set_name, set_type="hash:ip"):
        """
        Create a new ipset.

        Parameters:
            - set_name (str): Name of the ipset to create.
            - set_type (str): Type of the ipset (default is 'hash:ip').

        Example:
            self.create_set("my_ipset_group")
        """
        return self._run_ipset_cmd(["create", set_name, set_type])

    def delete_set(self, set_name):
        """
        Delete an existing ipset.

        Parameters:
            - set_name (str): Name of the ipset to delete.

        Example:
            self.delete_set("my_ipset_group")
        """
        return self._run_ipset_cmd(["destroy", set_name])

    def add_entry(self, set_name, entry):
        """
        Add an entry to an ipset.

        Parameters:
            - set_name (str): Name of the ipset to add the entry to.
            - entry (str): Entry to add (e.g., IP address).

        Example:
            self.add_entry("my_ipset_group", "192.168.1.1")
        """
        return self._run_ipset_cmd(["add", set_name, entry])

    def delete_entry(self, set_name, entry):
        """
        Delete an entry from an ipset.

        Parameters:
            - set_name (str): Name of the ipset to delete the entry from.
            - entry (str): Entry to delete (e.g., IP address).

        Example:
            self.delete_entry("my_ipset_group", "192.168.1.1")
        """
        return self._run_ipset_cmd(["del", set_name, entry])

    def list_set(self, set_name=None):
        """
        List the contents of an ipset or all sets.

        Parameters:
            - set_name (str, optional): Name of the ipset to list. Lists all sets if None.

        Example:
            self.list_set("my_ipset_group")
        """
        cmd = ["list"] if set_name is None else ["list", set_name]
        return self._run_ipset_cmd(cmd)

    def flush_set(self, set_name=None):
        """
        Flush an ipset or all sets.

        Parameters:
            - set_name (str, optional): Name of the ipset to flush. Flushes all sets if None.

        Example:
            self.flush_set("my_ipset_group")
        """
        cmd = ["flush"] if set_name is None else ["flush", set_name]
        return self._run_ipset_cmd(cmd)

    def save(self):
        """
        Save the current ipset rules.

        Example:
            self.save()
        """
        return self._run_ipset_cmd(["save"])

    def restore(self, file_path):
        """
        Restore ipset rules from a file.

        Parameters:
            - file_path (str): Path to the file containing saved ipset rules.

        Example:
            self.restore("/path/to/rules.save")
        """
        return self._run_ipset_cmd(["restore", "-file", file_path])

    def execute_raw_ipset_cmd(self, cmd):
        """
        Execute a raw ipset command, ensuring it is ipset-related and sanitized.

        Parameters:
            - cmd (list): List of command arguments. The first argument must be 'ipset'.

        Raises:
            - ValueError: If the command does not begin with 'ipset' or contains potentially unsafe input.

        Example:
            self.execute_raw_ipset_cmd(["ipset", "list", "my_ipset_group"])
        """
        # Check command begins with "ipset"
        if cmd[0] != "ipset":
            raise ValueError("Only ipset commands are allowed.")

        # Allowed ipset commands for safety
        allowed_commands = {"create", "destroy", "add", "del", "list", "flush", "save", "restore"}

        # Verify the second argument is a valid ipset command
        if len(cmd) < 2 or cmd[1] not in allowed_commands:
            raise ValueError(f"Invalid ipset command: {cmd[1]}")

        # Ensure no argument contains special shell characters
        for arg in cmd[1:]:
            if any(c in arg for c in [';', '&', '|', '$', '`', '>', '<']):
                raise ValueError(f"Potentially unsafe character in argument: {arg}")

        # Run sanitized command
        return self._run_ipset_cmd(cmd[1:])

'''
ipset_manager = IPSetManager()

# Create a new ipset
ipset_manager.create_set("my_ipset_group")

# Add an entry
ipset_manager.add_entry("my_ipset_group", "192.168.1.1")

# List all ipsets
print(ipset_manager.list_set())

# Execute a raw command
ipset_manager.execute_raw_ipset_cmd(["ipset", "list", "my_ipset_group"])
'''
