from utils.adas.point import Point

class LaneInfo:
    def __init__(self, lane_info_dict):
        self.is_detect_line = lane_info_dict["isDetectLine"]
        self.p_left_carhood = Point(lane_info_dict["pLeftCarhood.x"], lane_info_dict["pLeftCarhood.y"])
        self.p_right_carhood = Point(lane_info_dict["pRightCarhood.x"], lane_info_dict["pRightCarhood.y"])
        self.p_left_far = Point(lane_info_dict["pLeftFar.x"], lane_info_dict["pLeftFar.y"])
        self.p_right_far = Point(lane_info_dict["pRightFar.x"], lane_info_dict["pRightFar.y"])