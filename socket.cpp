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

#include "socket.hpp"

// SOCKET::SOCKET(ADAS_Config_S *m_config)
// {
//     m_serverIP   = m_config->HistoricalFeedModeConfig.serverIP;
//     m_serverPort = m_config->HistoricalFeedModeConfig.serverPort;
// }

SOCKET::SOCKET()
{
}

SOCKET::~SOCKET()
{
}

int SOCKET::create_socket()
{
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
    {
        std::cerr << "\nSocket creation error\n";
    }
    return sock;
}

bool SOCKET::connect_to_server(int sock, const char *server_ip, int server_port)
{
    struct sockaddr_in serv_addr;
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port   = htons(server_port);

    if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
    {
        std::cerr << "\nInvalid address/Address not supported\n";
        return false;
    }

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        std::cerr << "\nConnection Failed\n";
        return false;
    }

    return true;
}

bool SOCKET::send_frame_index(int sock, int frame_index)
{
    uint32_t frame_index_net = htonl(frame_index);
    if (send(sock, reinterpret_cast<const char *>(&frame_index_net), sizeof(frame_index_net), 0) < 0)
    {
        std::cerr << "Error sending frame index.\n";
        return false;
    }
    return true;
}

bool SOCKET::send_image_size(int sock, uint32_t image_size)
{
    image_size = htonl(image_size);
    if (send(sock, reinterpret_cast<const char *>(&image_size), sizeof(image_size), 0) < 0)
    {
        std::cerr << "Error sending image size.\n";
        return false;
    }
    return true;
}

bool SOCKET::send_image_data(int sock, const std::vector<uchar> &buffer)
{
    if (send(sock, buffer.data(), buffer.size(), 0) < 0)
    {
        std::cerr << "Error sending image data.\n";
        return false;
    }
    return true;
}

bool SOCKET::send_image_path(int sock, const std::string &image_path)
{
    uint32_t path_length = static_cast<uint32_t>(image_path.size());
    path_length          = htonl(path_length);
    if (send(sock, reinterpret_cast<const char *>(&path_length), sizeof(path_length), 0) < 0)
    {
        std::cerr << "Failed to send path length" << std::endl;
        return false;
    }
    if (send(sock, image_path.c_str(), image_path.size(), 0) < 0)
    {
        std::cerr << "Failed to send image path" << std::endl;
        return false;
    }
    return true;
}

bool SOCKET::send_json_log_message(int sock, const char *json_log)
{
    if (send(sock, json_log, strlen(json_log), 0) < 0)
    {
        std::cerr << "Error sending JSON log.\n";
        return false;
    }
    return true;
}

void SOCKET::close_socket(int sock)
{
    close(sock);
    std::cout << "Connection closed.\n";
}

void SOCKET::send_image_and_log_live_mode(const cv::Mat &displayImg, const char *json_log, const char *server_ip,
                                          int server_port, int frame_index)
{
    int sock = create_socket();
    if (sock < 0)
        return;

    if (!connect_to_server(sock, server_ip, server_port))
    {
        close_socket(sock);
        return;
    }

    if (displayImg.empty() || displayImg.cols == 0 || displayImg.rows == 0)
    {
        std::cerr << "Error: The cv::Mat image is invalid.\n";
        close_socket(sock);
        return;
    }

    std::vector<uchar> buffer;
    if (!cv::imencode(".jpg", displayImg, buffer))
    {
        std::cerr << "Error encoding the image.\n";
        close_socket(sock);
        return;
    }

    std::cout << "Sending image of size: " << buffer.size() << " bytes\n";

    if (!send_frame_index(sock, frame_index) || !send_image_size(sock, buffer.size()) || !send_image_data(sock, buffer)
        || !send_json_log_message(sock, json_log))
    {
        close_socket(sock);
        return;
    }

    std::cout << "Image data and JSON log sent successfully.\n";

    close_socket(sock);
}

void SOCKET::send_image(const std::string &image_path, const char *server_ip, int server_port)
{
    int sock = create_socket();
    if (sock < 0)
        return;

    if (!connect_to_server(sock, server_ip, server_port))
    {
        close_socket(sock);
        return;
    }

    // Read the image file
    std::ifstream file(image_path, std::ios::binary);
    if (!file)
    {
        std::cerr << "Could not open the file: " << image_path << std::endl;
        close_socket(sock);
        return;
    }

    // // Read the file content into a buffer
    // file.seekg(0, std::ios::end);
    // std::streamsize size = file.tellg();
    // file.seekg(0, std::ios::beg);
    // std::vector<char> buffer(size);
    // // std::vector<unsigned char> buffer(size);
    // if (!file.read(buffer.data(), size))
    // {
    //     std::cerr << "Error reading the file: " << image_path << std::endl;
    //     close_socket(sock);
    //     return;
    // }

    // Read the file content into a buffer (using unsigned char)
    file.seekg(0, std::ios::end);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<unsigned char> buffer(size);
    if (!file.read(reinterpret_cast<char *>(buffer.data()), size))
    {
        std::cerr << "Error reading the file: " << image_path << std::endl;
        close_socket(sock);
        return;
    }

    // Send the image size and data
    if (!send_image_size(sock, buffer.size()) || !send_image_data(sock, buffer))
    {
        close_socket(sock);
        return;
    }

    std::cout << "Image data sent successfully.\n";

    close_socket(sock);
}

void SOCKET::send_json_log(const char *json_log, const char *server_ip, int server_port)
{
    int sock = create_socket();
    if (sock < 0)
        return;

    if (!connect_to_server(sock, server_ip, server_port))
    {
        close_socket(sock);
        return;
    }

    if (!send_json_log_message(sock, json_log))
    {
        close_socket(sock);
        return;
    }

    std::cout << "JSON log sent successfully.\n";

    close_socket(sock);
}

void SOCKET::send_image_and_log_and_frameIdx_and_imgPath(const std::string &image_path, const char *json_log,
                                                         const char *server_ip, int server_port, int frame_index)
{
    int sock = create_socket();
    if (sock < 0)
        return;

    if (!connect_to_server(sock, server_ip, server_port))
    {
        close_socket(sock);
        return;
    }

    // Read the image file
    std::ifstream file(image_path, std::ios::binary);
    if (!file)
    {
        std::cerr << "Could not open the file: " << image_path << std::endl;
        close_socket(sock);
        return;
    }

    // // Read the file content into a buffer
    // file.seekg(0, std::ios::end);
    // std::streamsize size = file.tellg();
    // file.seekg(0, std::ios::beg);
    // std::vector<char> buffer(size);
    // if (!file.read(buffer.data(), size))
    // {
    //     std::cerr << "Error reading the file: " << image_path << std::endl;
    //     close_socket(sock);
    //     return;
    // }

    // Read the file content into a buffer (using unsigned char)
    file.seekg(0, std::ios::end);
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<unsigned char> buffer(size);
    if (!file.read(reinterpret_cast<char *>(buffer.data()), size))
    {
        std::cerr << "Error reading the file: " << image_path << std::endl;
        close_socket(sock);
        return;
    }

    std::cout << "Sending image of size: " << size << " bytes" << std::endl;

    // Send frame index
    if (!send_frame_index(sock, frame_index))
    {
        close_socket(sock);
        return;
    }

    // Send image size and data
    if (!send_image_size(sock, buffer.size()) || !send_image_data(sock, buffer))
    {
        close_socket(sock);
        return;
    }

    std::cout << "Image data sent." << std::endl;

    // Send image path
    if (!send_image_path(sock, image_path))
    {
        close_socket(sock);
        return;
    }

    std::cout << "Image path sent." << std::endl;

    // Send JSON log
    if (!send_json_log_message(sock, json_log))
    {
        close_socket(sock);
        return;
    }

    std::cout << "JSON log sent." << std::endl;

    // Close the socket
    close_socket(sock);
    std::cout << "Connection closed." << std::endl;
}

// void SOCKET::send_image_and_log_live_mode(const cv::Mat &displayImg, const char *json_log, const char *server_ip,
//                                   int server_port, int frame_index)
// {
//     int                sock = 0;
//     struct sockaddr_in serv_addr;
//     const char *       json_log_message = json_log;

//     // Create socket
//     if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
//     {
//         std::cerr << "\nSocket creation error\n";
//         return;
//     }

//     serv_addr.sin_family = AF_INET;
//     serv_addr.sin_port   = htons(server_port);

//     // Convert IPv4 and IPv6 addresses from text to binary form
//     if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
//     {
//         std::cerr << "\nInvalid address/Address not supported\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Attempt to connect to the server
//     if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
//     {
//         std::cerr << "\nConnection Failed\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Check the image
//     if (displayImg.empty())
//     {
//         std::cerr << "Error: The cv::Mat image is empty.\n";
//         close(sock);
//         return;
//     }

//     if (displayImg.cols == 0 || displayImg.rows == 0)
//     {
//         std::cerr << "Error: The cv::Mat image has zero width or height.\n";
//         close(sock);
//         return;
//     }

//     // Encode the cv::Mat image to a byte buffer
//     std::vector<uchar> buffer;
//     // std::vector<int>   params = {cv::IMWRITE_PNG_COMPRESSION, 3}; // PNG with compression level 3
//     if (!cv::imencode(".jpg", displayImg, buffer)) // params
//     {
//         std::cerr << "Error encoding the image.\n";
//         close(sock);
//         return;
//     }

//     std::cout << "Sending image of size: " << buffer.size() << " bytes\n";

//     // Send the frame_index
//     uint32_t frame_index_net = htonl(frame_index); // Convert to network byte order
//     send(sock, reinterpret_cast<const char *>(&frame_index_net), sizeof(frame_index_net), 0);

//     // Send the size of the image
//     uint32_t image_size = static_cast<uint32_t>(buffer.size());
//     image_size          = htonl(image_size); // Convert to network byte order
//     send(sock, reinterpret_cast<const char *>(&image_size), sizeof(image_size), 0);

//     // Send the image data
//     send(sock, buffer.data(), buffer.size(), 0);

//     std::cout << "Image data sent.\n";

//     // Send the JSON log
//     send(sock, json_log_message, strlen(json_log_message), 0);

//     std::cout << "JSON log sent.\n";

//     // Close the socket
//     close(sock);
//     std::cout << "Connection closed.\n";
// }

// void SOCKET::send_image(const std::string &image_path, const char *server_ip, int server_port)
// {
//     int                sock = 0;
//     struct sockaddr_in serv_addr;

//     // Create socket
//     if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
//     {
//         std::cerr << "\nSocket creation error\n";
//         return;
//     }

//     serv_addr.sin_family = AF_INET;
//     serv_addr.sin_port   = htons(server_port);

//     // Convert IPv4 and IPv6 addresses from text to binary form
//     if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
//     {
//         std::cerr << "\nInvalid address/Address not supported\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Attempt to connect to the server
//     if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
//     {
//         std::cerr << "\nConnection Failed\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Read the image file
//     std::ifstream file(image_path, std::ios::binary);
//     if (!file)
//     {
//         std::cerr << "Could not open the file: " << image_path << std::endl;
//         close(sock);
//         return;
//     }

//     // Read the file content into a buffer
//     file.seekg(0, std::ios::end);
//     std::streamsize size = file.tellg();
//     file.seekg(0, std::ios::beg);
//     std::vector<char> buffer(size);
//     if (!file.read(buffer.data(), size))
//     {
//         std::cerr << "Error reading the file: " << image_path << std::endl;
//         close(sock);
//         return;
//     }

//     // Send the size of the image
//     int image_size = buffer.size();
//     send(sock, reinterpret_cast<const char *>(&image_size), sizeof(image_size), 0);

//     // Send the image data
//     send(sock, buffer.data(), buffer.size(), 0);

//     // Close the socket
//     close(sock);
// }

// void SOCKET::send_image_and_log_live_mode(const cv::Mat &displayImg, const char *json_log, const char *server_ip,
//                                   int server_port, int frame_index)
// {
//     int                sock = 0;
//     struct sockaddr_in serv_addr;
//     const char *       json_log_message = json_log;

//     // Create socket
//     if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
//     {
//         std::cerr << "\nSocket creation error\n";
//         return;
//     }

//     serv_addr.sin_family = AF_INET;
//     serv_addr.sin_port   = htons(server_port);

//     // Convert IPv4 and IPv6 addresses from text to binary form
//     if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
//     {
//         std::cerr << "\nInvalid address/Address not supported\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Attempt to connect to the server
//     if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
//     {
//         std::cerr << "\nConnection Failed\n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     // Check the image
//     if (displayImg.empty())
//     {
//         std::cerr << "Error: The cv::Mat image is empty.\n";
//         close(sock);
//         return;
//     }

//     if (displayImg.cols == 0 || displayImg.rows == 0)
//     {
//         std::cerr << "Error: The cv::Mat image has zero width or height.\n";
//         close(sock);
//         return;
//     }

//     // Encode the cv::Mat image to a byte buffer
//     std::vector<uchar> buffer;
//     // std::vector<int>   params = {cv::IMWRITE_PNG_COMPRESSION, 3}; // PNG with compression level 3
//     if (!cv::imencode(".jpg", displayImg, buffer)) // params
//     {
//         std::cerr << "Error encoding the image.\n";
//         close(sock);
//         return;
//     }

//     std::cout << "Sending image of size: " << buffer.size() << " bytes\n";

//     // Send the frame_index
//     uint32_t frame_index_net = htonl(frame_index); // Convert to network byte order
//     send(sock, reinterpret_cast<const char *>(&frame_index_net), sizeof(frame_index_net), 0);

//     // Send the size of the image
//     uint32_t image_size = static_cast<uint32_t>(buffer.size());
//     image_size          = htonl(image_size); // Convert to network byte order
//     send(sock, reinterpret_cast<const char *>(&image_size), sizeof(image_size), 0);

//     // Send the image data
//     send(sock, buffer.data(), buffer.size(), 0);

//     std::cout << "Image data sent.\n";

//     // Send the JSON log
//     send(sock, json_log_message, strlen(json_log_message), 0);

//     std::cout << "JSON log sent.\n";

//     // Close the socket
//     close(sock);
//     std::cout << "Connection closed.\n";
// }

// Alsiter add 2024-07-29
// void SOCKET::send_json_log(const char* json_log, const char* server_ip, int server_port)
// {
//     int                sock = 0;
//     struct sockaddr_in serv_addr;
//     char*              message = (char*)json_log;

//     if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
//     {
//         std::cerr << "\n Socket creation error \n";
//         return;
//     }

//     serv_addr.sin_family = AF_INET;
//     serv_addr.sin_port   = htons(server_port);

//     if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
//     {
//         std::cerr << "\nInvalid address/ Address not supported \n";
//         return;
//     }

//     if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0)
//     {
//         std::cerr << "\nConnection Failed \n";
//         close(sock); // Ensure the socket is closed in case of failure
//         return;
//     }

//     send(sock, message, strlen(message), 0);
//     close(sock);
// }