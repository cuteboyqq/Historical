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

JSON_LOG::JSON_LOG(std::string file, ADAS_Config_S* _config) : m_jsonFilePath(file)
{
#ifdef SPDLOG_USE_SYSLOG
    auto logger = spdlog::syslog_logger_mt("adas-output", "adas-output", LOG_CONS | LOG_NDELAY, LOG_SYSLOG);
#else
    auto logger = spdlog::stdout_color_mt("JSON");
    logger->set_pattern("[%n] [%^%l%$] %v");
#endif

    logger->set_level(_config->stDebugConfig.enableJson ? spdlog::level::debug : spdlog::level::info);
    m_bDebugProfiling = _config->stDebugProfiling;
}

JSON_LOG::~JSON_LOG()
{
}

std::string JSON_LOG::logInfo(WNC_ADAS_Results& adasResult, std::vector<BoundingBox>& humanBBoxList,
                              std::vector<BoundingBox>& vehicleBBoxList, std::vector<BoundingBox>& roadSignBBoxList,
                              Object& tailingObject, int frameIdx, float inferenceTime, int bufferSize)
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

    jsonData["frame_ID"][std::to_string(frameIdx)]["ADAS"].push_back(adasStr);
    jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["ADAS"].push_back(adasStr);

    // Create an "Vanisjline" array for each frame
    if (m_bSaveVanishLine)
    {
        json vanishline = {{"vanishLineY", adasResult.yVanish}};
        jsonData["frame_ID"][std::to_string(frameIdx)]["vanishLine"].push_back(vanishline);
        jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["vanishLine"].push_back(vanishline);
    }

    if (m_bSaveLaneInfo)
    {
        json laneArray;
        // Add lane info
        json obj;
        obj["pLeftFar.x"]      = adasResult.pLeftFar.x;
        obj["pLeftFar.y"]      = adasResult.pLeftFar.y;
        obj["pLeftCarhood.x"]  = adasResult.pLeftCarhood.x;
        obj["pLeftCarhood.y"]  = adasResult.pLeftCarhood.y;
        obj["pRightFar.x"]     = adasResult.pRightFar.x;
        obj["pRightFar.y"]     = adasResult.pRightFar.y;
        obj["pRightCarhood.x"] = adasResult.pRightCarhood.x;
        obj["pRightCarhood.y"] = adasResult.pRightCarhood.y;
        obj["isDetectLine"]    = adasResult.isDetectLine;
        // Add the object to the "Obj" array
        laneArray.push_back(obj);

        // Add the "Obj" array to the frame
        jsonData["frame_ID"][std::to_string(frameIdx)]["LaneInfo"]             = laneArray;
        jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["LaneInfo"] = laneArray;
    }

    if (m_bSaveDetObjLog)
    {
        // VEHICLE
        for (auto& box : vehicleBBoxList)
        {
            BoundingBox rescaleBox;
            utils::rescaleBBox(box, rescaleBox, MODEL_WIDTH, MODEL_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT);
            json det = {{"detectObj.x1", rescaleBox.x1}, {"detectObj.y1", rescaleBox.y1},
                        {"detectObj.x2", rescaleBox.x2}, {"detectObj.y2", rescaleBox.y2},
                        {"detectObj.label", "VEHICLE"},  {"detectObj.confidence", rescaleBox.confidence}};
            jsonData["frame_ID"][std::to_string(frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
            jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["detectObj"]["VEHICLE"].push_back(det);
        }

        for (auto& box : humanBBoxList)
        {
            BoundingBox rescaleBox;
            utils::rescaleBBox(box, rescaleBox, MODEL_WIDTH, MODEL_HEIGHT, FRAME_WIDTH, FRAME_HEIGHT);
            json det = {{"detectObj.x1", rescaleBox.x1}, {"detectObj.y1", rescaleBox.y1},
                        {"detectObj.x2", rescaleBox.x2}, {"detectObj.y2", rescaleBox.y2},
                        {"detectObj.label", "HUMAN"},    {"detectObj.confidence", rescaleBox.confidence}};
            jsonData["frame_ID"][std::to_string(frameIdx)]["detectObj"]["HUMAN"].push_back(det);
            jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["detectObj"]["HUMAN"].push_back(det);
        }
    }

    if (m_bSaveTrackObj)
    {
        json track = {{"tailingObj.x1", tailingObject.bbox.x1},
                      {"tailingObj.y1", tailingObject.bbox.y1},
                      {"tailingObj.x2", tailingObject.bbox.x2},
                      {"tailingObj.y2", tailingObject.bbox.y2},
                      {"tailingObj.label", tailingObject.classStr},
                      {"tailingObj.distanceToCamera", tailingObject.distanceToCamera},
                      {"tailingObj.id", tailingObject.id}};
        jsonData["frame_ID"][std::to_string(frameIdx)]["tailingObj"].push_back(track);
        jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["tailingObj"].push_back(track);
    }

    if (m_bDebugProfiling)
    {
        json profile = {{"inferenceTime", inferenceTime}, {"bufferSize", bufferSize}};
        jsonData["frame_ID"][std::to_string(frameIdx)]["debugProfile"].push_back(profile);
        jsonDataCurrentFrame["frame_ID"][std::to_string(frameIdx)]["debugProfile"].push_back(profile);
    }
    std::string jsonCurrentFrameString = jsonDataCurrentFrame.dump();
    // Convert the JSON object to a string with indentation
    if (m_bShowJson)
    {
#ifndef SPDLOG_USE_SYSLOG
        logger->debug("====================================================================================");
#endif
        logger->debug("json:{}", jsonCurrentFrameString);
#ifndef SPDLOG_USE_SYSLOG
        logger->debug("====================================================================================");
#endif
    }

    std::string jsonString = jsonDataCurrentFrame.dump(4);
    if (m_bSaveToJSONFile)
        _saveJsonLogFile(jsonString);

    return jsonCurrentFrameString;
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
    std::ofstream outFile(m_jsonFilePath, std::ios::app);
    if (outFile)
    {
        // Add a newline before the new entry if the file is not empty
        if (outFile.tellp() > 0)
            outFile << std::endl;

        outFile << jsonString; // Adjust the indentation as needed
        logger->debug("Append new line to the file");
    }
    else
        logger->error("Unable to open the file for writing");
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