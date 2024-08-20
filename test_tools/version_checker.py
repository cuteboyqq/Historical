
class VersionChecker:
    def __init__(self, remote_ssh, config):

        # Connection to the remote host
        self.remote_host = remote_ssh

        # Get the versions
        self.firmware_version = None
        self.mcu_version      = None
        self.adas_version     = None
        self._parse_remote_versions()

        # Target versions
        self.target_firmware_version = config.test_version_fw_version
        self.target_mcu_version = config.test_version_mcu_version
        self.target_adas_version = config.test_version_adas_version

        # Result
        self.result = False

    def _get_versions(self):
        """
        Get the versions of the remote host.

        Returns:
            versions_dict (dict): The versions of the remote host.
        """
        versions_dict = {
            "firmware_version": self.firmware_version,
            "mcu_version": self.mcu_version,
            "adas_version": self.adas_version
        }
        return versions_dict

    def _parse_remote_versions(self):
        """
        Parse the versions of the remote host.
        """
        command = "cat /etc/WNC_VERSION"
        versions_str = self.remote_host.execute_command(command)
        self.firmware_version = self._get_firmware_version(versions_str)
        self.mcu_version = self._get_mcu_version(versions_str)
        self.adas_version = self._get_adas_version(versions_str)

    def _get_firmware_version(self, versions_str):
        """
        Get the firmware version of the remote host.
        Args:
            versions_str (str): The versions string.
        Returns:
            firmware_version (str): The firmware version.
        """
        firmware_version = None
        for line in versions_str.split("\n"):
            if line.startswith("WNC_INTERNAL_VERSION"):
                key, value = line.split("=")
                firmware_version = value

        return firmware_version

    def _get_mcu_version(self, versions_str):
        """
        Get the mcu version of the remote host.
        Args:
            versions_str (str): The versions string.
        Returns:
            mcu_version (str): The mcu version.
        """
        mcu_version = None
        for line in versions_str.split("\n"):
            if line.startswith("MCU_BUILD_VERSION"):
                key, value = line.split("=")
                mcu_version = value

        return mcu_version

    def _get_adas_version(self, versions_str):
        """
        Get the adas version of the remote host.
        Args:
            versions_str (str): The versions string.
        Returns:
            adas_version (str): The adas version.
        """
        adas_version = None
        for line in versions_str.split("\n"):
            if line.startswith("ADAS_VERSION"):
                key, value = line.split("=")
                adas_version = value

        return adas_version

    def check_versions(self):
        """
        Check the versions of the remote host.
        Returns:
            True if the versions are correct, False otherwise.
        """
        is_version_ok = True

        # Get the versions
        versions_dict = self._get_versions()

        # Step1. Check firmware version
        if versions_dict["firmware_version"] != self.target_firmware_version:
            print(f"❌ Firmware version mismatch: \
                {versions_dict['firmware_version']} != {self.target_firmware_version}")
            is_version_ok = False

        # Step2. Check mcu version
        if versions_dict["mcu_version"] != self.target_mcu_version:
            print(f"❌ MCU version mismatch: \
                {versions_dict['mcu_version']} != {self.target_mcu_version}")
            is_version_ok = False

        # Step3. Check adas version
        if versions_dict["adas_version"] != self.target_adas_version:
            print(f"❌ ADAS version mismatch: \
                {versions_dict['adas_version']} != {self.target_adas_version}")
            is_version_ok = False

        self.result = is_version_ok
        return is_version_ok

    def get_results(self):
        """Get the version results

        Returns:
            dict: The version results
        """
        res = "\t ✅ Passed" if self.result else "\t ❌ Failed"
        results = {
            "Firmware Version": self.firmware_version + res,
            "MCU Version": self.mcu_version + res,
            "ADAS Version": self.adas_version + res,
            # "overall": "✅ Passed" if self.result else "❌ Failed"
        }
        return results




