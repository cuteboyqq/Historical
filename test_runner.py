from datetime import datetime
from utils.remote_ssh import RemoteSSH
from test_tools.version_checker import VersionChecker
from test_tools.config_checker import ConfigChecker
from test_tools.performance_checker import PerformanceChecker
from test_tools.detection_checker import DetectionChecker
from test_tools.resource_checker import RemoteResourceChecker

__version__ = "0.0.1.alpha"

class TestRunner:
    def __init__(self, config):
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

        # Initialize the RemoteSSH object
        self.remote_ssh = RemoteSSH(
            hostname=config.host_name,
            username=config.user_name,
            password=config.password,
            port=config.port)

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

    def is_setup_success(self):
        return self.is_setup            

    def setup(self):
        separator = "-" * 50
        print("🚀 Starting device connection...")
        print(separator)
        print()

        if not self.remote_ssh.connect():
            return False

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
        
        # print("🚀 Starting test execution...")
        # print(separator)
        # print()

        # verifications = [
        #     ("Version", self.version_checker.check_versions),
        #     ("Configuration", self.config_checker.check_config),
        #     ("Performance", self.performance_checker.check_performance),
        #     ("Detection", self.detection_checker.check_detection),
        #     ("Resource", self.resource_checker.check_resource)
        # ]

        # for i, (name, check_func) in enumerate(verifications, 1):
        #     print(f"[ {i}. {name} Verification ]")
        #     print(separator)
        #     result = check_func()
        #     status = "✅ Passed" if result else "❌ Failed"
        #     if result:
        #         print(f"✅ Verification ... \033[32mPassed\033[0m \n")
        #     else:
        #         print(f"❌ Verification ... \033[31mFailed\033[0m \n")    

        #     # Store the check results
        #     self.check_results[name] = {
        #         "status": status,
        #         "result": result
        #     }

        # print("🏁 All tests completed")

        try:
            
            print("🚀 Starting test execution...\n")

            verifications = [
                ("Version", self.version_checker.check_versions),
                ("Configuration", self.config_checker.check_config),
                ("Performance", self.performance_checker.check_performance),
                ("Detection", self.detection_checker.check_detection),
                ("Resource", self.resource_checker.check_resource)
            ]

            for i, (name, check_func) in enumerate(verifications, 1):
                print(f"{i}. {name} verification...")
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

            print("🏁 All tests completed")

        except Exception as e:
            print(f"❗ An error occurred during testing: {str(e)}")
        finally:
            self.teardown()

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
        report.append(f"Host: {self.config.host_name}")
        report.append(f"User: {self.config.user_name}")
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

    runner = TestRunner(config)
    if runner.is_setup_success():
        runner.run_tests()

    report = runner.gen_test_report()
    print(report)