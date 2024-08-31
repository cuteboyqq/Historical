from datetime import datetime
from utils.display import DisplayUtils
from utils.connection_handler import ConnectionHandler
from utils.adas_runner import AdasRunner
from test_tools.version_checker import VersionChecker
from test_tools.config_checker import ConfigChecker
from test_tools.performance_checker import PerformanceChecker
from test_tools.detection_checker import DetectionChecker
from test_tools.resource_checker import RemoteResourceChecker

__version__ = "0.0.1"

class TestRunner:
    def __init__(self, connection, config):
        """
        Initialize the TestRunner object
        Args:
            config (Args): The configuration object
        """
        head_separator = "=" * 50
        print()
        print(head_separator)
        print(f"\n🔖 ADAS Test Runner ( v{__version__} )\n")
        print(head_separator)
        print()

        # Initialize the configuration object
        self.config = config

        # Initialize the message displaying object
        self.display = DisplayUtils()

        # Initialize the ADAS runner object
        self.adas_runner = AdasRunner(connection, config)

        # Initialize the RemoteSSH object
        self.remote_ssh = connection.remote_ssh

        # Initialize the checker objects
        self.version_checker        = None
        self.config_checker         = None
        self.performance_checker    = None
        self.detection_checker      = None
        self.resource_checker       = None

        # Setup the checker objects
        self.is_setup               = self.setup()

        # Initialize the check results
        self.check_results          = {}
        self.role                   = "Device"

    def is_setup_success(self):
        return self.is_setup

    def setup(self):
        """Setup the test runner

        Returns:
            bool: True if the setup is successful, False otherwise
        """
        separator = "-" * 50
        print('\n')
        print("🚀 Starting checker initialization...")
        print(separator)
        print()

        checker_list = [
            ("version", VersionChecker),
            ("config", ConfigChecker),
            ("performance", PerformanceChecker),
            ("detection", DetectionChecker),
            ("resource", RemoteResourceChecker)
        ]

        for name, checker_class in checker_list:
            setattr(self, f"{name.lower()}_checker", checker_class(self.remote_ssh, self.config))
            print(f"✅ {name.capitalize():13} Checker \t \033[32mInitialized\033[0m")
        print('\n')

        return True

    def run_tests(self):
        """
        Run the tests
        """
        separator = "-" * 50
        print("🚀 Starting test execution...")
        print(separator)
        print()

        # Stop ADAS
        if not self.adas_runner.stop_adas():
            self.display.show_status(self.role, "Failed to stop ADAS", False)
            return False

        # Modify remote config
        if not self.adas_runner.modify_remote_config(enable_show_debug_profiling=True):
            self.display.show_status(self.role, "Failed to modify remote config", False)
            return False

        # Run remote ADAS script
        if not self.adas_runner.run_adas():
            self.display.show_status(self.role, "Failed to run remote ADAS script", False)
            return False

        verifications = [
            ("Version", self.version_checker.check_versions),
            ("Configuration", self.config_checker.check_config),
            ("Performance", self.performance_checker.check_performance),
            ("Detection", self.detection_checker.check_detection),
            ("Resource", self.resource_checker.check_resource)
        ]

        for i, (name, check_func) in enumerate(verifications, 1):
            print(f"[ {i}. {name} Verification ]")
            print(separator)
            result = check_func()
            status = "✅ Passed" if result else "❌ Failed"
            if result:
                print(f"✅ Verification ... \033[32mPassed\033[0m \n")
            else:
                print(f"❌ Verification ... \033[31mFailed\033[0m \n")

            # Store the check results
            self.check_results[name] = {
                "status": status,
                "result": result
            }

        # Modify remote config
        if not self.adas_runner.modify_remote_config(enable_show_debug_profiling=False):
            self.display.show_status(self.role, "Failed to modify remote config", False)
            return False

        print("🏁 All tests completed")

    def teardown(self):
        """
        Disconnect from the device
        """
        print("Disconnecting from the device...")
        self.remote_ssh.disconnect()

    def gen_test_report(self):
        """
        Generate the test report
        """
        report = []
        head_separator = "=" * 50
        separator = "-" * 50

        def format_results(results):
            if not results:
                return []
            max_key_length = max(len(str(key)) for key in results.keys())
            return [f"{str(key):<{max_key_length}} : {str(value):>}" for key, value in results.items()]

        # Test information
        report.append("\n")
        report.append(head_separator)
        report.append("\n📊 [ ADAS Test Report ]\n")
        report.append(head_separator)
        report.append(f"ADAS Test Runner v{__version__}")
        report.append(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Host: {self.config.camera_host_name}")
        report.append(f"User: {self.config.camera_user_name}")
        report.append(head_separator)

        # Version information
        report.append("\n🔢 [ Version Information ]")
        report.append(separator)
        report.extend(format_results(self.version_checker.get_results()))
        report.append(separator)

        # Configuration test results
        report.append("\n⚙️ [ Configuration Test Results ]")
        report.append(separator)
        report.extend(format_results(self.config_checker.get_results()))
        report.append(separator)

        # Performance test results
        report.append("\n⚡ [ Performance Test Results ]")
        report.append(separator)
        report.extend(format_results(self.performance_checker.get_results()))
        # report.append(f"Monitoring Period: {self.config.test_check_duration} seconds")
        report.append(separator)

        # Detection test results
        report.append("\n🔍 [ Detection Test Results ]")
        report.append(separator)
        report.extend(format_results(self.detection_checker.get_results()))
        # report.append(f"Monitoring Period: {self.config.test_check_duration} seconds")
        report.append(separator)

        # Resource test results
        report.append("\n💻 [ Resource Test Results ]")
        report.append(separator)
        report.extend(format_results(self.resource_checker.get_results()))
        # report.append(f"Monitoring Period: {self.config.test_check_duration} seconds")
        report.append(separator)

        # Overall test results
        report.append("\n🏁 [ Overall Test Results ]")
        report.append(head_separator)
        checkers = [
            ("Version", self.version_checker),
            ("Configuration", self.config_checker),
            ("Performance", self.performance_checker),
            ("Detection", self.detection_checker),
            ("Resource", self.resource_checker)
        ]
        overall_results = {}
        for name, checker in checkers:
            # results = checker.get_results()
            status = "✅ Passed" if checker.result else "❌ Failed"
            overall_results[name] = status
        report.extend(format_results(overall_results))
        report.append(separator)

        # Summary
        total_tests = len(overall_results)
        passed_tests = sum(1 for status in overall_results.values() if status == "✅ Passed")
        summary = {
            "Total Tests": total_tests,
            "Passed Tests": passed_tests,
            "Failed Tests": total_tests - passed_tests,
            "Pass Rate": f"{passed_tests / total_tests * 100:.2f}%"
        }
        report.extend(format_results(summary))

        return "\n".join(report)

if __name__ == "__main__":
    import yaml
    from config.args import Args

    # Load the YAML configuration file and return its content as a dictionary
    def load_config(config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    # Load configuration settings from the specified YAML file
    config_yaml = load_config('config/config.yaml')

    # Initialize Args object with the loaded configuration
    config = Args(config_yaml)

    # Initialize ConnectionHandler
    connection_handler = ConnectionHandler(config)

    # Check if the connection is setup successfully
    if connection_handler.is_setup_success():

        # Initialize TestRunner
        runner = TestRunner(connection_handler, config)

        # Run the tests
        runner.run_tests()

        #
        connection_handler.close_connection()

        # Generate the test report
        report = runner.gen_test_report()
        print(report)