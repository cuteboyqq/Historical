from task.Historical import *
from config.config import *
from utils.connection import Connection


if __name__=="__main__":
    args = get_args()
    history = Historical(args)

    DRAW_AI_RESULT_ON_IMAGES = False
    PLOT_DISTANCE = False
    COVERT_TO_RAW_VIDEO=False
    SEMI_ONLINE_DRAW_AI_RESULT_ON_IMAGES = False
    ONLINE_DRAW_AI_RESULT_ON_IMAGES = True
    OFFLINE_DRAW_AI_RESULT_ON_IMAGES = False

    if DRAW_AI_RESULT_ON_IMAGES:
        # frame_ids_1, distances_1 = history.draw_AI_result_to_images()
        history.visualize_hisotircal_main()

    if PLOT_DISTANCE:
        # history.compare_distance_in_multiple_csv_file()
        history.plot_distance_in_one_csv_file()

    if COVERT_TO_RAW_VIDEO:
        history.save_rawimages_to_videoclip()

    if SEMI_ONLINE_DRAW_AI_RESULT_ON_IMAGES:
        connect = Connection(args)
        connect.start_server()

    if ONLINE_DRAW_AI_RESULT_ON_IMAGES:
        connect = Connection(args)
        connect.start_server_ver2()

    if OFFLINE_DRAW_AI_RESULT_ON_IMAGES:
        history.parse_live_mode_historical_csv_file()
    
 