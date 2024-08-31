from datetime import datetime
from utils.display import DisplayUtils
# from visualize_tools.visualizer_online import VisualizerOnline
# from visualize_tools.visualizer_semionline import VisualizerSemiOnline
# from visualize_tools.visualizer_offline import VisualizerOffline
from task.visualizer_online import VisualizerOnline
from task.visualizer_semionline import VisualizerSemiOnline
from task.visualizer_offline import VisualizerOffline

__version__ = "0.0.1"

class VisualizeRunner:
    def __init__(self, connection_handler, config):
        """Initialize the VisualizeRunner object.

        Args:
            config (Args): The configuration object containing all settings.
        """
        self.display = DisplayUtils()
        self.display.print_main_header(f"ADAS Visualize Runner ( v{__version__} )")

        # Store the configuration object
        self.config = config

        # Initialize the Visualizer object based on the mode
        self.visualizer = None
        if self.config.visualize_mode == "online":
            self.visualizer = VisualizerOnline(connection_handler, self.config)
        elif self.config.visualize_mode == "semi-online":
            self.visualizer = VisualizerSemiOnline(connection_handler, self.config)
        elif self.config.visualize_mode == "offline":
            self.visualizer = VisualizerOffline(connection_handler, self.config)
        else:
            raise ValueError(f"Invalid mode: {self.config.mode}")

    def run_visualize(self):
        """Run the ADAS visualization process.
        """
        self.visualizer.run()

        print("🏁 ADAS visualization stopped")


# if __name__ == "__main__":
#     import yaml
#     from config.args import Args

#     def load_config(config_file):
#         """Load the YAML configuration file and return its content as a dictionary.

#         Args:
#             config_file (str): Path to the YAML configuration file.

#         Returns:
#             dict: Configuration settings loaded from the YAML file.
#         """
#         with open(config_file, 'r') as file:
#             config = yaml.safe_load(file)
#         return config

#     # Load configuration settings from the specified YAML file
#     config_yaml = load_config('config/config.yaml')

#     # Initialize Args object with the loaded configuration
#     config = Args(config_yaml)

#     if config.visualize_mode == "offline":
#         # Create VisualizeRunner instance
#         runner = VisualizeRunner(None, config)
#         # Run the visualization
#         runner.run_visualize()
#     else:
#         from utils.connection_handler import ConnectionHandler

#         connection_handler = ConnectionHandler(config)
#         # Check if the connection is setup successfully
#         if connection_handler.is_setup_success():

#             # Create VisualizeRunner instance
#             runner = VisualizeRunner(connection_handler, config)

#             # Run the visualization
#             runner.run_visualize()

#             connection_handler.close_connection()