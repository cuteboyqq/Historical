import socket
import json
import cv2

import json
import cv2
global index
index  = 0
def process_json_log(json_log):
    try:
        log_data = json.loads(json_log)
        print("Received JSON:", json.dumps(log_data, indent=4))  # Print formatted JSON

        frame_ID = list(log_data["frame_ID"].keys())[0]  # Extract the first frame_ID key
        
        detect_objs = log_data["frame_ID"][frame_ID]["detectObj"]["VEHICLE"]
        tailing_objs = log_data["frame_ID"][frame_ID]["tailingObj"]
        vanishline_objs = log_data["frame_ID"][frame_ID]["vanishLineY"]

        image_path = f"assets/images/2024-7-31-15-57/RawFrame_{frame_ID}.png"
        print(image_path)
        image = cv2.imread(image_path)
        cv2.putText(image, 'frame_ID:'+str(frame_ID), (10,10), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
        for obj in vanishline_objs:
            vanishlineY = obj["vanishlineY"]
            x2 = image.shape[1]
            cv2.line(image, (0, vanishlineY), (x2, vanishlineY), (0, 255, 255), thickness=1)
            cv2.putText(image, 'VanishLineY:' + str(round(vanishlineY,3)), (10,30), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)

        for obj in tailing_objs:
            tailingObj_x1, tailingObj_y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
            tailingObj_x2, tailingObj_y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
            distance = obj["tailingObj.distanceToCamera"]
            label = obj["tailingObj.label"]
            distance_to_camera = obj['tailingObj.distanceToCamera']
            tailingObj_id = obj['tailingObj.id']
            tailingObj_label = obj['tailingObj.label']
            # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            im = image
            showtailobjBB_corner = True
            if showtailobjBB_corner:
                top_left = (tailingObj_x1, tailingObj_y1)
                bottom_right = (tailingObj_x2, tailingObj_y2)
                top_right = (tailingObj_x2,tailingObj_y1)
                bottom_left = (tailingObj_x1,tailingObj_y2) 
                BB_width = abs(tailingObj_x2 - tailingObj_x1)
                BB_height = abs(tailingObj_y2 - tailingObj_y1)
                divide_length = 5
                thickness = 3
                color = (0,255,255)
                # Draw each side of the rectangle
                cv2.line(im, top_left, (top_left[0]+int(BB_width/divide_length), top_left[1]), color, thickness)
                cv2.line(im, top_left, (top_left[0], top_left[1] + int(BB_height/divide_length)), color, thickness)

                cv2.line(im, bottom_right,(bottom_right[0] - int(BB_width/divide_length),bottom_right[1]), color, thickness)
                cv2.line(im, bottom_right,(bottom_right[0],bottom_right[1] - int(BB_height/divide_length) ), color, thickness)


                cv2.line(im, top_right, ((top_right[0]-int(BB_width/divide_length)), top_right[1]), color, thickness)
                cv2.line(im, top_right, (top_right[0], (top_right[1]+int(BB_height/divide_length))), color, thickness)

                cv2.line(im, bottom_left, ((bottom_left[0]+int(BB_width/divide_length)), bottom_left[1]), color, thickness)
                cv2.line(im, bottom_left, (bottom_left[0], (bottom_left[1]-int(BB_height/divide_length))), color, thickness)
            else:
                cv2.rectangle(im, (tailingObj_x1, tailingObj_y1), (tailingObj_x2, tailingObj_y2), color=(0,255,255), thickness=2)
                cv2.putText(image, f"{label} ({distance:.2f}m)", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            cv2.putText(im, f'{tailingObj_label} ID:{tailingObj_id}', (tailingObj_x1, tailingObj_y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(im, 'Distance:' + str(round(distance_to_camera,3)) + 'm', (tailingObj_x1, tailingObj_y1-25), cv2.FONT_HERSHEY_SIMPLEX,0.45, (0, 255, 255), 1, cv2.LINE_AA)
        
        for obj in detect_objs:
            x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
            x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
            confidence = obj["detectObj.confidence"]
            label = obj["detectObj.label"]
            if tailingObj_x1!=x1 and tailingObj_y1!=y1:
                cv2.rectangle(image, (x1, y1), (x2, y2), (255, 200, 0), 1)
                cv2.putText(image, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 0), 1)
        image = cv2.resize(image, (1280, 720), interpolation=cv2.INTER_AREA)
        cv2.imshow("Annotated Image", image)
        cv2.waitKey(1)  # Display the image for a short time
        cv2.imwrite(f'AI_result_images/frame_{frame_ID}.jpg',image)
    except KeyError as e:
        print(f"KeyError: {e} - The key might be missing in the JSON data.")
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e} - The JSON data might be malformed.")
    except Exception as e:
        print(f"Error: {e} - An unexpected error occurred.")


# Example usage
json_log = '''{
    "frame_ID": {
        "89": {
            "ADAS": [{"FCW": false, "LDW": false}],
            "detectObj": {
                "VEHICLE": [
                    {"detectObj.confidence": 0.8481980562210083, "detectObj.label": "VEHICLE", "detectObj.x1": 269, "detectObj.x2": 312, "detectObj.y1": 160, "detectObj.y2": 203},
                    {"detectObj.confidence": 0.8470443487167358, "detectObj.label": "VEHICLE", "detectObj.x1": 78, "detectObj.x2": 143, "detectObj.y1": 154, "detectObj.y2": 207}
                ]
            },
            "tailingObj": [
                {"tailingObj.distanceToCamera": 27.145750045776367, "tailingObj.id": 3, "tailingObj.label": "VEHICLE", "tailingObj.x1": 230, "tailingObj.x2": 257, "tailingObj.y1": 166, "tailingObj.y2": 193}
            ],
            "vanishLineY": [{"vanishlineY": 171}]
        }
    }
}'''

# process_json_log(json_log)

def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def receive_image_and_log(client_socket):
    global index

    try:
        # Receive the size of the image
        size_data = client_socket.recv(4)
        if not size_data:
            print("Failed to receive image size.")
            return

        size = int.from_bytes(size_data, byteorder='big')
        print(f"Expected image size: {size} bytes")

        # Receive the image data
        buffer = b''
        while len(buffer) < size:
            data = client_socket.recv(min(size - len(buffer), 4096))
            if not data:
                break
            buffer += data

        if len(buffer) != size:
            print(f"Failed to receive the complete image data. Received {len(buffer)} bytes out of {size}")
            return

        print(f"Successfully received the complete image data. Total bytes: {len(buffer)}")

        # Save the image to a file
        image_path = f'assets/images/received/received_image_{index}.png'
        with open(image_path, 'wb') as file:
            file.write(buffer)

        # Read the remaining data for JSON log
        json_data = b''
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            json_data += data
            if b'\r\n\r\n' in data:
                break

        json_data = json_data.decode('utf-8')

        # Process the JSON log
        process_json_log(json_data)

        index += 1

    except Exception as e:
        print(f"Error: {e} - An unexpected error occurred.")



import os
def start_server():
    host = '192.168.1.10'  # Bind to localhost
    port = 5000  # Non-privileged port number

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
    except PermissionError as e:
        print(f"PermissionError: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    server_socket.listen(5)
    print(f"Server started on {host}:{port}")
    os.makedirs('AI_result_images',exist_ok=True)
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        json_log = client_socket.recv(4096).decode('utf-8')
        process_json_log(json_log)
        # receive_image_and_log(client_socket)
        client_socket.close()


def start_server_ver2():
    host = '192.168.1.10'  # Bind to localhost
    port = 5000  # Non-privileged port number

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port))
    except PermissionError as e:
        print(f"PermissionError: {e}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    server_socket.listen(5)
    print(f"Server started on {host}:{port}")
    os.makedirs('assets/images/received', exist_ok=True)

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        receive_image_and_log(client_socket)
        client_socket.close()



if __name__ == "__main__":
    start_server_ver2()