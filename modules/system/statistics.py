import platform
import psutil
import socket
import logging
import datetime
import json
import os

class SystemProfiler:
    """
    Gathers system information and profiles it for operational insights and statistics.
    
    Attributes:
        hostname (str): The hostname of the system.
        os_info (str): The operating system information.
        arch (str): The system architecture.
        cpu_info (dict): Information about the CPU (cores, usage).
        memory_info (dict): Information about memory usage.
        disk_info (dict): Information about disk usage.
        network_info (dict): Information about network interfaces.
        boot_time (datetime): The system boot time.
    """
    
    def __init__(self):
        """
        Initializes the SystemProfiler class, gathering initial system information.
        """
        self.hostname = self.get_hostname()
        self.os_info = self.get_os_info()
        self.arch = platform.machine()
        self.cpu_info = self.get_cpu_info()
        self.memory_info = self.get_memory_info()
        self.disk_info = self.get_disk_info()
        self.network_info = self.get_network_info()
        self.boot_time = self.get_boot_time()
        
    def get_hostname(self):
        """
        Retrieves the system hostname.
        
        Returns:
            str: The hostname of the system.
        """
        try:
            hostname = socket.gethostname()
            logging.debug(f"Hostname retrieved: {hostname}")
            return hostname
        except Exception as e:
            logging.error(f"Error retrieving hostname: {e}")
            return "Unknown"
    
    def get_os_info(self):
        """
        Retrieves the operating system information.
        
        Returns:
            str: A string containing the OS name, release, and version.
        """
        try:
            os_info = f"{platform.system()} {platform.release()} {platform.version()}"
            logging.debug(f"OS Info retrieved: {os_info}")
            return os_info
        except Exception as e:
            logging.error(f"Error retrieving OS info: {e}")
            return "Unknown"
    
    def get_cpu_info(self):
        """
        Retrieves CPU information, including core count and usage statistics.
        
        Returns:
            dict: A dictionary containing the number of cores and CPU usage percentages.
        """
        try:
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "cpu_usage_percent": psutil.cpu_percent(interval=1, percpu=True)
            }
            logging.debug(f"CPU Info retrieved: {cpu_info}")
            return cpu_info
        except Exception as e:
            logging.error(f"Error retrieving CPU info: {e}")
            return {}
    
    def get_memory_info(self):
        """
        Retrieves memory information, including total and available memory.
        
        Returns:
            dict: A dictionary containing total, available, used, and percentage of memory usage.
        """
        try:
            mem = psutil.virtual_memory()
            memory_info = {
                "total_memory": mem.total,
                "available_memory": mem.available,
                "used_memory": mem.used,
                "memory_usage_percent": mem.percent
            }
            logging.debug(f"Memory Info retrieved: {memory_info}")
            return memory_info
        except Exception as e:
            logging.error(f"Error retrieving memory info: {e}")
            return {}
    
    def get_disk_info(self):
        """
        Retrieves disk information for all partitions, including usage and filesystem type.
        
        Returns:
            dict: A dictionary containing disk usage information for each partition.
        """
        disk_info = {}
        try:
            for partition in psutil.disk_partitions():
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.device] = {
                    "mount_point": partition.mountpoint,
                    "file_system_type": partition.fstype,
                    "total_space": usage.total,
                    "used_space": usage.used,
                    "free_space": usage.free,
                    "usage_percent": usage.percent
                }
            logging.debug(f"Disk Info retrieved: {disk_info}")
        except Exception as e:
            logging.error(f"Error retrieving disk info: {e}")
        return disk_info
    
    def get_network_info(self):
        """
        Retrieves network information, including IP addresses and MAC addresses for each interface.
        
        Returns:
            dict: A dictionary containing network interface details.
        """
        network_info = {}
        try:
            interfaces = psutil.net_if_addrs()
            for iface, addrs in interfaces.items():
                network_info[iface] = {}
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        network_info[iface]["ipv4"] = addr.address
                    elif addr.family == socket.AF_INET6:
                        network_info[iface]["ipv6"] = addr.address
                    elif addr.family == psutil.AF_LINK:
                        network_info[iface]["mac_address"] = addr.address
            logging.debug(f"Network Info retrieved: {network_info}")
        except Exception as e:
            logging.error(f"Error retrieving network info: {e}")
        return network_info
    
    def get_boot_time(self):
        """
        Retrieves the system boot time.
        
        Returns:
            datetime: The boot time of the system.
        """
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            logging.debug(f"Boot Time retrieved: {boot_time}")
            return boot_time
        except Exception as e:
            logging.error(f"Error retrieving boot time: {e}")
            return datetime.datetime.min
    
    def to_json(self, filepath="system_profile.json"):
        """
        Exports the system profile to a JSON file.
        
        Args:
            filepath (str): The file path to save the JSON data.
        """
        try:
            data = {
                "hostname": self.hostname,
                "os_info": self.os_info,
                "arch": self.arch,
                "cpu_info": self.cpu_info,
                "memory_info": self.memory_info,
                "disk_info": self.disk_info,
                "network_info": self.network_info,
                "boot_time": self.boot_time.isoformat()
            }
            with open(filepath, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            logging.info(f"System profile exported to {filepath}")
        except Exception as e:
            logging.error(f"Error exporting system profile to JSON: {e}")

'''
# Example usage:
if __name__ == "__main__":
    profiler = SystemProfiler()
    profiler.to_json()  # Export system profile to a JSON file
'''
