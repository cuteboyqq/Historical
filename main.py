from task.Historical import *
# from config.config import *
from utils.connection import Connection
import yaml
from config.args import Args

# Load the YAML configuration
def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__=="__main__":

    config = load_config('config/config.yaml')
    args = Args(config)

    history = Historical(args)

    history.visualize(mode=args.mode,
                      jsonlog_from=args.jsonlog_from)

    if args.run_plot:
        history.visualize(plot_distance=True)

    if args.save_rawvideo:
        history.visualize(gen_raw_video=True, raw_images_dir = None) #"runs/laneDeparture/laneDeparture4"

     
    if args.save_extractframe:
        history.visualize(extract_video_to_frames="assets/videos/Brooklyn Bridge to the Bronx via FDR Drive.mp4",crop=False)
    
 