import socket
import json
import cv2

import json
import cv2

def process_json_log(json_log):
    try:
        log_data = json.loads(json_log)
        print("Received JSON:", json.dumps(log_data, indent=4))  # Print formatted JSON

        frame_ID = list(log_data["frame_ID"].keys())[0]  # Extract the first frame_ID key
        detect_objs = log_data["frame_ID"][frame_ID]["detectObj"]["VEHICLE"]
        tailing_objs = log_data["frame_ID"][frame_ID]["tailingObj"]

        image_path = f"assets/images/2024-7-31-15-57/RawFrame_{frame_ID}.png"
        print(image_path)
        image = cv2.imread(image_path)

        for obj in detect_objs:
            x1, y1 = obj["detectObj.x1"], obj["detectObj.y1"]
            x2, y2 = obj["detectObj.x2"], obj["detectObj.y2"]
            confidence = obj["detectObj.confidence"]
            label = obj["detectObj.label"]
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, f"{label} ({confidence:.2f})", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        for obj in tailing_objs:
            x1, y1 = obj["tailingObj.x1"], obj["tailingObj.y1"]
            x2, y2 = obj["tailingObj.x2"], obj["tailingObj.y2"]
            distance = obj["tailingObj.distanceToCamera"]
            label = obj["tailingObj.label"]
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(image, f"{label} ({distance:.2f}m)", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        cv2.imshow("Annotated Image", image)
        cv2.waitKey(1)  # Display the image for a short time

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

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        json_log = client_socket.recv(4096).decode('utf-8')
        process_json_log(json_log)
        client_socket.close()



if __name__ == "__main__":
    start_server()
