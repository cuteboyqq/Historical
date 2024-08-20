import json
import pytz
from datetime import datetime

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class LaneInfo:
    def __init__(self, lane_info_dict):
        self.is_detect_line = lane_info_dict["isDetectLine"]
        self.p_left_carhood = Point(lane_info_dict["pLeftCarhood.x"], lane_info_dict["pLeftCarhood.y"])
        self.p_right_carhood = Point(lane_info_dict["pRightCarhood.x"], lane_info_dict["pRightCarhood.y"])
        self.p_left_far = Point(lane_info_dict["pLeftFar.x"], lane_info_dict["pLeftFar.y"])
        self.p_right_far = Point(lane_info_dict["pRightFar.x"], lane_info_dict["pRightFar.y"])

class BoundingBox:
    def __init__(self, x1, y1, x2, y2, label, confidence):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.label = label
        self.confidence = confidence

class DetectObject:
    def __init__(self, bounding_box):
        self.bbox = bounding_box

class TailingObject:
    def __init__(self, id, bounding_box, following_distance):
        self.id = id
        self.bbox = bounding_box
        self.following_distance = following_distance

class AdasLogParser:
    def __init__(self):
        """
        Initialize the AdasLogParser class.
        """
        self.timestamp          = None
        self.frame_id           = None
        self.tailing_objs       = None
        self.vanishing_y_objs   = None
        self.adas_objs          = None
        self.lane_objs          = None
        self.detect_vehicle_objs = {}
        self.detect_pedestrian_objs = {}
        # Tailing Object
        self.tailing_obj        = None

        # Inference Time
        self.inference_time     = None

        # Buffer Size
        self.buffer_size        = None

        # Debug
        self.debug_objs         = None

        # Detect Object List
        self.detect_vehicle_list    = []
        self.detect_pedestrian_list = []

    def _parse_timestamp(self, timestamp_str):
        """
        Parse the timestamp from the log string.

        Args:
            timestamp_str (str): The timestamp string.
        """
        # Example: 2024-08-09T17:54:31.291871+00:00,syslog.notice ...
        timestamp_str = timestamp_str.split("+00:00")[0]
        dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
        dt_utc = dt.astimezone(pytz.UTC)
        timestamp = dt_utc.timestamp()
        return timestamp

    def _get_detect_obj(self):
        """
        Get the detect object list.
        """
        self.detect_vehicle_list = []
        self.detect_pedestrian_list = []
        self.detect_cyclist_list = []

        for obj in self.detect_vehicle_objs:
            x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
            x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
            label = obj["detectObj.label"]
            confidence = obj["detectObj.confidence"]
            bbox = BoundingBox(x1, y1, x2, y2, label, confidence)
            detect_obj = DetectObject(bbox)
            self.detect_vehicle_list.append(detect_obj)

        for obj in self.detect_pedestrian_objs:
            x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
            x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
            label = obj["detectObj.label"]
            confidence = obj["detectObj.confidence"]
            bbox = BoundingBox(x1, y1, x2, y2, label, confidence)
            detect_obj = DetectObject(bbox)
            self.detect_pedestrian_list.append(detect_obj)

    def parse(self, log_str):
        """
        Parse the adas log string.

        Args:
            log_str (str): The adas log string.
        """
        res = log_str.split("json:")
        if len(res) >= 2:
            [timestamp_str, json_str] = res
            json_str = json_str.strip().strip('"')
            # Replace escaped double quotes with single quotes
            json_str = json_str.replace('""', '"')

            # try:
            json_log = json.loads(json_str)
            frame_content = json_log["frame_ID"]
            self.timestamp = self._parse_timestamp(timestamp_str)
            # print(f"\nself.timestamp = {self.timestamp}")

            self.frame_id = list(frame_content.keys())[0]
            # print(f"\nself.frame_id = {self.frame_id}")

            self.adas_event_objs = frame_content[self.frame_id]["ADAS"][0]
            # print(f"\nself.adas_event_objs = {self.adas_event_objs}")

            if "tailingObj" in frame_content[self.frame_id].keys():
                self.tailing_objs = frame_content[self.frame_id]["tailingObj"]
            # print(f"\nself.tailing_objs = {self.tailing_objs}")

            if "vanishLineY" in frame_content[self.frame_id].keys():
                self.vanishing_y_objs = frame_content[self.frame_id]["vanishLineY"]
            # print(f"\nself.vanishing_y_objs = {self.vanishing_y_objs}")

            if "detectObj" in frame_content[self.frame_id]:
                if "VEHICLE" in frame_content[self.frame_id]["detectObj"].keys():
                    self.detect_vehicle_objs = \
                        frame_content[self.frame_id]["detectObj"]["VEHICLE"]

                if "HUMAN" in frame_content[self.frame_id]["detectObj"].keys():
                    self.detect_pedestrian_objs = \
                        frame_content[self.frame_id]["detectObj"]["HUMAN"]

            if "LaneInfo" in frame_content[self.frame_id].keys():
                self.lane_objs = frame_content[self.frame_id]["LaneInfo"]

            if "debugProfile" in frame_content[self.frame_id].keys():
                self.debug_objs = frame_content[self.frame_id]["debugProfile"]

            # Get the detect object list
            self._get_detect_obj()

            # except json.JSONDecodeError as e:
            #     print(f"JSON parsing error: {str(e)}")
            #     print(f"Problematic JSON string: {json_str}")
            # except Exception as e:
            #     print(f"An error occurred while parsing: {str(e)}")
            #     print(frame_content)

    def get_timestamp(self):
        """
        Get the timestamp.

        Returns:
            float: The timestamp.
        """
        return self.timestamp

    def get_frame_id(self):
        """
        Get the frame id.

        Returns:
            int: The frame id.
        """
        return int(self.frame_id)

    def get_lane_info(self):
        """
        Get the lane info.

        Returns:
            LaneInfo: The lane info.
        """
        for obj in self.lane_objs:
            print(obj)
            lane_info = LaneInfo(obj)
            return lane_info

    def get_vanishing_line_y(self):
        """
        Get the vanishing line y.

        Returns:
            float: The vanishing line y.
        """
        for obj in self.vanishing_y_objs:
            return float(obj["vanishlineY"])

    def get_fcw_event(self):
        """
        Get the fcw event.

        Returns:
            bool: The fcw event.
        """
        if self.adas_event_objs["FCW"] == "true":
            return True
        else:
            return False

    def get_ldw_event(self):
        """
        Get the ldw event.

        Returns:
            bool: The ldw event.
        """
        if self.adas_event_objs["LDW"] == "true":
            return True
        else:
            return False

    def get_detect_vehicle_list(self):
        """
        Get the detect vehicle list.

        Returns:
            list: The detect vehicle list.
        """
        return self.detect_vehicle_list

    def get_detect_pedestrian_list(self):
        """
        Get the detect pedestrian list.

        Returns:
            list: The detect pedestrian list.
        """
        return self.detect_pedestrian_list

    def get_tailing_obj(self):
        """
        Get the tailing object.

        Returns:
            TailingObject: The tailing object.
        """
        for obj in self.tailing_objs:
            x1, y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
            x2, y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
            following_distance = obj["tailingObj.distanceToCamera"]
            obj_id = obj["tailingObj.id"]
            label = obj["tailingObj.label"]
            confidence = 0
            bbox = BoundingBox(x1, y1, x2, y2, label, confidence)
            self.tailing_obj = TailingObject(obj_id, bbox, following_distance)
            return self.tailing_obj

    def get_inference_time(self):
        """
        Get the inference time.

        Returns:
            float: The inference time.
        """
        if self.debug_objs is None:
            return None

        for obj in self.debug_objs:
            self.inference_time = obj["inferenceTime"]
            return self.inference_time

    def get_buffer_size(self):
        """
        Get the input frame buffer size.

        Returns:
            float: The buffer size.
        """
        if self.debug_objs is None:
            return None

        for obj in self.debug_objs:
            self.buffer_size = obj["bufferSize"]
            return self.buffer_size