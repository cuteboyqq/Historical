from task.Historical import *
from config.config import *



if __name__=="__main__":
    args = get_args()
    history = Historical(args)

    DRAW_AI_RESULT_ON_IMAGES = True
    PLOTDISTANCE = False

    if DRAW_AI_RESULT_ON_IMAGES:
        frame_ids_1, distances_1 = history.draw_AI_result_to_images()

    if PLOTDISTANCE:
        history.compare_distance_in_multiple_csv_file()