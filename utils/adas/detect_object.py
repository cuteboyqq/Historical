from utils.adas.bbox import BoundingBox

class DetectObject:
    def __init__(self, bounding_box):
        self.bbox = bounding_box