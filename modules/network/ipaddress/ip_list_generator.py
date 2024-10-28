import ipaddress
from typing import List, Tuple, Union
import json

class IPAddressManager:
    """
    A class to manage and perform various operations on IP addresses, including sorting,
    categorizing based on RFC, identifying broadcast types, condensing into ranges or CIDRs,
    and saving sorted lists to disk.
    """

    def __init__(self):
        pass

    @classmethod
    def sort_ips(cls, ip_list: List[str]) -> List[str]:
        """
        Sorts a list of IP addresses in ascending order.
        
        Args:
            ip_list (List[str]): A list of IP addresses as strings.

        Returns:
            List[str]: A sorted list of IP addresses.
        """
        ip_objects = [ipaddress.ip_address(ip) for ip in ip_list]
        sorted_ips = sorted(ip_objects)
        return [str(ip) for ip in sorted_ips]

    @classmethod
    def categorize_ips(cls, ip_list: List[str]) -> dict:
        """
        Categorizes IP addresses based on RFC and their usability on the internet.
        
        Args:
            ip_list (List[str]): A list of IP addresses as strings.

        Returns:
            dict: A dictionary categorizing IPs as internet-usable, private, loopback,
                  link-local, multicast, broadcast, and reserved.
        """
        categories = {
            "internet_usable": [],
            "private": [],
            "loopback": [],
            "link_local": [],
            "multicast": [],
            "broadcast": [],
            "reserved": []
        }

        for ip in ip_list:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_global:
                categories["internet_usable"].append(str(ip))
            elif ip_obj.is_private:
                categories["private"].append(str(ip))
            elif ip_obj.is_loopback:
                categories["loopback"].append(str(ip))
            elif ip_obj.is_link_local:
                categories["link_local"].append(str(ip))
            elif ip_obj.is_multicast:
                categories["multicast"].append(str(ip))
            elif ip_obj.is_reserved:
                categories["reserved"].append(str(ip))
            if ip_obj.is_multicast or ip_obj.is_loopback:
                categories["broadcast"].append(str(ip))  # Optional, if you consider these "broadcast"

        return categories

    @classmethod
    def condense_ips(cls, ip_list: List[str]) -> List[Union[str, Tuple[str, str]]]:
        """
        Condenses a list of IP addresses into ranges or CIDRs.

        Args:
            ip_list (List[str]): A list of IP addresses as strings.

        Returns:
            List[Union[str, Tuple[str, str]]]: A list of CIDR ranges or IP ranges.
        """
        ip_objects = [ipaddress.ip_address(ip) for ip in sorted(ip_list, key=lambda ip: int(ipaddress.ip_address(ip)))]
        ranges = []
        start_ip = ip_objects[0]
        end_ip = start_ip

        for ip in ip_objects[1:]:
            if ip - 1 == end_ip:
                end_ip = ip
            else:
                if start_ip == end_ip:
                    ranges.append(str(start_ip))
                else:
                    ranges.append((str(start_ip), str(end_ip)))
                start_ip = ip
                end_ip = ip
        if start_ip == end_ip:
            ranges.append(str(start_ip))
        else:
            ranges.append((str(start_ip), str(end_ip)))

        return ranges

    @classmethod
    def save_ips(cls, ip_list: List[str], filename: str) -> None:
        """
        Saves a list of IP addresses to a file.

        Args:
            ip_list (List[str]): A list of IP addresses as strings.
            filename (str): The file name to save the IP addresses.
        """
        with open(filename, 'w') as f:
            for ip in ip_list:
                f.write(f"{ip}\n")

    @classmethod
    def load_ips(cls, filename: str) -> List[str]:
        """
        Loads a list of IP addresses from a file.

        Args:
            filename (str): The file name to load the IP addresses from.

        Returns:
            List[str]: A list of IP addresses as strings.
        """
        with open(filename, 'r') as f:
            return [line.strip() for line in f.readlines()]

    @classmethod
    def run_bulk_processing(cls, input_file: str, output_file: str) -> None:
        """
        Runs bulk processing on an IP address list, sorting, categorizing, and saving results.

        Args:
            input_file (str): The file containing IP addresses to process.
            output_file (str): The file to save the processed IP addresses.
        """
        ip_list = cls.load_ips(input_file)
        sorted_ips = cls.sort_ips(ip_list)
        categorized_ips = cls.categorize_ips(sorted_ips)
        condensed_ips = cls.condense_ips(sorted_ips)

        result = {
            "sorted_ips": sorted_ips,
            "categorized_ips": categorized_ips,
            "condensed_ips": condensed_ips
        }

        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
