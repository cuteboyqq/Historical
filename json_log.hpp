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

#ifndef __JSON_LOG__
#define __JSON_LOG__

#include "json.hpp"
#include <fstream>
#include <vector>
#include "bounding_box.hpp"
#include "dataStructures.h"
#include "adas_config_reader.hpp"
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

using namespace std;

class JSON_LOG
{
public:
    JSON_LOG(std::string file, ADAS_Config_S* m_config);
    ~JSON_LOG();

    void logInfo(WNC_ADAS_Results adasResult, std::vector<BoundingBox> m_humanBBoxList,
                 std::vector<BoundingBox> m_vehicleBBoxList, std::vector<BoundingBox> m_roadSignBBoxList,
                 Object& m_tailingObject, int m_frameIdx);

    void send_json_log(const char *json_log, const char *server_ip, int server_port);
    std::string get_local_ip();

protected:
    void _saveJsonLogFile(std::string jsonString);

    int m_modelWidth  = 576;
    int m_modelHeight = 320;
    int m_frameWidth  = 576;
    int m_frameHeight = 320;

    bool m_bShowJson       = true;
    bool m_bSaveTrackObj   = true;
    bool m_bSaveLaneInfo   = true;
    bool m_bSaveDetObjLog  = true;
    bool m_bSaveVanishLine = true;
    bool m_bSaveLDWLog     = true;
    bool m_bSaveFCWLog     = true;
    bool m_bSaveToJSONFile = 
#ifdef SAV837
        false
#else
        true
#endif
        ;
    bool m_sendJSONLog = true;

    std::string m_serverIP = "192.168.1.10";
    int m_port = 5000;

    std::string m_jsonFilePath;
};

#endif