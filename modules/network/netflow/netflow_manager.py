import subprocess
import json
import os
from core import shared as shared
#from iptables_manager import IptablesManager
from modules.iptables.iptables_manager import IptablesManager

class NetFlowManager:
    """
    This class manages NetFlow rules in iptables, keeps track of rules,
    and interfaces with a JSON file and shared storage.
    """

    def __init__(self):
        pass

    config_file = "iptables_netflow.json"


    @staticmethod
    def _load_rules():
        """Loads NetFlow rules from a JSON file."""
        if os.path.exists(NetFlowManager.config_file):
            with open(NetFlowManager.config_file, "r") as f:
                return json.load(f)
        return {}

    @staticmethod
    def _save_rules(rules):
        """Saves NetFlow rules to a JSON file."""
        with open(NetFlowManager.config_file, "w") as f:
            json.dump(rules, f, indent=4)


    @staticmethod
    def add_netflow_rule(chain="OUTPUT", interface="eth0", position=1):
        """
        Adds a NetFlow rule to a specified iptables chain and position,
        and saves the rule in the JSON file for persistent tracking.

        :param chain: The iptables chain to add the rule to (default: "OUTPUT").
        :param interface: The network interface to monitor (default: "eth0").
        :param position: Position of the rule in the chain (default: 1).
        """
        rules = NetFlowManager._load_rules()

        try:
            # Determine interface flag based on chain
            interface_flag = "-i" if chain == "INPUT" else "-o" if chain == "OUTPUT" else None
            command = ["sudo", "iptables", "-I", chain, str(position)]
            
            # Add interface option if applicable
            if interface_flag:
                command.extend([interface_flag, interface])
            
            # Add NETFLOW target
            command.extend(["-j", "NETFLOW"])

            # Add rule in iptables
            subprocess.run(command, check=True)

            # Create and store rule ID
            rule_id = f"{chain}_{interface}_{position}"
            rules[rule_id] = {"chain": chain, "interface": interface, "position": position}

            # Save rule in JSON file for persistence
            NetFlowManager._save_rules(rules)
            
            print(f"NetFlow rule added to {chain} chain for interface {interface} at position {position}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to add NetFlow rule: {e}")



    @staticmethod
    def remove_netflow_rule_by_id(rule_id):
        """
        Removes a specific NetFlow rule by its ID, if it exists in the JSON file.

        :param rule_id: ID of the rule to remove.
        """
        rules = NetFlowManager._load_rules()

        if rule_id in rules:
            rule = rules[rule_id]
            try:
                # Use IptablesManager to remove rule by its position
                IptablesManager.remove_rule_by_number(rule["chain"], rule["position"])
                del rules[rule_id]
                NetFlowManager._save_rules(rules)
                shared.remove_rule(rule_id)
                print(f"Removed NetFlow rule with ID {rule_id}.")
            except Exception as e:
                print(f"Failed to remove NetFlow rule with ID {rule_id}: {e}")
        else:
            print(f"No rule found with ID {rule_id}.")

    @staticmethod
    def remove_netflow_rule_by_number(chain="OUTPUT", line_number=1):
        """
        Removes a NetFlow rule by line number in a specific chain.

        :param chain: The iptables chain to target (default: "OUTPUT").
        :param line_number: Line number of the rule to remove (default: 1).
        """
        try:
            # Use IptablesManager to remove rule by line number
            IptablesManager.remove_rule_by_number(chain, line_number)
            print(f"NetFlow rule removed from {chain} chain at line {line_number}.")
        except Exception as e:
            print(f"Failed to remove rule at line {line_number}: {e}")


    @staticmethod
    def list_netflow_rules(chain="OUTPUT"):
        """
        Lists all NetFlow rules in a specified iptables chain and shows from JSON.

        :param chain: The iptables chain to list (default: "OUTPUT").
        """
        try:
            # Use subprocess to list rules in the specified chain
            print(f"Listing NetFlow rules for chain {chain}:")
            subprocess.run(
                ["sudo", "iptables", "-L", chain, "-v", "-n", "--line-numbers"],
                check=True
            )

            # Display NetFlow rules stored in JSON file
            print("\nCurrent NetFlow rules from configuration:")
            rules = NetFlowManager._load_rules()
            for rule_id, rule in rules.items():
                if rule["chain"] == chain:
                    print(f"ID: {rule_id} | Chain: {rule['chain']} | Interface: {rule['interface']} | Position: {rule['position']}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to list NetFlow rules for chain {chain}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


    @staticmethod
    def reset_all_netflow():
        """
        Resets all NetFlow configurations by clearing NetFlow rules in iptables,
        and removing entries from JSON and shared storage.
        """
        rules = NetFlowManager._load_rules()

        for rule_id, rule in rules.items():
            try:
                IptablesManager.remove_rule_by_number(rule["chain"], rule["position"])
                print(f"Removed rule ID {rule_id} from {rule['chain']} chain.")
            except Exception as e:
                print(f"Failed to remove rule ID {rule_id}: {e}")

        # Clear JSON file and shared storage
        NetFlowManager._save_rules({})
        shared.clear_all_rules()
        print("All NetFlow configurations have been reset.")

    @staticmethod
    def configure_netflow_destination(destination="127.0.0.1:2055"):
        """
        Configures the destination IP and port for exporting NetFlow data.

        :param destination: Destination IP and port for NetFlow data (default: "127.0.0.1:2055").
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.destination={destination}"],
                check=True
            )
            print(f"NetFlow data destination set to {destination}.")
            print("Observe reports at the destination or using monitoring tools.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to configure NetFlow destination: {e}")

    @staticmethod
    def set_flow_timeouts(active_timeout=300, inactive_timeout=15):
        """
        Sets the active and inactive timeout for NetFlow records.

        :param active_timeout: Active timeout in seconds (default: 300).
        :param inactive_timeout: Inactive timeout in seconds (default: 15).
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.timeout_active={active_timeout}"],
                check=True
            )
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.timeout_inactive={inactive_timeout}"],
                check=True
            )
            print(f"NetFlow active timeout set to {active_timeout} seconds.")
            print(f"NetFlow inactive timeout set to {inactive_timeout} seconds.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set NetFlow timeouts: {e}")

    @staticmethod
    def set_sampling_rate(rate=1):
        """
        Sets the sampling rate for NetFlow data collection.

        :param rate: The sampling rate, where 1 means sampling every packet (default: 1).
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.sampling_rate={rate}"],
                check=True
            )
            print(f"NetFlow sampling rate set to {rate}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set NetFlow sampling rate: {e}")


    @staticmethod
    def set_protocol_version(version=9):
        """
        Sets the NetFlow protocol version for exporting data.

        :param version: The NetFlow protocol version (default: 9).
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.protocol_version={version}"],
                check=True
            )
            print(f"NetFlow protocol version set to {version}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set NetFlow protocol version: {e}")


    @staticmethod
    def set_max_flow_cache(size=65536):
        """
        Sets the maximum number of flows the NetFlow cache can hold.

        :param size: Maximum number of flows (default: 65536).
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.maxflows={size}"],
                check=True
            )
            print(f"NetFlow maximum flow cache size set to {size}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set NetFlow maximum flow cache size: {e}")


    @staticmethod
    def enable_ipv6_flows(enable=True):
        """
        Enables or disables IPv6 flows in the NetFlow export.

        :param enable: Boolean flag to enable or disable IPv6 flow export (default: True).
        """
        value = 1 if enable else 0
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.ipv6={value}"],
                check=True
            )
            print(f"IPv6 flow export {'enabled' if enable else 'disabled'}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set IPv6 flow export: {e}")


    @staticmethod
    def set_protocol_expiry_times(tcp_timeout=3600, udp_timeout=300, icmp_timeout=60):
        """
        Sets expiry times for flows based on protocol.

        :param tcp_timeout: Expiry time for TCP flows in seconds (default: 3600).
        :param udp_timeout: Expiry time for UDP flows in seconds (default: 300).
        :param icmp_timeout: Expiry time for ICMP flows in seconds (default: 60).
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.tcp_timeout={tcp_timeout}"],
                check=True
            )
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.udp_timeout={udp_timeout}"],
                check=True
            )
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.icmp_timeout={icmp_timeout}"],
                check=True
            )
            print(f"Set TCP flow expiry to {tcp_timeout}s, UDP to {udp_timeout}s, and ICMP to {icmp_timeout}s.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set protocol expiry times: {e}")


    @staticmethod
    def set_exporting_interface(interface="eth0"):
        """
        Sets a specific interface for exporting NetFlow data.

        :param interface: Network interface to use for NetFlow export (default: "eth0").
        """
        try:
            subprocess.run(
                ["sudo", "sysctl", f"net.netflow.nf0.interface={interface}"],
                check=True
            )
            print(f"NetFlow exporting interface set to {interface}.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set NetFlow exporting interface: {e}")
