import json
import matplotlib.pyplot as plt
import csv

def extract_adas_data_json(json_file):
    extracted_data = []
    extracted_vanish = []
    extracted_y2 = []
    smooth_distance = []

    with open(json_file, 'r') as file:
        data = file.readlines()
        for line in data:
            if "tailingObj.distanceToCamera" in line:
                extracted_data.append(float(line.strip("\n").split(":")[-1].strip(",").strip(" ")))

            elif "tailingObj.smoothDistance" in line:
                smooth_distance.append(float(line.strip("\n").split(":")[-1].strip(",").strip(" ")))

            elif "tailingObj.y2" in line:
                extracted_y2.append(float(line.strip("\n").split(":")[-1].strip(" ")))
            
            elif "vanishLineY" in line:
                extracted_vanish.append(float(line.strip("\n").split(":")[-1].strip(" ")))

    return extracted_data, extracted_vanish, extracted_y2, smooth_distance




# def extract_adas_data_json(json_file):
#     extracted_data = []
#     with open(json_file, 'r') as file:
#         json_data = json.load(file)
#         json_data = json_data['frame_ID']
#         indices = [int(i) for i in json_data.keys()]
#         indices = sorted(indices)
 
#         for ind in indices:
#             frame_data = json_data[str(ind)]
#             if 'tailingObj' in frame_data:
#                 frame_data = frame_data['tailingObj']
#                 objs = [obj for obj in frame_data if ('tailingObj.label' in obj and obj['tailingObj.label'] == 'VEHICLE')]
#                 if(len(objs)>0):
#                     for obj in objs[:1]:
#                         if 'tailingObj.distanceToCamera' in obj:
#                             extracted_data.append(float(obj['tailingObj.distanceToCamera']))
#                 else:
#                     extracted_data.append(float(frame_data[0]['tailingObj.distanceToCamera']))
#             else:
#                 print(frame_data.keys())
#     return extracted_data


def extract_distance_data_csv(file_path):
    frame_ids = []
    distances = []

    with open(file_path, 'r') as file:
        reader = csv.reader(file, delimiter=',')
        for row in reader:
            # Debug print for each row
            print(f"Row: {row}")

            # Join the row into a single string
            row_str = ','.join(row)
            
            # Find the position of 'json:'
            json_start = row_str.find('json:')
            if json_start != -1:
                json_data = row_str[json_start + 5:].strip()
                if json_data.startswith('"') and json_data.endswith('"'):
                    json_data = json_data[1:-1]  # Remove enclosing double quotes
                
                # Replace any double quotes escaped with backslashes
                json_data = json_data.replace('\\"', '"')
                
                try:
                    data = json.loads(json_data)
                    print(f"Parsed JSON: {data}")

                    for frame_id, frame_data in data['frame_ID'].items():
                        frame_ids.append(int(frame_id))
                        tailing_objs = frame_data.get('tailingObj', [])
                        if tailing_objs:
                            distance_to_camera = tailing_objs[0].get('tailingObj.distanceToCamera', None)
                            if distance_to_camera is not None:
                                distances.append(distance_to_camera)
                            else:
                                distances.append(float('nan'))  # Handle missing values
                        else:
                            distances.append(float('nan'))  # Handle missing values
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                except Exception as e:
                    print(f"Unexpected error: {e}")

    return frame_ids, distances

import numpy as np
def calculate_match_rate(frame_ids_1, distances_1, frame_ids_2, distances_2, tolerance=1.0):
    common_frame_ids = set(frame_ids_1).intersection(set(frame_ids_2))
    matches = 0
    total_common = 0

    for frame_id in common_frame_ids:
        idx1 = frame_ids_1.index(frame_id)
        idx2 = frame_ids_2.index(frame_id)

        if not np.isnan(distances_1[idx1]) and not np.isnan(distances_2[idx2]):
            if abs(distances_1[idx1] - distances_2[idx2]) <= tolerance:
                matches += 1
        total_common += 1

    match_rate = (matches / total_common) * 100 if total_common > 0 else 0
    return match_rate, total_common


# Paths to your CSV files
json_file_1 = 'G9D2400AURSD-1726106769000-1726106829000-1-VIDEO.json'

csv_file_1 = '2024-8-16-21-28-run1.csv'
csv_file_2 = '2024-8-16-21-28-run2.csv'


# Extract data from the CSV files
frame_ids_1, distances_1 = extract_distance_data_csv(csv_file_1)
frame_ids_2, distances_2 = extract_distance_data_csv(csv_file_2)

# Calculate the match rate
tolerance = 0.0  # Adjust this value if necessary
match_rate, total_common = calculate_match_rate(frame_ids_1, distances_1, frame_ids_2, distances_2, tolerance)

print(f"Match rate between Run1 and Run2: {match_rate:.2f}%")
print(f"Total common frames: {total_common}")



plt.figure(figsize=(200, 100))

plt.plot(distances_1, label='Run1')
plt.plot(distances_2, label='Run2')

plt.xlabel('FrameID')
plt.ylabel('tailingObj.distanceToCamera')
plt.title('Distance to Camera over Frames')
plt.legend()
plt.grid(True)

plt.show()