import sys
import time

class DisplayUtils:
    @staticmethod
    def show_status(role, task, status):
        """Display the status of a task with colored output.

        Args:
            role (str): The role performing the task.
            task (str): The task being performed.
            status (bool): True if the task was successful, False otherwise.
        """
        if status:
            print(f"✅ {role.capitalize():13} {task} \t \033[32mSuccessful\033[0m")
        else:
            print(f"❌ {role.capitalize():13} {task} \t \033[31mFailed\033[0m")

    @staticmethod
    def show_message(role, message):
        """Display a warning message with colored output.

        Args:
            role (str): The role issuing the warning.
            message (str): The warning message to display.
        """
        print(f"💬 {role.capitalize():13} {message}")

    @staticmethod
    def show_warning(role, message):
        """Display a warning message with colored output.

        Args:
            role (str): The role issuing the warning.
            message (str): The warning message to display.
        """
        print(f"⚠️ {role.capitalize():13} {message} \t \033[33mWarning\033[0m")

    @staticmethod
    def print_separator(char="-", length=50):
        """Print a separator line.

        Args:
            char (str): The character to use for the separator. Defaults to "-".
            length (int): The length of the separator. Defaults to 50.
        """
        print(char * length)

    @staticmethod
    def print_progress(message, progress_char="|/-\\"):
        """Print a progress message with a spinning animation.

        Args:
            message (str): The message to display.
            progress_char (str): The characters to use for the spinning animation.
        """
        for char in progress_char:
            sys.stdout.write(f'\r{message} {char}')
            sys.stdout.flush()
            time.sleep(0.1)

    @staticmethod
    def print_header(message):
        """Print a header message.

        Args:
            message (str): The header message to display.
        """
        print(f"\n🚀 {message}")
        DisplayUtils.print_separator()
        print()


    @staticmethod
    def print_main_header(message):
        head_separator = "=" * 50
        print()
        print(head_separator)
        print(f"\n🔖 {message}\n")
        print(head_separator)
        print()


