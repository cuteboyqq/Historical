from task.task_assigner import TaskAssigner
from utils.connection import Connection
import yaml
from config.args import Args

# Load the YAML configuration file and return its content as a dictionary
def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__=="__main__":

    # Load configuration settings from the specified YAML file
    config = load_config('config/config.yaml')
    
    # Initialize Args object with the loaded configuration
    args = Args(config)

    # Create TaskAssigner object using the Args object
    task = TaskAssigner(args)

    task.task_assigner(mode=args.mode, jsonlog_from=args.jsonlog_from)

    # Optionally generate and display plots of distance data if specified in config
    if args.run_plot:
        task.task_assigner(plot_distance=True)

    # Optionally generate and save raw video if specified in config
    if args.save_rawvideo:
        task.task_assigner(gen_raw_video=True, raw_images_dir="assets/images/InternalUse_Ver3-1920x1080")  # Directory for saving raw videos (None for default)

    # Optionally extract frames from a video and optionally crop them if specified in config
    if args.save_extractframe:
        task.task_assigner(extract_video_to_frames="assets/videos/Brooklyn Bridge to the Bronx via FDR Drive.mp4", crop=False)

    
 