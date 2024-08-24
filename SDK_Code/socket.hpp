/*
  (C) 2023-2024 Wistron NeWeb Corporation (WNC) - All Rights Reserved

  This software and its associated documentation are the confidential and
  proprietary information of Wistron NeWeb Corporation (WNC) ("Company") and
  may not be copied, modified, distributed, or otherwise disclosed to third
  parties without the express written consent of the Company.

  Unauthorized reproduction, distribution, or disclosure of this software and
  its associated documentation or the information contained herein is a
  violation of applicable laws and may result in severe legal penalties.
*/

#ifndef __SOCKET__
#define __SOCKET__

#include <fstream>
#include <vector>
#include "bounding_box.hpp"
#include "dataStructures.h"
// #include "adas_config_reader.hpp"
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <iostream>
#include <cstring>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <vector>
// OpenCV
#ifdef SAV837
#include <opencv2/core.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>
#endif
using namespace std;

class SOCKET
{
public:
    // SOCKET(ADAS_Config_S* m_config);
    SOCKET();
    ~SOCKET();
    void send_image_and_log_live_mode(const cv::Mat &displayImg, const char *json_log, const char *server_ip,
                                  int server_port, int frame_index);
    void send_image(const std::string &image_path, const char *server_ip, int server_port);
    void send_json_log(const char *json_log, const char *server_ip, int server_port);
    void send_image_and_log_and_frameIdx_and_imgPath(const std::string &image_path, const char *json_log,
                                                    const char *server_ip, int server_port, int frame_index);

    std::string m_serverIP;   
    int         m_serverPort;

private:
    int create_socket();
    bool connect_to_server(int sock, const char *server_ip, int server_port);
    bool send_frame_index(int sock, int frame_index);
    bool send_image_size(int sock, uint32_t image_size);
    bool send_image_data(int sock, const std::vector<uchar> &buffer);
    bool send_image_path(int sock, const std::string &image_path);
    bool send_json_log_message(int sock, const char *json_log);
    void close_socket(int sock);

    
};

#endif