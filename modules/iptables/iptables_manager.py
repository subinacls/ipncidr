import subprocess

class IptablesManager:
    """
    A class to manage iptables firewall rules and ipset configurations.
    """

    def __init__(self):
        """
        Initialize the IptablesManager with default profiles.

            Attributes:
                - profiles (dict): Contains firewall profiles (default, open, restricted).
        """
        self.required_binaries = ["iptables","iptables-save","iptables-restore"]
        self.profiles = {
            "default": {"policy": "DROP", "rules": []},
            "open": {"policy": "ACCEPT", "rules": []},
            "restricted": {"policy": "DROP", "rules": []},
        }

    def set_profile(self, profile_name):
        """
        Set a default profile for the firewall.

            Parameters:
                - profile_name (str): The name of the profile to apply.

            Returns:
                - str: Confirmation message of profile application.

            Raises:
                - ValueError: If the profile name is invalid.

            Example:
                manager = IptablesManager()
                manager.set_profile("default")
        """
        if profile_name in self.profiles:
            policy = self.profiles[profile_name]["policy"]
            self._run_iptables_cmd(["-P", "INPUT", policy])
            return f"Profile '{profile_name}' applied with policy {policy}."
        else:
            raise ValueError("Invalid profile name.")

    def add_rule(self, src_ip, dest_port, action="DROP", insert=False):
        """
        Add a new rule to the iptables configuration.

            Parameters:
                - src_ip (str): Source IP address for the rule.
                - dest_port (int): Destination port to match for the rule.
                - action (str): Action to take on matched traffic (e.g., "ACCEPT" or "DROP").
                - insert (bool): If True, insert the rule at the top; otherwise, append it.

            Returns:
                - str: Confirmation message indicating the rule has been added.

            Example:
                manager = IptablesManager()
                manager.add_rule(src_ip="192.168.1.1", dest_port=22, action="ACCEPT", insert=True)
        """
        cmd = ["-I" if insert else "-A", "INPUT", "-s", src_ip, "-p", "tcp", "--dport", str(dest_port), "-j", action]
        self._run_iptables_cmd(cmd)
        return f"Rule added: {action} traffic from {src_ip} to port {dest_port}"

    def delete_rule(self, src_ip, dest_port, action="DROP"):
        """
        Delete a rule from the iptables configuration.

            Parameters:
                - src_ip (str): Source IP address of the rule to delete.
                - dest_port (int): Destination port of the rule to delete.
                - action (str): Action of the rule to delete.

            Returns:
                - str: Confirmation message indicating the rule has been deleted.

            Example:
                manager = IptablesManager()
                manager.delete_rule(src_ip="192.168.1.1", dest_port=22, action="ACCEPT")
        """
        cmd = ["-D", "INPUT", "-s", src_ip, "-p", "tcp", "--dport", str(dest_port), "-j", action]
        self._run_iptables_cmd(cmd)
        return f"Rule deleted: {action} traffic from {src_ip} to port {dest_port}"

    def flush_all_rules(self):
        """
        Flush all iptables rules.

            Returns:
                - str: Confirmation message indicating all rules have been flushed.
        """
        self._run_iptables_cmd(["-F"])
        return "All iptables rules have been flushed."


    def flush_rule_group(self, chain_name="INPUT"):
        """
        Flush a specific chain (rule group) in iptables.

            Parameters:
                - chain_name (str): Name of the iptables chain to flush (e.g., INPUT, OUTPUT, FORWARD).

            Returns:
                - str: Confirmation message indicating the specific chain has been flushed.
        """
        self._run_iptables_cmd(["-F", chain_name])
        return f"Iptables chain '{chain_name}' has been flushed."


    def list_ipset_groups(self):
        """
        List all configured ipset groups.

            Returns:
                - list: A list of ipset group names, or a message if no groups are found.
        """
        try:
            result = subprocess.run(["ipset", "list", "-n"], capture_output=True, text=True, check=True)
            groups = result.stdout.strip().splitlines()
            if groups:
                return groups
            else:
                return "No ipset groups are configured."
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to list ipset groups: {e}")

    def apply_ipset_group(self, group_name, action="DROP", direction="INPUT"):
        """
        Apply an ipset group as a match criterion in iptables.

            Parameters:
                - group_name (str): Name of the ipset group to apply.
                - action (str): Action to take on matched traffic (e.g., "ACCEPT" or "DROP").
                - direction (str): Chain direction to apply the rule (e.g., "INPUT", "OUTPUT").

            Returns:
                - str: Confirmation message indicating the ipset group has been applied.
        """
        print(f"Available groups: {', '.join(self.list_ipset_groups())}")
        if group_name not in self.list_ipset_groups():
            return f"Ipset group '{group_name}' does not exist. Available groups: {', '.join(self.list_ipset_groups())}"

        cmd = ["-A", direction, "-m", "set", "--match-set", group_name, "src", "-j", action]
        self._run_iptables_cmd(cmd)
        return f"Ipset group '{group_name}' applied to {direction} chain with action {action}."






    def delete_rule_by_line_number(self, line_number):
        """
        Delete a rule by its line number.

            Parameters:
                - line_number (int): Line number of the rule to delete.

            Returns:
                - str: Confirmation message indicating the rule has been deleted.
        """
        cmd = ["-D", "INPUT", str(line_number)]
        self._run_iptables_cmd(cmd)
        return f"Rule at line {line_number} deleted."

    def move_rule(self, from_line, to_line):
        """
        Move a rule from one line to another.

            Parameters:
                - from_line (int): The original line number of the rule.
                - to_line (int): The new line number to insert the rule at.

            Returns:
                - str: Confirmation message indicating the rule has been moved.
        """
        rules = self.show_rules()
        rule_to_move = rules.get(from_line)
        if rule_to_move:
            self.delete_rule_by_line_number(from_line)
            self._run_iptables_cmd(["-I", "INPUT", str(to_line)] + rule_to_move.split()[2:])
            return f"Rule moved from line {from_line} to {to_line}."
        else:
            return f"No rule found at line {from_line}."

    def save_rules(self):
        """
        Save the current iptables rules to a file.

            Returns:
                - str: Confirmation message indicating rules have been saved.
        """
        self._run_iptables_cmd(["-S"], output_file="iptables_rules_save.txt")
        return "Iptables rules saved to iptables_rules_save.txt."

    def reload_rules(self):
        """
        Reload the iptables rules from the saved file.

            Returns:
                - str: Confirmation message indicating rules have been reloaded.
        """
        subprocess.run(["iptables-restore", "<", "iptables_rules_save.txt"], shell=True, check=True)
        return "Iptables rules reloaded from iptables_rules_save.txt."

    def show_rules(self):
        """
        Show the current iptables rule set.

            Parameters:
                - with_line_numbers (bool): Whether to show line numbers with rules.

            Returns:
                - str: The current iptables rule set as a string with optional line numbers.
        """
        result = subprocess.run(["iptables", "-L", "-v", "-n", "--line-numbers"], capture_output=True, text=True)
        output = result.stdout
        return output

    def _run_iptables_cmd(self, cmd, output_file=None):
        """
        Run an iptables command, optionally saving output to a file.

            Parameters:
                - cmd (list): List of command arguments for iptables.
                - output_file (str, optional): File path to save command output.

            Raises:
                - RuntimeError: If the iptables command fails.
        """
        try:
            if output_file:
                with open(output_file, "w") as file:
                    subprocess.run(["iptables"] + cmd, stdout=file, check=True)
            else:
                subprocess.run(["iptables"] + cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Iptables command failed: {e}")






    def create_ipset_group(self, group_name, hash_type="hash:net,port"):
        """
        Create an IPset group with the specified hash type.

            Parameters:
                - group_name (str): Name of the IPset group.
                - hash_type (str): Hash type for the IPset (default: 'hash:net,port').

            Returns:
                - str: Confirmation message indicating the IPset group has been created.

            Example:
                manager = IptablesManager()
                manager.create_ipset_group("my_ipset_group")
        """
        self._run_ipset_cmd(["create", group_name, hash_type])
        return f"IPset group '{group_name}' created with hash type '{hash_type}'"

    def add_ip_to_ipset(self, group_name, ip, port=None):
        """
        Add an IP to an IPset group.

            Parameters:
                - group_name (str): Name of the IPset group.
                - ip (str): IP address to add.
                - port (int, optional): Port to associate with the IP in the group.

            Returns:
                - str: Confirmation message indicating the IP has been added.

            Example:
                manager = IptablesManager()
                manager.add_ip_to_ipset("my_ipset_group", "192.168.1.1", port=80)
        """
        cmd = ["add", group_name, f"{ip},{port}" if port else ip]
        self._run_ipset_cmd(cmd)
        return f"IP {ip} added to IPset group '{group_name}' on port {port}" if port else f"IP {ip} added to IPset group '{group_name}'"

    def _run_iptables_cmd(self, cmd):
        """
        Run an iptables command.

            Parameters:
                - cmd (list): List of command arguments for iptables.

            Raises:
                - RuntimeError: If the iptables command fails.

            Example:
                self._run_iptables_cmd(["-A", "INPUT", "-s", "192.168.1.1", "-j", "DROP"])
        """
        try:
            subprocess.run(["iptables"] + cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Iptables command failed: {e}")

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
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ipset command failed: {e}")
