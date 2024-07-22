from engine.BaseDataset import BaseDataset
from task.Historical import *
from config.config import *



if __name__=="__main__":
    args = get_args()
    history = Historical(args)
    # Extract data from both files
    frame_ids_1, distances_1 = history.Draw_AI_result_to_images()

    