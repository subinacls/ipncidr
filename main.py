# main.py

import os
import logging
import inspect
from core.module_loader import ModuleLoader
from core import shared as shared

# Configure logging
logging.basicConfig(filename='logs/app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main_menu():
    print("\nPlease select an option:")
    print("1. List available modules and explore contents")
    print("2. Run a function in an initialized module")
    print("3. Display help for a module or function")
    print("4. Exit")

def handle_navigation(choice):
    """Handle navigation based on user input."""
    if choice == "88":
        print("Returning to the previous menu...")
        return "back"
    elif choice == "99":
        print("Returning to the main menu...")
        return "main"
    elif choice == "00":
        print("Exiting application.")
        exit(0)
    return None

def display_argument_table(method_sig, user_args):
    """Display a table of arguments for the method, marking them as Mandatory or Optional."""
    args_table = []
    for idx, param in enumerate(method_sig.parameters.values(), 1):
        if param.name == 'self':
            continue
        arg_type = "Mandatory" if param.default == param.empty else "Optional"
        current_value = user_args.get(param.name, param.default if param.default != param.empty else "N/A")
        args_table.append((idx, param.name, arg_type, current_value))

    print("\nArgument Table:")
    print("{:<4} {:<15} {:<10} {:<20}".format("No.", "Argument", "Type", "Current Value"))
    print("-" * 50)
    for idx, name, arg_type, current_value in args_table:
        print("{:<4} {:<15} {:<10} {:<20}".format(idx, name, arg_type, str(current_value)))
    return args_table

def main():
    shared.info and logger.info("Starting Module Loader Interactive Environment")
    base_path = os.path.join(os.path.dirname(__file__), 'modules')
    loader = ModuleLoader(base_path=base_path)

    while True:
        main_menu()
        choice = input("Enter your choice: ")

        if choice == "1":
            print("\n=== Available Modules and Initialized Classes ===")
            for module_key, module_content in loader.modules_dict['app']['module'].items():
                print(f"\nModule: {module_key}")
                for class_name, class_info in module_content.items():
                    if 'instance' in class_info:
                        print(f"  Initialized Class: {class_name}")
            print("\n=======================================")

        elif choice == "2":
            return_to_main = False
            while not return_to_main:
                print("\n=== Initialized Classes ===")
                module_class_pairs = []
                for module_key, module_content in loader.modules_dict['app']['module'].items():
                    for class_name, class_info in module_content.items():
                        if 'instance' in class_info:
                            display_text = f"{module_key} - {class_name}"
                            module_class_pairs.append((display_text, class_info['instance']))

                for idx, (display_text, _) in enumerate(module_class_pairs, 1):
                    print(f"{idx}. {display_text}")

                module_choice = input("\nSelect a module by number or enter '88' to go back, '99' for main menu, '00' to exit: ")
                nav_result = handle_navigation(module_choice)
                if nav_result == "back":
                    break
                elif nav_result == "main":
                    return_to_main = True
                    break

                try:
                    module_choice = int(module_choice) - 1
                    selected_instance = module_class_pairs[module_choice][1]
                except (ValueError, IndexError):
                    print("Invalid selection. Please select a valid module and class number.")
                    continue

                while not return_to_main:
                    methods = [m for m in dir(selected_instance) if not m.startswith('_') and callable(getattr(selected_instance, m))]
                    for idx, method_name in enumerate(methods, 1):
                        print(f"{idx}. {method_name}")

                    method_choice = input("\nSelect a method by number to execute or enter '88' to go back, '99' for main menu, '00' to exit: ")
                    nav_result = handle_navigation(method_choice)
                    if nav_result == "back":
                        break
                    elif nav_result == "main":
                        return_to_main = True
                        break

                    try:
                        method_choice = int(method_choice) - 1
                        selected_method = methods[method_choice]
                        method_to_call = getattr(selected_instance, selected_method)

                        method_sig = inspect.signature(method_to_call)
                        user_args = {}
                        has_args = any(param.name != 'self' for param in method_sig.parameters.values())

                        if not has_args:
                            print(f"\nExecuting '{selected_method}' with no arguments required.")
                            result = method_to_call()
                            print(f"\nResult: {result}")
                            continue

                        while True:
                            os.system('clear')
                            print(f"Editing arguments for method '{selected_method}':")
                            args_table = display_argument_table(method_sig, user_args)

                            arg_choice = input("\nSelect an argument by number to edit, or enter '99' to finish setup: ")
                            if arg_choice == "99":
                                break

                            try:
                                arg_idx = int(arg_choice) - 1
                                arg_name = args_table[arg_idx][1]
                                new_value = input(f"Enter value for '{arg_name}': ")
                                user_args[arg_name] = new_value
                            except (ValueError, IndexError):
                                print("Invalid selection. Please select a valid argument number.")
                                continue

                        try:
                            result = method_to_call(**user_args)
                            print(f"\nResult: {result}")
                        except Exception as e:
                            print(f"Error executing method {selected_method}: {e}")
                            logger.error(f"Failed to execute method {selected_method} with arguments {user_args}: {e}")

                    except (ValueError, IndexError, AttributeError) as e:
                        print(f"Error selecting method: {e}")
                        logger.error(f"Error selecting method: {e}")

        elif choice == "3":
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

        elif choice == "4":
            print("Exiting Module Loader Interactive Environment.")
            break

        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
