import os
import subprocess
import crypt
from datetime import datetime, timedelta
import pwd
import grp

class PAMUserManager:
    def __init__(self, username, password, shell='/bin/bash'):
        """
        Initialize PAMUserManager instance for managing system users.

            Parameters:
                - username (str): The username for the new user.
                - password (str): The password for the user.
                - shell (str): The login shell for the user (default is /bin/bash).

            Returns:
                - None
        """
        self.username = username
        self.password = password
        self.shell = shell

    def create_user(self):
        """
        Create a user on the system and sets an encrypted password.

            Parameters:
                - None

            Returns:
                - str: Confirmation message of user creation.

            Raises:
                - subprocess.CalledProcessError: If user creation fails.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.create_user()
        """
        try:
            subprocess.run(['useradd', '-m', '-s', self.shell, self.username], check=True)
            self._set_password()
            return f"User {self.username} created successfully."
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Error creating user {self.username}: {e}")

    def _set_password(self):
        """
        Set an encrypted password for the user.

            Parameters:
                - None

            Returns:
                - None

            Raises:
                - subprocess.CalledProcessError: If password setup fails.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager._set_password()
        """
        enc_password = crypt.crypt(self.password, crypt.mksalt(crypt.METHOD_SHA512))
        subprocess.run(['usermod', '-p', enc_password, self.username], check=True)

    def set_password_policy(self, min_length=8, max_length=64, min_days=7, max_days=90,
                            warn_days=7, complex_req=True):
        """
        Configure password policy including length, age, and complexity requirements.

            Parameters:
                - min_length (int): Minimum password length.
                - max_length (int): Maximum password length.
                - min_days (int): Minimum days between password changes.
                - max_days (int): Maximum days a password is valid.
                - warn_days (int): Days before expiration to warn user.
                - complex_req (bool): Enforce complexity requirements (default True).

            Returns:
                - str: Confirmation message of password policy application.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.set_password_policy(min_length=12, max_days=180)
        """
        with open('/etc/security/pwquality.conf', 'a') as f:
            f.write(f"minlen = {min_length}\n")
            f.write(f"maxlen = {max_length}\n")
            if complex_req:
                f.write("minclass = 4\n")  # Requires uppercase, lowercase, digit, and symbol

        subprocess.run(['chage', '-m', str(min_days), '-M', str(max_days),
                        '-W', str(warn_days), self.username], check=True)
        return "Password policy set successfully."

    def set_account_expiry(self, days_from_now=365):
        """
        Set the account expiration date for the user.

            Parameters:
                - days_from_now (int): Days from today until account expires.

            Returns:
                - str: Confirmation message of account expiration setup.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.set_account_expiry(180)
        """
        expiry_date = (datetime.now() + timedelta(days=days_from_now)).strftime('%Y-%m-%d')
        subprocess.run(['chage', '-E', expiry_date, self.username], check=True)
        return f"Account expiration for {self.username} set to {expiry_date}."

    def enforce_password_reset(self):
        """
        Force the user to reset their password at next login.

            Parameters:
                - None

            Returns:
                - str: Confirmation message of password reset enforcement.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.enforce_password_reset()
        """
        subprocess.run(['chage', '-d', '0', self.username], check=True)
        return f"Password reset enforced for {self.username}."

    def manage_user_groups(self, groups_to_add=None, groups_to_remove=None):
        """
        Manage group assignments for the user.

            Parameters:
                - groups_to_add (list): List of groups to add user to.
                - groups_to_remove (list): List of groups to remove user from.

            Returns:
                - str: Confirmation message of group updates.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.manage_user_groups(groups_to_add=["sudo", "developers"])
        """
        if groups_to_add:
            subprocess.run(['usermod', '-aG', ','.join(groups_to_add), self.username], check=True)
        if groups_to_remove:
            for group in groups_to_remove:
                subprocess.run(['gpasswd', '-d', self.username, group], check=True)
        return f"Group assignments updated for {self.username}."

    def configure_login_attempts(self, max_attempts=5, lockout_time=600):
        """
        Configure maximum login attempts and lockout time.

            Parameters:
                - max_attempts (int): Maximum login attempts before lockout.
                - lockout_time (int): Lockout duration in seconds.

            Returns:
                - str: Confirmation message of lockout configuration.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.configure_login_attempts(max_attempts=3, lockout_time=300)
        """
        with open('/etc/security/faillock.conf', 'a') as f:
            f.write(f"deny = {max_attempts}\n")
            f.write(f"unlock_time = {lockout_time}\n")
        return f"Login attempts and lockout configured: {max_attempts} attempts, {lockout_time} seconds lockout."

    def audit_user_permissions(self):
        """
        Audit user permissions, checking for group memberships that might pose a security risk.

            Parameters:
                - None

            Returns:
                - str: Message indicating potential security risks.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.audit_user_permissions()
        """
        user_groups = [g.gr_name for g in grp.getgrall() if self.username in g.gr_mem]
        warnings = []
        if 'sudo' in user_groups:
            warnings.append(f"{self.username} has sudo privileges.")
        if 'wheel' in user_groups:
            warnings.append(f"{self.username} is in the wheel group.")

        if warnings:
            return "Potential security risks:\n" + "\n".join(warnings)
        return f"No elevated permissions detected for {self.username}."

    def delete_user(self, remove_home=False):
        """
        Delete the user from the system, with option to remove home directory.

            Parameters:
                - remove_home (bool): Whether to delete user's home directory.

            Returns:
                - str: Confirmation message of user deletion.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.delete_user(remove_home=True)
        """
        cmd = ['userdel']
        if remove_home:
            cmd.append('-r')
        cmd.append(self.username)
        subprocess.run(cmd, check=True)
        return f"User {self.username} deleted."

    def set_password_character_restrictions(self, min_digits=1, min_uppercase=1,
                                            min_lowercase=1, min_special=1):
        """
        Enforce character requirements for passwords.

            Parameters:
                - min_digits (int): Minimum digits required in the password.
                - min_uppercase (int): Minimum uppercase letters required.
                - min_lowercase (int): Minimum lowercase letters required.
                - min_special (int): Minimum special characters required.

            Returns:
                - str: Confirmation message of character restriction setup.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.set_password_character_restrictions(min_special=2)
        """
        with open('/etc/security/pwquality.conf', 'a') as f:
            f.write(f"dcredit = -{min_digits}\n")
            f.write(f"ucredit = -{min_uppercase}\n")
            f.write(f"lcredit = -{min_lowercase}\n")
            f.write(f"ocredit = -{min_special}\n")
        return "Password character restrictions set."

    def lock_account(self):
        """
        Lock the user account, preventing login.

            Parameters:
                - None

            Returns:
                - str: Confirmation message of account lock.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.lock_account()
        """
        subprocess.run(['usermod', '-L', self.username], check=True)
        return f"Account {self.username} locked."

    def unlock_account(self):
        """
        Unlock the user account, allowing login.

            Parameters:
                - None

            Returns:
                - str: Confirmation message of account unlock.

            Example:
                manager = PAMUserManager("testuser", "password123")
                manager.unlock_account()
        """
        subprocess.run(['usermod', '-U', self.username], check=True)
        return f"Account {self.username} unlocked."
