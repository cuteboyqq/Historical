1. Set parameters in Historical/config/config.py
	For example (In config.py) :
		# Paths to your CSV files
		CSV_FILE = 'assets/csv_file/test-live-2024-07-22-11-43.csv' #live mode
		# the RawFrame images directory
		IMG_DIR = "assets/images/2024-7-23-11-38"
		# Basname of the images
		IMAGE_BASE_NAME = "RawFrame_"
		# image foramt
		IMAGE_FORMAT = "png"
		# Directory of saving the AI result images
		SAVE_IM_DIR = "/home/ali/Projects/GitHub_Code/ali/Historical/AI_result_image"
		
	
2. Open ternimal on your computer
	Ubuntu : Ctrl + Alt + T
	Windows 10/11 : Windows + R, type cmd and enter
	
3. In ternimal, go to Historical directory : [cmd] cd [cutomer directory]/Historical 

(HINT: 3-1. and 3-3. just for the first time, 3-2. need to do every time)

       3-1. Create environment (Note: If you already have environment (env folder), skip this to 3-2.)
       
       	[cmd] python -m venv env
       	or [cmd] python3.8 -m venv env
       	or [cmd] python3.9 -m venv env
       	This command will create a 'env' folder for you to install library
           Based on your python version
           
           
       3-2. Activate the environment
       
		Ubuntu 18.04/20.04/22.04
			- [cmd] source env/bin/activate
		Windows 10/11
			-[cmd] env\Scripts\activate
			
			
	3-3. Install some library software (Note: If you already installed the software library, skip this to 4.)
		for example : 
			[cmd] pip install opencv-python
			[cmd] pip install matplotlib
		
		
4. Start run Historical/main.py, go to the directory : [cmd] cd [customer directory]/Historical
	4-1. [cmd] python main.py
	And it will start parsing CSV file and draw AI result on the RawFrame images, or saving AI result images if customer enable saving AI result images




