import os
import re

class PAMManager:
    """
    A class to manage PAM (Pluggable Authentication Modules) settings on the local system.

    This class allows users to list available PAM modules, view and modify PAM configuration
    files for services, and receive recommendations on commonly used configurations.

    Attributes:
        pam_dir (str): Directory where PAM configuration files are stored (e.g., /etc/pam.d).


    """

    def __init__(self, pam_dir="/etc/pam.d"):
        self.pam_dir = pam_dir
        if not os.path.isdir(self.pam_dir):
            raise ValueError(f"The specified PAM directory '{self.pam_dir}' does not exist.")

    def list_services(self):
        # List all PAM-enabled services
        """
        List all PAM-enabled services (Ex: SSH) on the local system

            Returns:
                - list: A list of PAM enabled service found on the local system.


        """
        return [file for file in os.listdir(self.pam_dir) if os.path.isfile(os.path.join(self.pam_dir, file))]

    def show_service_config(self, service):
        """
        Show specific PAM-enabled service configured (Ex: SSH) on the local system

            Returns:
                - list: Output of a specific PAM enabled service configuration settings.


        """
        # Display the current PAM configuration for a specific service
        config_path = os.path.join(self.pam_dir, service)
        if os.path.isfile(config_path):
            with open(config_path, "r") as file:
                return file.read()
        else:
            return f"No configuration file found for service '{service}'."

    def check_compliance(self):
        """
        Check PAM configurations for compliance with security best practices and standards.

            Returns:
                - list: A list of compliance findings with category and location information.


        """
        findings = []
        standards = {
            "password_min_length": 9,
            "lockout_attempts": 3,
            "lockout_duration": 900,
            "inactivity_timeout": 600
        }

        # Check each PAM configuration file for common compliance issues
        for service in self.list_services():
            config_path = os.path.join(self.pam_dir, service)
            with open(config_path, "r") as file:
                for line in file:
                    line = line.strip()

                    # Check for minimum password length
                    if "pam_unix.so" in line and "minlen=" in line:
                        minlen = int(re.search(r"minlen=(\d+)", line).group(1))
                        if minlen < standards["password_min_length"]:
                            findings.append(
                                f"[CIS] Password length less than {standards['password_min_length']} characters: {config_path}"
                            )

                    # Check for account lockout policy
                    if "pam_tally2.so" in line and "deny=" in line:
                        deny = int(re.search(r"deny=(\d+)", line).group(1))
                        if deny < standards["lockout_attempts"]:
                            findings.append(
                                f"[CIS] Account lockout threshold below {standards['lockout_attempts']} attempts: {config_path}"
                            )

                    # Check for lockout duration
                    if "pam_tally2.so" in line and "unlock_time=" in line:
                        unlock_time = int(re.search(r"unlock_time=(\d+)", line).group(1))
                        if unlock_time < standards["lockout_duration"]:
                            findings.append(
                                f"[CIS] Lockout duration less than {standards['lockout_duration']} seconds: {config_path}"
                            )

                    # Check for session inactivity timeout
                    if "pam_faildelay.so" in line and "delay=" in line:
                        delay = int(re.search(r"delay=(\d+)", line).group(1))
                        if delay < standards["inactivity_timeout"]:
                            findings.append(
                                f"[NIST] Session inactivity timeout less than {standards['inactivity_timeout']} seconds: {config_path}"
                            )

                    # Check for additional secure authentication modules
                    if "auth" in line and "required" in line and "pam_deny.so" not in line and "pam_unix.so" not in line:
                        findings.append(
                            f"[BEST PRACTICE] Consider using additional secure modules (e.g., pam_tally2, pam_faildelay): {config_path}"
                        )

        return findings if findings else ["All checked configurations are compliant."]

    def list_pam_modules(self):
        """
        List available PAM modules on the system.

            Returns:
                - list: A list of PAM module names.
        """
        modules = []
        try:
            with open("/etc/pam.conf", "r") as pam_conf:
                for line in pam_conf:
                    match = re.search(r"^\s*(\S+)\s", line)
                    if match:
                        module = match.group(1)
                        if module not in modules:
                            modules.append(module)
        except FileNotFoundError:
            pass
        return modules or ["No PAM modules found in /etc/pam.conf"]

    def recommend_settings(self, service):
        """
        Recommend common PAM settings based on best practices for security and usability.

            Parameters:
                - service (str): The service name for which to recommend settings.

            Returns:
                - list: A list of recommended PAM configurations.
        """
        recommendations = {
            "sshd": [
                "auth required pam_faildelay.so delay=2000000",
                "auth required pam_sepermit.so",
                "auth substack password-auth",
                "auth include postlogin",
                "account required pam_nologin.so",
                "account include password-auth",
                "password include password-auth",
                "session required pam_selinux.so close",
                "session required pam_loginuid.so",
                "session optional pam_keyinit.so force revoke",
                "session include password-auth",
                "session required pam_limits.so"
            ],
            "login": [
                "auth required pam_securetty.so",
                "auth required pam_nologin.so",
                "auth include system-auth",
                "account required pam_access.so",
                "account required pam_nologin.so",
                "password include system-auth",
                "session required pam_limits.so",
                "session required pam_unix.so",
                "session optional pam_lastlog.so",
            ]
        }
        return recommendations.get(service, ["No recommendations available for this service."])

    def add_rule(self, service, rule):
        """
        Add a new rule to the PAM configuration for a specific service.

            Parameters:
                - service (str): The service name to configure (e.g., 'login').
                - rule (str): The PAM rule to add (e.g., "auth required pam_unix.so").

            Returns:
                - str: Confirmation message of the rule addition.
        """
        config_path = os.path.join(self.pam_dir, service)
        with open(config_path, "a") as file:
            file.write(rule + "\n")
        return f"Rule added to '{service}' configuration: {rule}"

    def modify_rule(self, service, old_rule, new_rule):
        """
        Modify an existing rule in the PAM configuration for a specific service.

            Parameters:
                - service (str): The service name to configure.
                - old_rule (str): The existing rule to be replaced.
                - new_rule (str): The new rule to replace the existing rule.

            Returns:
                - str: Confirmation message indicating the rule modification.
        """
        config_path = os.path.join(self.pam_dir, service)
        with open(config_path, "r") as file:
            lines = file.readlines()
        with open(config_path, "w") as file:
            modified = False
            for line in lines:
                if line.strip() == old_rule:
                    file.write(new_rule + "\n")
                    modified = True
                else:
                    file.write(line)
        return f"Rule modified in '{service}' configuration." if modified else "Rule not found."

    def delete_rule(self, service, rule):
        """
        Delete a rule from the PAM configuration for a specific service.

            Parameters:
                - service (str): The service name to configure.
                - rule (str): The rule to delete.

            Returns:
                - str: Confirmation message indicating the rule deletion.
        """
        config_path = os.path.join(self.pam_dir, service)
        with open(config_path, "r") as file:
            lines = file.readlines()
        with open(config_path, "w") as file:
            deleted = False
            for line in lines:
                if line.strip() == rule:
                    deleted = True
                    continue
                file.write(line)
        return f"Rule deleted from '{service}' configuration." if deleted else "Rule not found."


'''
# Example Usage
pam_manager = PAMManager()

# List all PAM-enabled services
print("Available PAM Services:")
print(pam_manager.list_services())

# Show current configuration for sshd
print("\nCurrent SSHD Configuration:")
print(pam_manager.show_service_config("sshd"))

# Recommend settings for sshd
print("\nRecommended SSHD Settings:")
print(pam_manager.recommend_settings("sshd"))

# Add a rule to sshd configuration
print(pam_manager.add_rule("sshd", "auth required pam_unix.so"))

# Modify a rule in sshd configuration
print(pam_manager.modify_rule("sshd", "auth required pam_unix.so", "auth required pam_securetty.so"))

# Delete a rule from sshd configuration
print(pam_manager.delete_rule("sshd", "auth required pam_securetty.so"))
'''
