import os

class ConfigChecker:
    def __init__(self, remoteSSH, config):
        """Initializes a ConfigChecker instance.

        Args:
            remoteSSH: RemoteSSH instance
            config: Config instance
        """

        # Conneciton to the remote host
        self.remoteSSH = remoteSSH

        # Read the golden config file
        self.golden_config_path = config.test_adas_config_path
        self.golden_config_dict = self._parse_config(is_from_remote=False)

        # Read the remote config file
        self.remote_config_dict = self._parse_config(is_from_remote=True)

        # Ignore the config keys
        self.ignore_config_list = [
            "CameraHeight"
        ]

        # 
        self.is_missing_key             = False
        self.is_different_values        = False
        self.is_enable_debug_flags      = False
        self.is_enable_display_flags    = False
        self.is_enable_showtime_flags   = False
        self.result                     = False

    def _get_config_from_remote(self):
        """Gets the configuration file from the remote host.
        """
        command = f"cat /customer/adas/config/config.txt"
        return self.remoteSSH.execute_command(command)

    def _get_config_from_local(self):
        """Gets the configuration file from the local host.
        """
        if not os.path.exists(self.golden_config_path):
            raise FileNotFoundError(f"The golden config file {self.golden_config_path} does not exist.")

        with open(self.golden_config_path, "r", encoding="utf-8") as file:
            return file.read()

    def _parse_config(self, is_from_remote=True):
        """Parses the configuration file.

        Args:
            is_from_remote (bool, optional):
                Whether the configuration file is from the remote host or the golden configuration file.
                Defaults to True.
        """
        if is_from_remote:
            config_str = self._get_config_from_remote()
        else:
            config_str = self._get_config_from_local()

        config_dict = {}
        for line in config_str.split("\n"):
            if line.startswith("#"):
                continue
            else:
                res = line.split("=")
                if len(res) >= 2:
                    key = res[0][:-1]
                    _value = res[1]
                    value = _value.split('#')[0].strip()
                    config_dict[key] = value

        return config_dict

    def _is_remote_config_missing_key(self):
        """Checks if the remote configuration file is missing any keys.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        no_missing_key = True
        for key, value in self.golden_config_dict.items():
            if key not in self.remote_config_dict.keys():
                print(f"Key {key} not found in remote config")
                no_missing_key = False

        return no_missing_key

    def _is_remote_config_different_values(self):
        """Checks if the remote configuration file has different values.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        no_diff_value = True
        for key, value in self.golden_config_dict.items():
            if key in self.ignore_config_list:
                continue
            if key in self.remote_config_dict.keys() and self.remote_config_dict[key] != value:
                print(f"Key {key} has different value in remote config")
                no_diff_value = False

        return no_diff_value

    def _is_remote_config_enable_debug_flags(self):
        """Checks if the remote configuration file is disabled debug mode.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        is_debug_enable = False
        for key, value in self.remote_config_dict.items():
            # Check Debug Flags
            if key.startswith("Debug") and "Path" not in key:
                if int(value) == 1:
                    print(f"❌ Detect \"{key}\" = 1")
                    is_debug_enable = True

        return is_debug_enable

    def _is_remote_config_enable_display_flags(self):
        """Checks if the remote configuration file is disabled debug mode.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        is_display_enable = False
        for key, value in self.remote_config_dict.items():
            # Check Display Flags
            if key.startswith("Display"):
                if int(value) == 1:
                    print(f"❌ Detect \"{key}\" = 1")
                    is_display_enable = True

        return is_display_enable

    def _is_remote_config_enable_showtime_flags(self):
        """Checks if the remote configuration file is disabled debug mode.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        is_show_enable = False
        for key, value in self.remote_config_dict.items():
            # Check Show Processing Time Flags
            if key.startswith("ShowProcTime"):
                if int(value) == 1:
                    print(f"❌ Detect \"{key}\" = 1")
                    is_show_enable = True

        return is_show_enable

    def check_config(self):
        """
        Checks the configuration file on the remote host against the golden configuration file.

        Returns:
            bool: True if the configuration file is valid, False otherwise.
        """
        is_config_valid = True

        # Step1. Check if the remote config is missing any keys
        if not self._is_remote_config_missing_key():
            self.is_missing_key = True
            is_config_valid = False

        # Step2. Check if the remote config has different values
        if not self._is_remote_config_different_values():
            self.is_different_values = True
            is_config_valid = False

        # Step3. Check if the remote config is disabled debug mode
        if self._is_remote_config_enable_debug_flags():
            self.is_enable_debug_flags = True
            is_config_valid = False

        # Step4. Check if the remote config is disabled debug mode
        if self._is_remote_config_enable_display_flags():
            self.is_enable_display_flags = True
            is_config_valid = False

        # Step5. Check if the remote config is disabled debug mode
        if self._is_remote_config_enable_showtime_flags():
            self.is_enable_showtime_flags = True
            is_config_valid = False

        self.result = is_config_valid
        return is_config_valid

    def get_results(self):
        """Get the config test results

        Returns:
            dict: The config test results
        """
        results = {
            "Missing Key":                  "✅ Passed" if not self.is_missing_key else "❌ Failed",
            "Different Parameters":         "✅ Passed" if not self.is_different_values else "❌ Failed",
            "Disable All Debug Flags":      "✅ Passed" if not self.is_enable_debug_flags else "❌ Failed",
            "Disable All Display Flags":    "✅ Passed" if not self.is_enable_display_flags else "❌ Failed",
            "Disable All Show Processing Time Flags": "✅ Passed" if not self.is_enable_showtime_flags else "❌ Failed",
        }
        return results









