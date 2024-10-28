# module_loader.py

import os
import importlib.util
import inspect
import shutil
import subprocess
import platform
import logging

logger = logging.getLogger(__name__)


class BinaryChecker:
    def __init__(self, required_binaries):
        """
        Initialize the BinaryChecker instance with a list of required binaries.

        Parameters:
            - required_binaries (list): List of binaries to check for availability.
        """
        self.required_binaries = required_binaries

    def check_binaries(self):
        """
        Check if the required binaries are available. If not, prompt the user to install them.

        Raises:
            - RuntimeError: If required binaries are missing and installation is declined.
        """
        missing_binaries = [binary for binary in self.required_binaries if not shutil.which(binary)]

        if missing_binaries:
            print(f"Warning: Missing binaries: {', '.join(missing_binaries)}")

            # Prompt the user to install missing binaries
            install_choice = input("Would you like to install the missing binaries? (y/n): ").strip().lower()
            if install_choice == 'y':
                for binary in missing_binaries:
                    self.install_binary(binary)
            else:
                raise RuntimeError(f"Cannot proceed without required binaries: {', '.join(missing_binaries)}")

    def install_binary(self, binary):
        """
        Install the specified binary based on the operating system.

        Parameters:
            - binary (str): The binary to install.

        Raises:
            - RuntimeError: If installation command fails or OS is unsupported.
        """
        os_type = platform.system()

        if os_type == "Linux":
            install_command = ["sudo", "apt-get", "install", "-y", binary]
            print(f"Attempting to install {binary} using APT on Linux...")
        elif os_type == "Darwin":  # macOS
            install_command = ["brew", "install", binary]
            print(f"Attempting to install {binary} using Homebrew on macOS...")
        elif os_type == "Windows":
            print(f"Installation of {binary} is not supported automatically on Windows. Please install it manually.")
            raise RuntimeError(f"Please manually install {binary} on Windows.")
        else:
            raise RuntimeError(f"Unsupported operating system: {os_type}")

        # Run installation command for supported OS
        try:
            result = subprocess.run(install_command, check=True, capture_output=True, text=True)
            print(result.stdout)
            print(f"{binary} installed successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to install {binary}: {e.stderr}")


class ModuleLoader:
    def __init__(self, base_path):
        self.modules_dict = {'app': {'module': {}}}
        self.base_path = base_path
        self.required_binaries_per_module = {
            'iptables_manager': ['iptables'],
            'ipset_manager': ['ipset'],
            'ssh': ['ssh']
        }
        self._ensure_init_files(base_path)
        self._load_modules(base_path)

    def _ensure_init_files(self, base_path):
        """Ensure each directory in the modules path has an __init__.py to be recognized as a package."""
        for root, dirs, _ in os.walk(base_path):
            for dir_name in dirs:
                init_file_path = os.path.join(root, dir_name, '__init__.py')
                if not os.path.exists(init_file_path):
                    open(init_file_path, 'w').close()
                    logger.debug(f"Created missing __init__.py in {init_file_path}")

    def _load_modules(self, base_path):
        """Recursively load Python modules from the specified base path using direct file paths."""
        logger.debug(f"Loading modules from base path: {base_path}")
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    module_name = os.path.splitext(file)[0]
                    self._check_module_binaries(module_name)

                    # Full path to the module file
                    module_path = os.path.join(root, file)
                    logger.debug(f"Attempting to load module from path: {module_path}")

                    try:
                        module = self._load_module_from_path(module_name, module_path)
                        unique_key = os.path.relpath(module_path, base_path).replace(os.path.sep, '.')
                        self._add_module_to_dict(module, unique_key)
                        logger.debug(f"Successfully loaded module from path: {module_path}")
                    except Exception as e:
                        logger.error(f"Failed to load module '{module_name}' from path '{module_path}': {e}")

    def _load_module_from_path(self, module_name, module_path):
        """Load a module from a specific file path."""
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _check_module_binaries(self, module_name):
        """Check for required binaries specific to a module."""
        required_binaries = self.required_binaries_per_module.get(module_name, [])
        if required_binaries:
            binary_checker = BinaryChecker(required_binaries)
            binary_checker.check_binaries()


    def _add_module_to_dict(self, module, module_key):
        """Organize instances of classes and functions from a module into the modules dictionary."""
        module_dict = {}
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Only include classes defined within the module (not imported)
                if obj.__module__ == module.__name__:
                    # Check if __init__ has required parameters beyond 'self'
                    init_sig = inspect.signature(obj.__init__)
                    has_required_params = any(
                        param.default == param.empty and param.name != 'self'
                        for param in init_sig.parameters.values()
                    )

                    if not has_required_params:
                        try:
                            instance = obj()  # Instantiate class without required positional args
                            class_methods = {
                                method_name: {
                                    'function': getattr(instance, method_name),
                                    'help': inspect.getdoc(getattr(instance, method_name))
                                }
                                for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction)
                            }
                            module_dict[name] = {
                                'instance': instance,  # Store the instance directly
                                'methods': class_methods,
                                'help': inspect.getdoc(obj)
                            }
                        except Exception as e:
                            logger.error(f"Failed to instantiate class {name} in module {module_key}: {e}")
                    else:
                        logger.warning(f"Skipped instantiation of {name} in {module_key}: requires arguments.")
            elif inspect.isfunction(obj):
                module_dict[name] = {
                    'function': obj,
                    'help': inspect.getdoc(obj)
                }
        self.modules_dict['app']['module'][module_key] = module_dict


    def display_help(self, path):
        """Display help documentation for a specified module or function."""
        try:
            logger.debug(f"Displaying help for path: {path}")
            module_name = path[0]
            if module_name not in self.modules_dict['app']['module']:
                print("Module not found.")
                return

            module_content = self.modules_dict['app']['module'][module_name]
            print(f"\n=== Help Documentation for Module: {module_name} ===")

            for item_name, item_content in module_content.items():
                if 'methods' in item_content:
                    print(f"\nClass: {item_name}")
                    print(item_content.get('help', "No class-level documentation available."))
                    print("\nMethods:")
                    for method_name, method_info in item_content['methods'].items():
                        if not method_name.startswith('_'):
                            print(f" - {method_name}: {method_info.get('help', 'No documentation available.')}")
                elif 'function' in item_content and not item_name.startswith('_'):
                    print(f"\nFunction: {item_name}")
                    print(item_content.get('help', "No documentation available."))

            print("\n=======================================")
        except Exception as e:
            logger.error(f"Unexpected error in display_help: {e}")
