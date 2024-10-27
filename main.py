# main.py

import os
import logging
import inspect
from module_loader import ModuleLoader
import shared

# Configure logging
logging.basicConfig(filename='logs/app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global dictionary to store initialized module instances
module_instances = {}

def main():
    shared.info and logger.info("Starting Module Loader Interactive Environment")
    base_path = os.path.join(os.path.dirname(__file__), 'modules')
    loader = ModuleLoader(base_path=base_path)

    while True:
        print("\nPlease select an option:")
        print("1. List available modules and explore contents")
        print("2. Initialize a module with configurable arguments")
        print("3. Run a function in an initialized module")
        print("4. Display help for a module or function")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            # List available modules and allow exploration
            if 'module' in loader.modules_dict['app'] and loader.modules_dict['app']['module']:
                print("\n=== Available Modules ===")
                # Sort module keys alphabetically
                module_keys = sorted(loader.modules_dict['app']['module'].keys())
                for idx, module_name in enumerate(module_keys, 1):
                    print(f"{idx}. {module_name}")
                print("\n=======================================")

                try:
                    module_choice = int(input("\nSelect a module by number to explore: ")) - 1
                    selected_module_key = module_keys[module_choice]
                except (ValueError, IndexError):
                    print("Invalid selection. Please select a valid module number.")
                    continue

                # Show classes and functions in the selected module
                module_content = loader.modules_dict['app']['module'][selected_module_key]
                print(f"\n=== Contents of Module: {selected_module_key} ===")
                classes = [name for name, content in module_content.items() if 'methods' in content]
                functions = [name for name, content in module_content.items() if 'function' in content]

                if classes:
                    print("\nClasses:")
                    for idx, class_name in enumerate(classes, 1):
                        print(f"{idx}. {class_name}")
                if functions:
                    print("\nFunctions:")
                    for idx, function_name in enumerate(functions, 1):
                        print(f"{idx}. {function_name}")

                if classes:
                    try:
                        class_choice = int(input("\nSelect a class by number to view its methods (or press Enter to skip): ")) - 1
                        selected_class_name = classes[class_choice]
                        class_content = module_content[selected_class_name]
                    except (ValueError, IndexError):
                        print("No class selected. Returning to main menu.")
                        continue

                    # Display methods in the selected class
                    methods = [name for name in class_content['methods'] if not name.startswith('_')]
                    if methods:
                        print(f"\nMethods in class '{selected_class_name}':")
                        for idx, method_name in enumerate(methods, 1):
                            print(f"  {idx}. {method_name}")

                    print("\n=======================================")
                else:
                    print("No classes available to drill down further.")
            else:
                print("No modules were found or loaded. Please check the modules directory and try again.")

        elif choice == "2":
            # Initialize a module
            global module_instances
            modules = list(loader.modules_dict['app']['module'].keys())
            for idx, module_name in enumerate(modules, 1):
                print(f"{idx}. {module_name}")
            try:
                module_choice = int(input("\nSelect a module by number to initialize: ")) - 1
                selected_module = modules[module_choice]
            except (ValueError, IndexError):
                print("Invalid selection. Please select a valid module number.")
                continue

            # Display classes in the selected module for initialization
            module_content = loader.modules_dict['app']['module'][selected_module]
            classes = [item_name for item_name, item_content in module_content.items() if 'methods' in item_content]
            for idx, class_name in enumerate(classes, 1):
                print(f"{idx}. {class_name}")
            try:
                class_choice = int(input("\nSelect a class by number to initialize: ")) - 1
                selected_class = classes[class_choice]
                class_content = module_content[selected_class]
                class_ref = class_content['class_ref']
            except (ValueError, IndexError):
                print("Invalid selection. Please select a valid class number.")
                continue

            # Dynamically build settings based on the class __init__ parameters
            init_sig = inspect.signature(class_ref.__init__)
            init_settings = {
                param.name: f"default_{param.name}" if param.default == param.empty else param.default
                for param in init_sig.parameters.values()
                if param.name != "self"
            }

            # Add or retrieve module settings in shared config
            settings = shared.add_module_settings(selected_class, init_settings)

            # Collect arguments for initialization using these settings
            args = []
            kwargs = {}
            print(f"\nInitializing class '{selected_class}' with settings: {settings}")
            for param in init_sig.parameters.values():
                if param.name == "self":
                    continue
                if param.default == param.empty:
                    args.append(input(f"Enter value for '{param.name}' (required): "))
                else:
                    default_val = settings.get(param.name, param.default)
                    user_input = input(f"Enter value for '{param.name}' (default={default_val}): ") or default_val
                    kwargs[param.name] = user_input

            # Instantiate the class with the provided arguments
            try:
                instance = class_ref(*args, **kwargs)
                module_instances[selected_class] = instance
                print(f"'{selected_class}' has been initialized successfully and stored for future use.")
                logger.debug(f"Instance of {selected_class} stored with args: {args}, kwargs: {kwargs}")
            except Exception as e:
                print(f"Error initializing the class: {e}")
                logger.error(f"Error initializing {selected_class} with args {args} and kwargs {kwargs}: {e}")

        elif choice == "3":
            # Run a function in an initialized module
            if not module_instances:
                print("No modules have been initialized yet. Please initialize a module first.")
                logger.debug("No initialized modules found.")
                continue

            # List initialized classes for method execution
            print("\n=== Initialized Modules ===")
            for idx, class_name in enumerate(module_instances.keys(), 1):
                print(f"{idx}. {class_name}")

            try:
                class_choice = int(input("\nSelect a class by number to execute its methods: ")) - 1
                selected_class_name = list(module_instances.keys())[class_choice]
                instance = module_instances[selected_class_name]
                logger.debug(f"Selected class instance: {selected_class_name}")
            except (ValueError, IndexError):
                print("Invalid selection. Please select a valid class number.")
                continue

            # Display and select methods for execution
            methods = [m for m in dir(instance) if not m.startswith('_') and callable(getattr(instance, m))]
            for idx, method_name in enumerate(methods, 1):
                print(f"{idx}. {method_name}")
            try:
                method_choice = int(input("\nSelect a method by number to execute: ")) - 1
                selected_method = methods[method_choice]
                method_to_call = getattr(instance, selected_method)
            except (ValueError, IndexError, AttributeError) as e:
                print(f"Error selecting or executing method: {e}")
                logger.error(f"Error selecting method: {e}")
                continue

            # Collect arguments and execute the method
            args = []
            kwargs = {}
            print("Enter arguments for the function (or press Enter to skip):")
            sig = inspect.signature(method_to_call)
            for param in sig.parameters.values():
                if param.name == "self":
                    continue
                if param.default == param.empty:
                    args.append(input(f"Enter argument for '{param.name}': "))
                else:
                    default_val = param.default
                    kwargs[param.name] = input(f"Enter argument for '{param.name}' (default={default_val}): ") or default_val

            try:
                result = method_to_call(*args, **kwargs)
                if result is not None:
                    print(f"\nResult: {result}")
                else:
                    print("\nResult: No output returned.")
                logger.info(f"Executed {selected_class_name}.{selected_method} with result: {result}")
            except Exception as e:
                print(f"Error executing the function: {e}")
                logger.error(f"Error executing {selected_class_name}.{selected_method}: {e}")

        elif choice == "4":
            print("\n=== Help Documentation ===")
            modules = list(loader.modules_dict['app']['module'].keys())
            for idx, module_name in enumerate(modules, 1):
                print(f"{idx}. {module_name}")
            try:
                module_choice = int(input("\nSelect a module by number: ")) - 1
                selected_module = modules[module_choice]
                loader.display_help([selected_module])
            except (ValueError, IndexError):
                print("Invalid selection. Please select a valid module number.")

        elif choice == "5":
            print("Exiting Module Loader Interactive Environment.")
            break

        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
