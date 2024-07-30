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

#include "json_log.hpp"

using json = nlohmann::json;

JSON_LOG::JSON_LOG(std::string file, ADAS_Config_S* _config)
    : m_jsonFilePath(file),
      m_modelWidth(_config->modelWidth),
      m_modelHeight(_config->modelHeight),
      m_frameWidth(_config->frameWidth),
      m_frameHeight(_config->frameHeight)
{
#ifdef SPDLOG_USE_SYSLOG
    auto logger = spdlog::syslog_logger_mt("adas-output", "adas-output", LOG_CONS | LOG_NDELAY, LOG_SYSLOG);
#else
    auto logger = spdlog::stdout_color_mt("JSON");
    logger->set_pattern("[%n] [%^%l%$] %v");
#endif

    logger->set_level(_config->stDebugConfig.enableJson ? spdlog::level::debug : spdlog::level::info);
}

JSON_LOG::~JSON_LOG()
{
}

std::string JSON_LOG::logInfo(WNC_ADAS_Results adasResult, std::vector<BoundingBox> m_humanBBoxList,
                              std::vector<BoundingBox> m_vehicleBBoxList, std::vector<BoundingBox> m_roadSignBBoxList,
                              Object& m_tailingObject, int m_frameIdx)
{
    auto logger = spdlog::get(
#ifdef SPDLOG_USE_SYSLOG
        "adas-output"
#else
        "JSON"
#endif
        );

    json jsonData, jsonDataCurrentFrame, adasStr;

    if (m_bSaveToJSONFile)
    {
        std::ifstream inFile(m_jsonFilePath);

        if (inFile.is_open())
        {
            inFile >> jsonData;
            inFile.close();
        }
        else
            logger->error("Unable to open the file");
    }

    if (m_bSaveLDWLog)
        adasStr["LDW"] = (adasResult.eventType == ADAS_EVENT_LDW_LEFT || adasResult.eventType == ADAS_EVENT_LDW_RIGHT
                          || adasResult.eventType == ADAS_EVENT_LDW_FCW);

    if (m_bSaveFCWLog)
        adasStr["FCW"] = (adasResult.eventType == ADAS_EVENT_FCW || adasResult.eventType == ADAS_EVENT_LDW_FCW);

    jsonData["frame_ID"][std::to_string(m_frameIdx)]["ADAS"].push_back(adasStr);
    jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["ADAS"].push_back(adasStr);

    // Create an "Vanisjline" array for each frame
    if (m_bSaveVanishLine)
    {
        json vanishline = {{"vanishlineY", adasResult.yVanish}};
        jsonData["frame_ID"][std::to_string(m_frameIdx)]["vanishLineY"].push_back(vanishline);
        jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["vanishLineY"].push_back(vanishline);
    }

    if (m_bSaveLaneInfo)
    {
        for (auto& box : m_vehicleBBoxList)
        {
            BoundingBox rescaleBox;
            utils::rescaleBBox(box, rescaleBox, m_modelWidth, m_modelHeight, m_frameWidth, m_frameHeight);
            json det = {{"detectObj.x1", rescaleBox.x1}, {"detectObj.y1", rescaleBox.y1},
                        {"detectObj.x2", rescaleBox.x2}, {"detectObj.y2", rescaleBox.y2},
                        {"detectObj.label", "VEHICLE"},  {"detectObj.confidence", rescaleBox.confidence}};
            jsonData["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
            jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
        }
    }

    if (m_bSaveDetObjLog)
    {
        // VEHICLE
        for (auto& box : m_vehicleBBoxList)
        {
            BoundingBox rescaleBox;
            utils::rescaleBBox(box, rescaleBox, m_modelWidth, m_modelHeight, m_frameWidth, m_frameHeight);
            json det = {{"detectObj.x1", rescaleBox.x1}, {"detectObj.y1", rescaleBox.y1},
                        {"detectObj.x2", rescaleBox.x2}, {"detectObj.y2", rescaleBox.y2},
                        {"detectObj.label", "VEHICLE"},  {"detectObj.confidence", rescaleBox.confidence}};
            jsonData["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
            jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
        }

        for (auto& box : m_humanBBoxList)
        {
            BoundingBox rescaleBox;
            utils::rescaleBBox(box, rescaleBox, m_modelWidth, m_modelHeight, m_frameWidth, m_frameHeight);
            json det = {{"detectObj.x1", rescaleBox.x1}, {"detectObj.y1", rescaleBox.y1},
                        {"detectObj.x2", rescaleBox.x2}, {"detectObj.y2", rescaleBox.y2},
                        {"detectObj.label", "HUMAN"},    {"detectObj.confidence", rescaleBox.confidence}};
            jsonData["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["HUMAN"].push_back(det);
            jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["detectObj"]["HUMAN"].push_back(det);
        }
    }

    if (m_bSaveTrackObj)
    {
        json track = {{"tailingObj.x1", m_tailingObject.bbox.x1},
                      {"tailingObj.y1", m_tailingObject.bbox.y1},
                      {"tailingObj.x2", m_tailingObject.bbox.x2},
                      {"tailingObj.y2", m_tailingObject.bbox.y2},
                      {"tailingObj.label", m_tailingObject.classStr},
                      {"tailingObj.distanceToCamera", m_tailingObject.distanceToCamera},
                      {"tailingObj.id", m_tailingObject.id}};
        jsonData["frame_ID"][std::to_string(m_frameIdx)]["tailingObj"].push_back(track);
        jsonDataCurrentFrame["frame_ID"][std::to_string(m_frameIdx)]["tailingObj"].push_back(track);
    }
    std::string jsonCurrentFrameString;
    // Convert the JSON object to a string with indentation
    if (m_bShowJson)
    {
        jsonCurrentFrameString = jsonDataCurrentFrame.dump();
#ifndef SPDLOG_USE_SYSLOG
        logger->debug("====================================================================================");
#endif
        logger->debug("json:{}", jsonCurrentFrameString);
#ifndef SPDLOG_USE_SYSLOG
        logger->debug("====================================================================================");
#endif
        // if (m_sendJSONLog)
        // {
        //     send_json_log(jsonCurrentFrameString.c_str(), m_serverIP.c_str(), m_port);
        // }
    }
    std::string jsonString = jsonData.dump(4);
    if (m_bSaveToJSONFile)
        _saveJsonLogFile(jsonString);

    return jsonCurrentFrameString;
}

// Alsiter add 2024-07-29
void JSON_LOG::send_json_log(const char* json_log, const char* server_ip, int server_port)
{
    int                sock = 0;
    struct sockaddr_in serv_addr;
    char*              message = (char*)json_log;

    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        std::cerr << "\n Socket creation error \n";
        return;
    }

    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port   = htons(server_port);

    if (inet_pton(AF_INET, server_ip, &serv_addr.sin_addr) <= 0)
    {
        std::cerr << "\nInvalid address/ Address not supported \n";
        return;
    }

    if (connect(sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0)
    {
        std::cerr << "\nConnection Failed \n";
        close(sock); // Ensure the socket is closed in case of failure
        return;
    }

    send(sock, message, strlen(message), 0);
    close(sock);
}

// int main() {
//     const char *json_log =
//     "{\"frame_ID\":{\"71\":{\"ADAS\":[{\"FCW\":false,\"LDW\":false}],\"detectObj\":{\"VEHICLE\":[{\"detectObj.confidence\":0.86842942237854,\"detectObj.label\":\"VEHICLE\",\"detectObj.x1\":268,\"detectObj.x2\":311,\"detectObj.y1\":158,\"detectObj.y2\":201}]},\"tailingObj\":[{\"tailingObj.distanceToCamera\":23.71468162536621,\"tailingObj.id\":3,\"tailingObj.label\":\"VEHICLE\",\"tailingObj.x1\":228,\"tailingObj.x2\":256,\"tailingObj.y1\":165,\"tailingObj.y2\":193}],\"vanishLineY\":[{\"vanishlineY\":168}]}}}";
//     const char *server_ip = "127.0.0.1"; // Replace with the actual server IP address
//     int server_port = 12345; // Replace with the actual server port

//     send_json_log(json_log, server_ip, server_port);
//     return 0;
// }

std::string JSON_LOG::get_local_ip()
{
    struct ifaddrs* interfaces = nullptr;
    struct ifaddrs* temp_addr  = nullptr;
    int             success    = 0;

    success = getifaddrs(&interfaces);
    if (success == 0)
    {
        temp_addr = interfaces;
        while (temp_addr != nullptr)
        {
            if (temp_addr->ifa_addr->sa_family == AF_INET)
            {
                if (strcmp(temp_addr->ifa_name, "lo") != 0) // Ignore the loopback interface
                {
                    char  address_buffer[INET_ADDRSTRLEN];
                    void* address_ptr = &((struct sockaddr_in*)temp_addr->ifa_addr)->sin_addr;
                    inet_ntop(AF_INET, address_ptr, address_buffer, INET_ADDRSTRLEN);
                    freeifaddrs(interfaces);
                    return std::string(address_buffer);
                }
            }
            temp_addr = temp_addr->ifa_next;
        }
    }
    freeifaddrs(interfaces);
    return "";
}

void JSON_LOG::_saveJsonLogFile(std::string jsonString)
{
    auto logger = spdlog::get(
#ifdef SPDLOG_USE_SYSLOG
        "adas-output"
#else
        "JSON"
#endif
        );

    // Write the updated JSON to the file
    std::ofstream outFile(m_jsonFilePath);
    if (outFile)
    {
        outFile << jsonString; // Adjust the indentation as needed
        logger->debug("Additional frame IDs appended to the JSON file");
    }
    else
        logger->error("Unable to open the file for writing");
}