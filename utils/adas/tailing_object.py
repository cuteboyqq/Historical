from utils.adas.bbox import BoundingBox

class TailingObject:
    def __init__(self, id, bounding_box, following_distance):
        self.id = id
        self.bbox = bounding_box
        self.following_distance = following_distance