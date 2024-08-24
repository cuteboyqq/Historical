/*
 * module_adas.cpp- Sigmastar
 *
 * Copyright (C) 2021 Sigmastar Technology Corp.
 *
 * Author: jeff.li <jeff.li@sigmastar.com.cn>
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 */

//==============================================================================
//
//                              INCLUDE FILES
//
//==============================================================================

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <sys/ipc.h>
#include <sys/msg.h>
#include <fcntl.h>

#include "module_common.h"
#include "module_adas.h"
#include "module_scl.h"
#include "mid_common.h"
#include "adas.h"
#include "ldws.h"
#include "bcam_adas.h"
#include "module_fb.h"
// #include "module_font.h"
#include "IPC_cardvInfo.h"
#include "adasShm_client.h"

// WNC-Yolo-Adas star
// #include "dla_base.h"

// #include "dla_base_class.h"

#define dis_WNC_ADAS 0 // turn off original Vendor supported ADAS content.

#include "dla_app.h"
#include "wnc_adas.hpp"
#include "event.h"
using namespace std;

// Alsiter add
#include <iostream>
#include <fstream>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

// CIpuInterface* g_IpuIntfObject;
// CIpuCommon* g_IpuIntfObject;
WNC_ADAS *g_IpuIntfObject;
// WNC-Yolo-Adas end

#define notify_interval 10
unsigned long g_last_notify = 0;

#define FIFO_NAME_ADAS "/tmp/.test_live"

#if CARDV_ADAS_ENABLE

#ifdef DEBUG_BUILD
#define __adas_print_str(x) syslog(LOG_INFO, #x "\n");
#define __adas_print_int(x) syslog(LOG_INFO, #x ": %d\n", x)
#elif RELEASE_BUILD
#define __adas_print_str(x)
#define __adas_print_int(x)
#else
#define __adas_print_str(x)
#define __adas_print_int(x)
#endif

typedef struct _ADAS_Context
{
    MI_SYS_ChnPort_t src_chn_port;

    struct
    {
        char      name[32];
        BOOL      thread_exit;
        pthread_t thread;
    } thread_param;

    struct
    {
        MI_BOOL ldws;
        MI_BOOL fcws;
        MI_BOOL sag;
        MI_BOOL bsd;
        MI_BOOL bcws;
    } feature;

    struct
    {
        int (*adas_get_buf_info)(unsigned short width, unsigned short height);

        ADAS_init_error_type (*adas_init)(unsigned short width, unsigned short height, unsigned char *working_buf_ptr,
                                          int working_buf_len, ADAS_init_params *params);

        ADAS_error_type (*adas_process)(const unsigned char *src, ADAS_set_info *params);

        int (*adas_enable)(ADAS_enable_params *ADAS_en);

        int (*adas_get_result)(ADAS_results *result);

        int (*adas_set_params)(ADAS_process_params *params);

        int (*adas_wait_process_done)(void);

        int (*adas_abort_process)(void);

        unsigned int (*adas_GetLibVersion)(unsigned int *ver);

        void (*adas_set_calibration)(int calibration_status);

        void (*adas_set_symmetry)(int symmetry_status);
    } api;
} ADAS_Context;

//==============================================================================
//
//                              GLOBAL VARIABLES
//
//==============================================================================

#if (ADAS_DRAW_INFO)
MI_SYS_WindowRect_t last_stRect    = {0, 0, 0, 0};
MI_SYS_WindowRect_t current_stRect = {0, 0, 0, 0};

ldws_params_t last_lane_info;
ldws_params_t current_lane_info;

Color_t white_Color = {255, 255, 255, 255};
Color_t black_Color = {255, 0, 0, 0};
Color_t red_Color   = {255, 255, 0, 0};
Color_t blue_Color  = {255, 0, 0, 255};

CarDV_FontData_t g_fontData_last;
CarDV_FontData_t g_fontData_new;
#endif

int                  adas_print_msg = 0;
static ADAS_Context *f_adas_ctx;
static ADAS_Context *r_adas_ctx;
ADAS_ATTR_t          gFrontAdasAttr = {.feature{.ldws = 0, .fcws = 0, .sag = 0, .bsd = 0, .bcws = 0}};
ADAS_ATTR_t          gRearAdasAttr = {.feature{.ldws = 0, .fcws = 0, .sag = 0, .bsd = 0, .bcws = 0}};

//==============================================================================
//
//                              EXTERN VARIABLES
//
//==============================================================================

extern CarDV_Info carInfo;
IPU_DlaInfo_S     gstDlaInfo;

//==============================================================================
//
//                              FUNCTIONS
//
//==============================================================================

static void *Adas_Task(void *args);
static void *Adas_Task_ImageMode(void *args);
static MI_S32 ADAS_SetFeature(ADAS_Context *adas_ctx, MI_U8 ldws, MI_U8 fcws, MI_U8 sag, MI_U8 bsd, MI_U8 bcws);
static MI_S32 ADAS_SetChannelPort(ADAS_Context *adas_ctx, MI_SYS_ChnPort_t *chanel_port);

#if (ADAS_DRAW_INFO)
void rotate(int origin_w, int origin_h, int origin_x, int origin_y, int *x, int *y)
{
#if (0) // 90 degree
    *x = origin_h - 1 - origin_y;
    *y = origin_x;
#elif (1) // 270 degree
    *x                             = origin_y;
    *y                             = origin_w - 1 - origin_x;
#else
    *x = origin_x;
    *y = origin_y;
#endif
}

#if dis_WNC_ADAS
void Show_FCar_Distance(MI_U32 distance)
{
    char   text_tt[2]  = {0};
    MI_U32 u32BuffSize = 0;
    MI_U8  text[2]     = {0};

    sprintf(text_tt, "%d", distance);
    strcpy((char *)text, text_tt);
    CARDV_WARN("distance:%d text is %s text_tt:%s \n", distance, text, text_tt);

    Color_t fColor;
    Color_t bColor;
    memset(&fColor, 0, sizeof(Color_t));
    memset(&bColor, 0, sizeof(Color_t));

    g_fontData_new.offset = 0;
    g_fontData_new.pmt    = E_MI_RGN_PIXEL_FORMAT_ARGB1555;
    int hzLen             = cardv_Font_Strlen(text); // calculate bytes

    // nFontSize = font width *nMultiple, 8, 12, 16, 24, 32, 48...
    int nFontSize = cardv_Font_GetSizeByType(FONT_SIZE_32);

    g_fontData_new.height = nFontSize;
    if (E_MI_RGN_PIXEL_FORMAT_ARGB1555 == g_fontData_new.pmt)
    {
        g_fontData_new.stride = nFontSize * hzLen * 2; // 1555 so,2bytes
        memcpy(&fColor, &white_Color, sizeof(Color_t));
    }
    else if (E_MI_RGN_PIXEL_FORMAT_I4 == g_fontData_new.pmt)
    {
        g_fontData_new.stride = nFontSize * hzLen / 2;
        fColor.a              = 0x00;
        fColor.r              = 15 & 0x0F; // refer to module_osd:OSD_DrawVideoStamp
        fColor.g              = 0x00;
        fColor.b              = 0x00;
    }
    CARDV_WARN("fmt:%d,len:%d,nFontsize:%d,height:%d,width:%d \n", g_fontData_new.pmt, hzLen, nFontSize,
               g_fontData_new.height, g_fontData_new.stride);

    if (g_fontData_new.height != 0)
    {
        u32BuffSize = g_fontData_new.stride * g_fontData_new.height;

        if (NULL == (g_fontData_new.buffer = (MI_U8 *)malloc(u32BuffSize)))
        {
            CARDV_ERR("malloc buffer err\n");
            return;
        }
        // CARDV_WARN("malloc buffer :%p size:%d \n",g_fontData_new.buffer,u32BuffSize);

        MI_U16 *pt  = (MI_U16 *)g_fontData_new.buffer;
        MI_U16  end = (u32BuffSize) / 2;

        for (int ii = 0; ii < end; ii++)
        {
            *pt = 0x801F;
            pt++;
        }
    }

    memcpy(&bColor, &blue_Color, sizeof(Color_t));

    if (MI_SUCCESS != cardv_Font_DrawText(&g_fontData_new, text, 0, FONT_SIZE_32, &fColor, &bColor, 0, FALSE))
    {
        CARDV_WARN("cardv_Font_DrawText error \n");
    }

#if (CARDV_FB_ENABLE)
    ST_Fb_DrawNum(&g_fontData_new, TRUE);
#endif

    if (NULL != g_fontData_new.buffer)
    {
        free(g_fontData_new.buffer);
        g_fontData_new.buffer = NULL;
    }
}

void Draw_FCar_Distance(MI_U8 distance, BOOL show)
{
#if (CARDV_FB_ENABLE)
    if (show == FALSE)
    {
        ST_FB_SyncDirtyDown();
        ST_Fb_DrawNum(&g_fontData_last, FALSE);
        memset(&g_fontData_new, 0, sizeof(g_fontData_new));
        memcpy(&g_fontData_last, &g_fontData_new, sizeof(g_fontData_last));
    }
    else
    {
        ST_FB_SyncDirtyDown();
        ST_Fb_DrawNum(&g_fontData_last, FALSE);
        Show_FCar_Distance(distance);
        memcpy(&g_fontData_last, &g_fontData_new, sizeof(g_fontData_last));
        // memset(&g_fontData_new,0,sizeof(g_fontData_new));//note this !
    }

    MI_SYS_WindowRect_t canvas;
    canvas.u16X      = 0;
    canvas.u16Y      = 0;
    canvas.u16Width  = 896;
    canvas.u16Height = 512;
    ST_FB_SyncDirtyUp(&canvas);
    // ST_Fb_SetColorKey(ARGB888_BLUE);
    ST_Fb_SetColorKey(0);
    ST_FB_Show(TRUE);
#endif
}

#endif
void Draw_Lane_Line(ldws_params_t lane_info, BOOL isDraw)
{
#if (CARDV_FB_ENABLE)
    MI_SYS_WindowRect_t canvas;
    MI_U32              u32Color = 0;
    int                 x1 = 0, y1 = 0, x2 = 0, y2 = 0;

    ////////////////////////////////////////////////////////////////////////////
    // 2023/6/27 PM 04:17:08,Hubert
    // Verify Alpha
    // MI_FB_GlobalAlpha_t stAlphaInfo;
    ////////////////////////////////////////////////////////////////////////////

    // Fixme: less than zero mean what?
    if ((lane_info.left_lane[0].x < 0) || (lane_info.left_lane[0].y < 0) || (lane_info.left_lane[1].x < 0)
        || (lane_info.left_lane[1].y < 0) || (lane_info.right_lane[0].x < 0) || (lane_info.right_lane[0].y < 0)
        || (lane_info.right_lane[1].x < 0) || (lane_info.right_lane[1].y < 0))
    {
        // CARDV_ERR("Please tell me what is this mean and how do deal with it ! \n");
        return;
    }

    if ((lane_info.left_lane[0].x >= 432) || (lane_info.left_lane[0].y >= 240) || (lane_info.left_lane[1].x >= 432)
        || (lane_info.left_lane[1].y >= 240) || (lane_info.right_lane[0].x >= 432) || (lane_info.right_lane[0].y >= 240)
        || (lane_info.right_lane[1].x >= 432) || (lane_info.right_lane[1].y >= 240))
    {
        return;
    }

    if (isDraw == FALSE)
    {
        // if not need to draw ,so clean up last Rectangle!
        ST_FB_SyncDirtyDown();
        if ((lane_info.left_lane[0].x == lane_info.left_lane[1].x) && (lane_info.left_lane[0].x == 0))
        {
            // doing nothing;
        }
        else if ((lane_info.right_lane[0].x == lane_info.right_lane[1].x) && (lane_info.right_lane[0].x == 0))
        {
            // doing nothing;
        }
        else
        {
            rotate(896, 512, last_lane_info.left_lane[0].x * 896 / 432, last_lane_info.left_lane[0].y * 512 / 240, &x1,
                   &y1);
            rotate(896, 512, last_lane_info.left_lane[1].x * 896 / 432, last_lane_info.left_lane[1].y * 512 / 240, &x2,
                   &y2);
            // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
            ST_Fb_FillLine2(x1, y1, x2, y2, ARGB888_BLUE, 1); // left line
            rotate(896, 512, last_lane_info.right_lane[0].x * 896 / 432, last_lane_info.right_lane[0].y * 512 / 240,
                   &x1, &y1);
            rotate(896, 512, last_lane_info.right_lane[1].x * 896 / 432, last_lane_info.right_lane[1].y * 512 / 240,
                   &x2, &y2);
            // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
            ST_Fb_FillLine2(x1, y1, x2, y2, ARGB888_BLUE, 1); // right line
        }
        memset(&current_lane_info, 0, sizeof(ldws_params_t));
    }
    else
    {
        ST_FB_SyncDirtyDown();
        // clean up last lane
        rotate(896, 512, last_lane_info.left_lane[0].x * 896 / 432, last_lane_info.left_lane[0].y * 512 / 240, &x1,
               &y1);
        rotate(896, 512, last_lane_info.left_lane[1].x * 896 / 432, last_lane_info.left_lane[1].y * 512 / 240, &x2,
               &y2);
        // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
        ST_Fb_FillLine2(x1, y1, x2, y2, ARGB888_BLUE, 1); // left line
        rotate(896, 512, last_lane_info.right_lane[0].x * 896 / 432, last_lane_info.right_lane[0].y * 512 / 240, &x1,
               &y1);
        rotate(896, 512, last_lane_info.right_lane[1].x * 896 / 432, last_lane_info.right_lane[1].y * 512 / 240, &x2,
               &y2);
        // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
        ST_Fb_FillLine2(x1, y1, x2, y2, ARGB888_BLUE, 1); // right line

        // update lane
        u32Color = 0xFFFF00; // yellow color
        memcpy(&current_lane_info, &lane_info, sizeof(ldws_params_t));
        rotate(896, 512, current_lane_info.left_lane[0].x * 896 / 432, current_lane_info.left_lane[0].y * 512 / 240,
               &x1, &y1);
        rotate(896, 512, current_lane_info.left_lane[1].x * 896 / 432, current_lane_info.left_lane[1].y * 512 / 240,
               &x2, &y2);
        // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
        ST_Fb_FillLine2(x1, y1, x2, y2, u32Color, 1); // left line
        rotate(896, 512, current_lane_info.right_lane[0].x * 896 / 432, current_lane_info.right_lane[0].y * 512 / 240,
               &x1, &y1);
        rotate(896, 512, current_lane_info.right_lane[1].x * 896 / 432, current_lane_info.right_lane[1].y * 512 / 240,
               &x2, &y2);
        // syslog(LOG_INFO, "L%d [%d,%d]->[%d,%d]\n", __LINE__, x1, y1, x2, y2);
        ST_Fb_FillLine2(x1, y1, x2, y2, u32Color, 1); // right line
    }

    canvas.u16X      = 0;
    canvas.u16Y      = 0;
    canvas.u16Width  = 896;
    canvas.u16Height = 512;
    ST_FB_SyncDirtyUp(&canvas);
    // ST_Fb_SetColorKey(ARGB888_BLUE);
    ST_Fb_SetColorKey(0);

    ////////////////////////////////////////////////////////////////////////////
    // 2023/6/27 PM 04:17:08,Hubert
    // Verify Alpha
    // memset(&stAlphaInfo, 0, sizeof(MI_FB_GlobalAlpha_t));
    // ST_FB_GetAlphaInfo(&stAlphaInfo);
    // stAlphaInfo.bAlphaEnable  = TRUE;
    // stAlphaInfo.bAlphaChannel = 0;
    // stAlphaInfo.u8Alpha0      = 0;
    // stAlphaInfo.u8Alpha1      = 0;
    // stAlphaInfo.u8GlobalAlpha = 0x80;
    // ST_FB_SetAlphaInfo(&stAlphaInfo);

    ////////////////////////////////////////////////////////////////////////////

    ST_FB_Show(TRUE);
    // update data
    memcpy(&last_lane_info, &current_lane_info, sizeof(ldws_params_t));
#endif
}

void Draw_FCar_Rectangle(fcws_info_t fcws_info, BOOL isDraw)
{
#if (CARDV_FB_ENABLE)
    MI_SYS_WindowRect_t canvas;
    MI_U32              u32Color = 0;

    if (isDraw == FALSE)
    {
        // if not need to draw ,so clean up last Rectangle!
        ST_FB_SyncDirtyDown();
        ST_Fb_DrawRect(&last_stRect, ARGB888_BLUE);
        memset(&current_stRect, 0, sizeof(MI_SYS_WindowRect_t));
    }
    else
    {
        // need to clean last Firstly!
        ST_FB_SyncDirtyDown();
        ST_Fb_DrawRect(&last_stRect, ARGB888_BLUE);
        u32Color                 = 0xFFFFFF; // white color
        current_stRect.u16X      = fcws_info.car_x * 896 / 432;
        current_stRect.u16Y      = fcws_info.car_y * 512 / 240;
        current_stRect.u16Width  = fcws_info.car_width * 896 / 432;
        current_stRect.u16Height = fcws_info.car_height * 512 / 240;
        ST_Fb_DrawRect(&current_stRect, u32Color);
    }

    canvas.u16X      = 0;
    canvas.u16Y      = 0;
    canvas.u16Width  = 896;
    canvas.u16Height = 512;
    ST_FB_SyncDirtyUp(&canvas);
    // ST_Fb_SetColorKey(ARGB888_BLUE);
    ST_Fb_SetColorKey(0);
    ST_FB_Show(TRUE);

    // update data
    memcpy(&last_stRect, &current_stRect, sizeof(MI_SYS_WindowRect_t));
#endif
}
#endif

static ADAS_Context *ADAS_Create(MI_BOOL bIsForntAdas, ADAS_ATTR_t *pAttr)
{
    ADAS_Context *p_adas_ctx = (ADAS_Context *)malloc(sizeof(ADAS_Context));

    if (p_adas_ctx)
    {
        p_adas_ctx->thread_param.thread_exit = 0;
        p_adas_ctx->thread_param.thread      = 0;

        if (pAttr)
        {
            ADAS_SetFeature(p_adas_ctx, pAttr->feature.ldws, pAttr->feature.fcws, pAttr->feature.sag,
                            pAttr->feature.bsd, pAttr->feature.bcws);

            ADAS_SetChannelPort(p_adas_ctx, &pAttr->stSrcChnPort);
        }

        if (bIsForntAdas)
        {
            strcpy(p_adas_ctx->thread_param.name, "front_adas_task");
            p_adas_ctx->api.adas_abort_process     = ADAS_abort_process;
            p_adas_ctx->api.adas_enable            = ADAS_enable;
            p_adas_ctx->api.adas_GetLibVersion     = ADAS_GetLibVersion;
            p_adas_ctx->api.adas_get_buf_info      = ADAS_get_buffer_info;
            p_adas_ctx->api.adas_get_result        = ADAS_get_result;
            p_adas_ctx->api.adas_init              = ADAS_init;
            p_adas_ctx->api.adas_process           = ADAS_process;
            p_adas_ctx->api.adas_set_calibration   = ADAS_set_calibration;
            p_adas_ctx->api.adas_set_params        = ADAS_set_params;
            p_adas_ctx->api.adas_set_symmetry      = ADAS_set_symmetry;
            p_adas_ctx->api.adas_wait_process_done = ADAS_wait_process_done;
        }
        else
        {
            strcpy(p_adas_ctx->thread_param.name, "rear_adas_task");
            p_adas_ctx->api.adas_abort_process     = BCam_ADAS_abort_process;
            p_adas_ctx->api.adas_enable            = BCam_ADAS_enable;
            p_adas_ctx->api.adas_GetLibVersion     = BCam_ADAS_GetLibVersion;
            p_adas_ctx->api.adas_get_buf_info      = BCam_ADAS_get_buffer_info;
            p_adas_ctx->api.adas_get_result        = BCam_ADAS_get_result;
            p_adas_ctx->api.adas_init              = BCam_ADAS_init;
            p_adas_ctx->api.adas_process           = BCam_ADAS_process;
            p_adas_ctx->api.adas_set_calibration   = BCam_ADAS_set_calibration;
            p_adas_ctx->api.adas_set_params        = BCam_ADAS_set_params;
            p_adas_ctx->api.adas_set_symmetry      = BCam_ADAS_set_symmetry;
            p_adas_ctx->api.adas_wait_process_done = BCam_ADAS_wait_process_done;
        }
    }
    return p_adas_ctx;
}

static MI_S32 ADAS_Destory(ADAS_Context **pp_adas_ctx)
{
    free(*pp_adas_ctx);
    *pp_adas_ctx = NULL;
    return 0;
}

static MI_S32 ADAS_SetFeature(ADAS_Context *adas_ctx, MI_U8 ldws, MI_U8 fcws, MI_U8 sag, MI_U8 bsd, MI_U8 bcws)
{
    adas_ctx->feature.ldws = ldws;
    adas_ctx->feature.fcws = fcws;
    adas_ctx->feature.sag  = sag;
    adas_ctx->feature.bsd  = bsd;
    adas_ctx->feature.bcws = bcws;
    return 0;
}

static MI_S32 ADAS_SetChannelPort(ADAS_Context *adas_ctx, MI_SYS_ChnPort_t *chanel_port)
{
    adas_ctx->src_chn_port = *chanel_port;
    return 0;
}

// static MI_S32 ADAS_Run(ADAS_Context *adas_ctx)
// {
//     int ret;

//     ret = pthread_create(&adas_ctx->thread_param.thread, NULL, Adas_Task, adas_ctx);
//     if (0 == ret)
//     {
//         pthread_setname_np(adas_ctx->thread_param.thread, adas_ctx->thread_param.name);
//         return 0;
//     }
//     else
//     {
//         return -1;
//     }
// }

/* Add Historical Mode Code*/
static MI_S32 ADAS_Run(ADAS_Context *adas_ctx, WNC_ADAS *g_IpuIntfObject)
{
    int         ret;
    int         MODE           = g_IpuIntfObject->m_yoloADAS->m_historical->m_InputMode;
    std::string raw_images_dir = g_IpuIntfObject->m_yoloADAS->m_historical->m_rawImageDir;
    std::string video          = g_IpuIntfObject->m_yoloADAS->m_historical->m_videoPath;
    char        type[]         = "1";
    //--------------------------Please Do not Remove below Note------------------
    //--------------Because maybe customer want video mode back.....------------
    // if (MODE == 1)
    // {
    //     cout << "==============FUNC: ADAS_Run================" << endl;
    //     cout << "         Video Mode" << endl;

    //     if (access(video.c_str(), F_OK) != -1)
    //     {
    //         printf("video path exists\n");
    //     }
    //     else
    //     {
    //         printf("*******************Error message********************************************\n");
    //         printf("*                                                                          *\n");
    //         printf("*  Video path doesn't exist, Please check video path is correct or not     *\n");
    //         printf("*  Note : Video path is set in /customer/adas/config/config.txt            *\n");
    //         printf("*                                                                          *\n");
    //         printf("*******************Error message********************************************\n");
    //         return -1;
    //     }

    //     player_running(video.c_str(), type);

    //     ret = pthread_create(&adas_ctx->thread_param.thread, NULL, Adas_Task_VideoMode, adas_ctx);
    // }
    if (MODE == 2)
    {
        cout << "==============FUNC: ADAS_Run================" << endl;
        cout << "         Image Mode" << endl;
        ret = pthread_create(&adas_ctx->thread_param.thread, NULL, Adas_Task_ImageMode, adas_ctx);
    }
    else if (MODE == 0)
    {
        cout << "==============FUNC: ADAS_Run================" << endl;
        cout << "        Sensor Mode" << endl;
        ret = pthread_create(&adas_ctx->thread_param.thread, NULL, Adas_Task, adas_ctx);
    }
    else if (MODE == 1)
    {
        cout << "==============FUNC: ADAS_Run================" << endl;
        cout << "         Video Mode" << endl;
        cout << " Note : Video mode is removed at 2024-06-12" << endl;
        cout << " No video mode is available !! Exit now" << endl;
    }
    else
    {
        cout << "Please enter below mode" << endl;
        cout << "0: Sensor mode" << endl;
        cout << "2: Image mode" << endl;
    }

    system("killall -SIGUSR1 diag");
    syslog(LOG_NOTICE, "[%s %d] send check to diag \n", __func__, __LINE__);
    if (0 == ret)
    {
        pthread_setname_np(adas_ctx->thread_param.thread, adas_ctx->thread_param.name);
        return 0;
    }
    else
    {
        return -1;
    }
}

static MI_S32 ADAS_Stop(ADAS_Context *adas_ctx)
{
    adas_ctx->thread_param.thread_exit = TRUE;
    pthread_join(adas_ctx->thread_param.thread, NULL);
    adas_ctx->api.adas_abort_process();
    adas_ctx->api.adas_wait_process_done();
    return 0;
}

static S32 ADAS_SourceImageWH(ADAS_Context *adas_ctx, U32 *width, U32 *height)
{
    MI_SYS_ChnPort_t *pSrcChnPort = &adas_ctx->src_chn_port;

    if (E_MI_MODULE_ID_SCL == pSrcChnPort->eModId)
    {
        MI_SCL_OutPortParam_t stSclOutputParam;
        memset(&stSclOutputParam, 0x0, sizeof(MI_SCL_OutPortParam_t));
        MI_SCL_GetOutputPortParam((MI_SCL_DEV)pSrcChnPort->u32DevId, pSrcChnPort->u32ChnId, pSrcChnPort->u32PortId,
                                  &stSclOutputParam);
        *width  = stSclOutputParam.stSCLOutputSize.u16Width;
        *height = stSclOutputParam.stSCLOutputSize.u16Height;

        return 0;
    }
    else
    {
        syslog(LOG_ALERT, "NOT support ADAS input module [%d]\n", pSrcChnPort->eModId);
        *width  = 0;
        *height = 0;

        return -1;
    }
}

// add notify adas event to iox
static MI_S32 notify_event_to_iox(time_t ra_time, int event_type, float ttc, float distance, int left_right)
{
    int           iRet   = -1;
    int           iMsqId = -1;
    time_t        dwTime;
    T_AdasInfoMsg msg;

    msg.iType      = MSG_TYPE_CarAdasEvent;
    msg.iCommand   = event_type; // MSG_CMD_EVENT_FCW MSG_CMD_EVENT_LDW ;
    msg.ra_time    = ra_time;
    msg.left_right = left_right;
    msg.ttc        = ttc;
    msg.distance   = distance;
    iMsqId         = msgget(MSG_KEY_CAR, IPC_CREAT | 0666);

    if (iMsqId < 0)
    {
        return iRet;
    }
    if ((msgsnd(iMsqId, (void *)&msg, sizeof(T_AdasInfoMsg) - sizeof(int), IPC_NOWAIT)) == -1)
        syslog(LOG_ALERT, "[%s %d] msgsnd fail!!!!\n", __func__, __LINE__);

    return 0;
}

static MI_S32 process_event_record(time_t ra_time, int iInterval, int command)
{
    int         iRet   = -1;
    int         iMsqId = -1;
    time_t      dwTime;
    T_CommonMsg msg;

    msg.iType     = MSG_TYPE_CarEvent;
    msg.iCommand  = command;
    msg.ra_time   = ra_time;
    msg.iInterval = iInterval;

    iMsqId = msgget(MSG_KEY_CAR, IPC_CREAT | 0666);

    if (iMsqId < 0)
    {
        syslog(LOG_ALERT, "[%s %d] msgget fail\n", __func__, __LINE__);
        return iRet;
    }
    if ((msgsnd(iMsqId, (void *)&msg, sizeof(T_CommonMsg) - sizeof(int), IPC_NOWAIT)) == -1)
        syslog(LOG_ALERT, "[%s %d] msgsnd fail\n", __func__, __LINE__);

    return 0;
}
void cardv_send_to_adas_fifo()
{
#if 1
    if (access(FIFO_NAME_ADAS, F_OK) == -1)
    {
        // FIFO does not exist, create it
        if (mkfifo(FIFO_NAME_ADAS, 0777) != 0)
        {
            syslog(LOG_CRIT, "[%s %d] Error creating FIFO.\n", __FUNCTION__, __LINE__);
            exit(EXIT_FAILURE);
        }
        else
        {
            syslog(LOG_INFO, "[%s %d] FIFO created successfully.\n", __FUNCTION__, __LINE__);
        }
    }
    else
    {
        syslog(LOG_INFO, "[%s %d] FIFO already exists.\n", __FUNCTION__, __LINE__);
    }

    int pipe_fd_w = 0;
    pipe_fd_w     = open(FIFO_NAME_ADAS, O_RDWR);
    if (pipe_fd_w >= 0)
    {
        // syslog(LOG_NOTICE, "%s  %d \n", __func__, __LINE__);
        write(pipe_fd_w, "hi", 2);
        close(pipe_fd_w);
    }
#endif
}

// void send_image_and_log_live_mode(const cv::Mat &displayImg, const char *json_log, const char *server_ip,
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

static S32 ADAS_GetSrcImage(ADAS_Context *adas_ctx, U8 **source_image, MI_SYS_BUF_HANDLE *hHandle)
{
    MI_S32           s32Ret = 0;
    MI_SYS_BufInfo_t stBufInfo;

    bool             success = ADAS_FAILURE;
    WNC_ADAS_Results adasResult;
    unsigned long    now_time  = 0;
    int              iInterval = 20;
    static int       callCount = 0;

#ifdef SPDLOG_USE_SYSLOG
    auto m_logger = spdlog::get("adas");
#else
    auto m_logger = spdlog::get("ADAS");
#endif

    // syslog(LOG_INFO,"WNC check source ID[%s \t %d]\n", __FUNCTION__, __LINE__);
    // syslog(LOG_INFO,"[&adas_ctx->src_chn_port.eModId \t %d]\n", adas_ctx->src_chn_port.eModId);
    // syslog(LOG_INFO,"[&adas_ctx->src_chn_port.u32DevId \t %d]\n", adas_ctx->src_chn_port.u32DevId);
    // syslog(LOG_INFO,"[&adas_ctx->src_chn_port.u32ChnId \t %d]\n", adas_ctx->src_chn_port.u32ChnId);
    // syslog(LOG_INFO,"[&adas_ctx->src_chn_port.u32PortId \t %d]\n", adas_ctx->src_chn_port.u32PortId);

    s32Ret = MI_SYS_ChnOutputPortGetBuf(&adas_ctx->src_chn_port, &stBufInfo, hHandle);
    if (MI_SUCCESS == s32Ret)
    {
        // 	[WNC]
        // void *pViraddr = NULL;
        // if (stBufInfo.eBufType == E_MI_SYS_BUFDATA_FRAME)
        // {
        //     pViraddr      = stBufInfo.stFrameData.pVirAddr[0];
        //     *source_image = static_cast<unsigned char *>(pViraddr);
        //     return 0;
        // }
        // 	[WNC]

        // 	[WNC] add WNC YOLOADAS service

        if ((++callCount % 10) == 0)
        {
            cardv_send_to_adas_fifo();
        }
        // Convert buffered image to cv::Mat
        MI_S32 s32Ret = MI_SUCCESS;
        auto   time_0 = std::chrono::high_resolution_clock::now();
        auto   time_1 = std::chrono::high_resolution_clock::now();

        std::string server_ip   = g_IpuIntfObject->m_config->HistoricalFeedModeConfig.serverIP;
        int         server_port = g_IpuIntfObject->m_config->HistoricalFeedModeConfig.serverPort;

        // Check pixel format
        if ((stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_ABGR8888)
            && (stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_ARGB8888)
            && (stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_YUV_SEMIPLANAR_420))
        {
            m_logger->error("ERROR!!! Pixel format is not valid");
            success = ADAS_FAILURE;
            exit(1);
        }

        // m_logger->debug("Start converting buffered image to cv::Mat");
        g_IpuIntfObject->_validateInputBuffer((MI_SYS_BufInfo_t *)&stBufInfo);
        g_IpuIntfObject->m_frameNum++;

        int  predFrameIdx;
        bool getPrediction;
        int  egoVelocity = static_cast<int>(adasShm_client_getRoadSpeed());

        if (g_IpuIntfObject->m_frameNum % g_IpuIntfObject->m_frameStep_wnc == 0)
        {
            m_logger->debug("");
            m_logger->debug("========================================");
            m_logger->debug("Frame Index: {}", g_IpuIntfObject->m_resultFrameIdx + 1);
            m_logger->debug("========================================");
            m_logger->debug("[gear] : {}", adasShm_client_getGear());
            m_logger->debug("[roadSpeed] : {}", adasShm_client_getRoadSpeed());
            m_logger->debug("[engineSpeed] : {}", adasShm_client_getEngineSpeed());
            m_logger->debug("[engineLoad] : {}", adasShm_client_getEngineLoad());

            // Update YOLO-ADAS frame buffer
            g_IpuIntfObject->m_yoloADAS->updateInputFrame(g_IpuIntfObject->m_aiInputImage,
                                                          g_IpuIntfObject->m_frameIdx_wnc);
            g_IpuIntfObject->_updateFrameIndex();
        }

        // Get last prediction
        YOLOADAS_Prediction pred;
        if (g_IpuIntfObject->m_yoloADAS->getLastestPrediction(pred, predFrameIdx))
            g_IpuIntfObject->m_yoloADASPostProc->updatePredictionBuffer(pred, predFrameIdx);

        if (!g_IpuIntfObject->m_yoloADASPostProc->getLastestResult(g_IpuIntfObject->m_procResult,
                                                                   g_IpuIntfObject->m_resultFrameIdx))
        {
            if (MI_SUCCESS != MI_SYS_ChnOutputPortPutBuf(*hHandle))
                m_logger->error("MI_SYS_ChnOutputPortPutBuf error!");
            *source_image = 0;
            return -1;
        }

        success = g_IpuIntfObject->_laneLineDetection() && g_IpuIntfObject->_objectDetection()
                          && g_IpuIntfObject->_objectFiltering() && g_IpuIntfObject->_objectTracking(egoVelocity)
                          && g_IpuIntfObject->_laneDepartureDetection() && g_IpuIntfObject->_forwardCollisionDetection()
                      ? ADAS_SUCCESS
                      : ADAS_FAILURE;

        if (success == ADAS_FAILURE)
            m_logger->warn("One or more of ADAS subtask failed");

        // Show Results
        g_IpuIntfObject->_showDetectionResults();

        // Save Results to Debug Logs
        if (g_IpuIntfObject->m_dbg_saveLogs)
            g_IpuIntfObject->_saveLogResults();

        // Draw and Save Results
        if (g_IpuIntfObject->m_dsp_results && success == ADAS_SUCCESS)
        {
            g_IpuIntfObject->_drawResults();
            if (g_IpuIntfObject->m_dbg_saveImages)
                g_IpuIntfObject->_saveDrawResults();
        }

        g_IpuIntfObject->m_yoloADAS->getDebugProfiles(g_IpuIntfObject->m_inferenceTime,
                                                      g_IpuIntfObject->m_inputBufferSize);

        if (g_IpuIntfObject->m_config->stDebugConfig.saveRawImages
            || g_IpuIntfObject->m_config->HistoricalFeedModeConfig.inputMode == 2)
        {
            g_IpuIntfObject->getResults(adasResult);
            std::string jsonLog = g_IpuIntfObject->m_jsonLog->logInfo(
                adasResult, g_IpuIntfObject->m_humanBBoxList, g_IpuIntfObject->m_vehicleBBoxList,
                g_IpuIntfObject->m_roadSignBBoxList, g_IpuIntfObject->m_tailingObject,
                g_IpuIntfObject->m_resultFrameIdx, g_IpuIntfObject->m_inferenceTime,
                g_IpuIntfObject->m_inputBufferSize);

            if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 0)
            {
                // send_image_and_log_live_mode(g_IpuIntfObject->m_aiInputImage, jsonlog.c_str(), server_ip.c_str(),
                //                              server_port, g_IpuIntfObject->m_resultFrameIdx);
                g_IpuIntfObject->m_socket->send_image_and_log_live_mode(g_IpuIntfObject->m_aiInputImage,
                                                                        jsonLog.c_str(), server_ip.c_str(), server_port,
                                                                        g_IpuIntfObject->m_resultFrameIdx);
            }
            else if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 1)
            {
                // g_IpuIntfObject->m_jsonLog->send_json_log(jsonlog.c_str(), server_ip.c_str(), server_port);
                g_IpuIntfObject->m_socket->send_json_log(jsonLog.c_str(), server_ip.c_str(), server_port);
            }
        }
        else
        {
            if (success == ADAS_SUCCESS)
            {
                g_IpuIntfObject->getResults(adasResult);
                std::string jsonLog = g_IpuIntfObject->m_jsonLog->logInfo(
                    adasResult, g_IpuIntfObject->m_humanBBoxList, g_IpuIntfObject->m_vehicleBBoxList,
                    g_IpuIntfObject->m_roadSignBBoxList, g_IpuIntfObject->m_tailingObject,
                    g_IpuIntfObject->m_resultFrameIdx, g_IpuIntfObject->m_inferenceTime,
                    g_IpuIntfObject->m_inputBufferSize);

                if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 0)
                {
                    // send_image_and_log_live_mode(g_IpuIntfObject->m_aiInputImage, jsonLog.c_str(), server_ip.c_str(),
                    //                              server_port, g_IpuIntfObject->m_resultFrameIdx);
                    g_IpuIntfObject->m_socket->send_image_and_log_live_mode(
                        g_IpuIntfObject->m_aiInputImage, jsonLog.c_str(), server_ip.c_str(), server_port,
                        g_IpuIntfObject->m_resultFrameIdx);
                }
                else if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 1)
                {
                    // g_IpuIntfObject->m_jsonLog->send_json_log(jsonlog.c_str(), server_ip.c_str(), server_port);
                    g_IpuIntfObject->m_socket->send_json_log(jsonLog.c_str(), server_ip.c_str(), server_port);
                }
            }
        }

        if (g_IpuIntfObject->m_estimateTime)
        {
            time_1 = std::chrono::high_resolution_clock::now();
            m_logger->info("");
            m_logger->info("Processing Time: {} ms",
                           std::chrono::duration_cast<std::chrono::nanoseconds>(time_1 - time_0).count()
                               / (1000.0 * 1000));
        }

        // Currently event Type is:ADAS_EVENT_LDW_LEFT ADAS_EVENT_LDW_RIGHT ADAS_EVENT_FCW
        if (adasResult.eventType != ADAS_EVENT_NORMAL)
        {
            now_time = time(NULL);
            if (adasResult.eventType == ADAS_EVENT_LDW_LEFT)
            {
                if (g_IpuIntfObject->m_dbg_notify_ldw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_LDW, sizeof(WAV_PATH_CARD_LDW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_LDW) + 1);
                }
                m_logger->debug("Detect LDW Left Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d now_time %ld\n", __func__, __LINE__, now_time);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_LDW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_LDW, 0.0, 0.0, 0);
                }
            }
            else if (adasResult.eventType == ADAS_EVENT_LDW_RIGHT)
            {
                if (g_IpuIntfObject->m_dbg_notify_ldw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_LDW, sizeof(WAV_PATH_CARD_LDW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_LDW) + 1);
                }
                m_logger->debug("Detect LDW Right Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d now_time %ld\n", __func__, __LINE__, now_time);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_LDW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_LDW, 0.0, 0.0, 1);
                }
            }
            else if (adasResult.eventType == ADAS_EVENT_FCW)
            {
                float currTTC        = 0;
                float followDistance = -1;
                for (const auto object : adasResult.objList)
                {
                    if (object.currTTC > 0)
                    {
                        currTTC = object.currTTC;
                        m_logger->debug("[TTC] : {}", currTTC);
                    }
                }
                followDistance = g_IpuIntfObject->m_tailingObject.distanceToCamera;
                m_logger->debug("[followDistance] : {}", followDistance);

                if (g_IpuIntfObject->m_dbg_notify_fcw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_FCW, sizeof(WAV_PATH_CARD_FCW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_FCW) + 1);
                }
                m_logger->debug("Detect FCW Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d \n", __func__, __LINE__);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_FCW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_FCW, currTTC, followDistance, 0);
                }
            }
            else
            {
                syslog(LOG_ALERT, "%s  %d Unknow type \n", __func__, __LINE__);
            }
            g_last_notify = now_time;
        }

        if (MI_SUCCESS != MI_SYS_ChnOutputPortPutBuf(*hHandle)) // wnc modify to hHandle from stBufHandle
        {
            m_logger->error("MI_SYS_ChnOutputPortPutBuf error");
            *source_image = 0;
            return -1;
        }
        // 	[WNC] add WNC YOLOADAS service
    }
    else
    {
        m_logger->warn("Failed to fetch system buffer"); // 	[WNC] add WNC YOLOADAS service
        // g_IpuIntfObject->logInfo("Failed to fetch system buffer!", __FUNCTION__, LOG_WARNING);

        success = ADAS_FAILURE; // 	[WNC] add WNC YOLOADAS service
    }

    *source_image = 0;
    return -1;
}

// void send_image(const std::string &image_path, const char *server_ip, int server_port)
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

// void send_image_and_log(const std::string &image_path, const char *json_log, const char *server_ip, int server_port,
//                         int frame_index)
// {
//     int                sock = 0;
//     struct sockaddr_in serv_addr;
//     char *             json_log_message = (char *)json_log;

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

//     std::cout << "Sending image of size: " << size << " bytes\n";

//     // Send the frame_index
//     uint32_t frame_index_net = htonl(frame_index); // Convert to network byte order
//     send(sock, reinterpret_cast<const char *>(&frame_index_net), sizeof(frame_index_net), 0);

//     // Send the size of the image
//     uint32_t image_size = static_cast<uint32_t>(size);
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

static S32 ADAS_GetSrcImage_FromImage(ADAS_Context *adas_ctx, U8 **source_image, MI_SYS_BUF_HANDLE *hHandle)
{
    MI_S32           s32Ret = 0;
    MI_SYS_BufInfo_t stBufInfo;

    bool             success = ADAS_FAILURE;
    WNC_ADAS_Results adasResult;
    unsigned long    now_time  = 0;
    int              iInterval = 20;
    static int       callCount = 0;

#ifdef SPDLOG_USE_SYSLOG
    auto m_logger = spdlog::get("adas");
#else
    auto m_logger = spdlog::get("ADAS");
#endif

    s32Ret = MI_SYS_ChnOutputPortGetBuf(&adas_ctx->src_chn_port, &stBufInfo, hHandle);
    if (MI_SUCCESS == s32Ret)
    {
        if ((++callCount % 10) == 0)
        {
            cardv_send_to_adas_fifo();
        }
        // Convert buffered image to cv::Mat
        MI_S32 s32Ret = MI_SUCCESS;
        auto   time_0 = std::chrono::high_resolution_clock::now();
        auto   time_1 = std::chrono::high_resolution_clock::now();

        // Check pixel format
        if ((stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_ABGR8888)
            && (stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_ARGB8888)
            && (stBufInfo.stFrameData.ePixelFormat != E_MI_SYS_PIXEL_FRAME_YUV_SEMIPLANAR_420))
        {
            m_logger->error("ERROR!!! Pixel format is not valid");
            // g_IpuIntfObject->logInfo("Pixel format is not valid!", __FUNCTION__, LOG_ERR);
            success = ADAS_FAILURE;
            exit(1);
        }
        //-------------------------Image mode : Get image from directory--------------------------
        MI_U32 u16ModelWidth  = 0;
        MI_U32 u16ModelHeight = 0;
        u16ModelHeight        = MODEL_HEIGHT;
        u16ModelWidth         = MODEL_WIDTH;
        //------------------------------------------------------------------------------
        // Get save PNG image directory
        std::string m_dbg_rawImgsDir = g_IpuIntfObject->m_config->HistoricalFeedModeConfig.rawImageDir;
        int         maxFrameIndex    = g_IpuIntfObject->m_max_counters;
        // m_max_counters = m_config->HistoricalFeedModeConfig.ImageModeEndFrame;
        // m_historicalFrameName = m_config->HistoricalFeedModeConfig.ImageModeFrameName;

        //-----------------------------------------------------------------------------------
        string imagedir = m_dbg_rawImgsDir;
        string image_name =
            g_IpuIntfObject->m_historicalFrameName + std::to_string(g_IpuIntfObject->m_counters) + ".png";
        string imagePath = imagedir + '/' + image_name;
        printf("%s\n", imagePath.c_str());
        cv::Mat imgFrame = cv::imread(imagePath, cv::IMREAD_UNCHANGED);

        if (imgFrame.empty())
        {
            printf("imgFrame is empty \n");
            return E_MI_ERR_FAILED;
            // return -1;
        }

        if (g_IpuIntfObject->m_counters > maxFrameIndex)
        {
            printf("frame index is larger than %d \n", maxFrameIndex);
            return E_MI_ERR_FAILED;
        }

        // Alsiter add 2024-07-31
        std::string server_ip   = g_IpuIntfObject->m_config->HistoricalFeedModeConfig.serverIP;
        int         server_port = g_IpuIntfObject->m_config->HistoricalFeedModeConfig.serverPort;

        cv::cvtColor(imgFrame, imgFrame, cv::COLOR_RGB2RGBA);

        int im_height = imgFrame.rows;
        int im_width  = imgFrame.cols;

        if (im_height != u16ModelHeight && im_width != u16ModelWidth)
        {
            cv::resize(imgFrame, imgFrame, cv::Size(u16ModelWidth, u16ModelHeight));
        }

        if (g_IpuIntfObject->m_dsp_results) // m_dsp_results
        {
            g_IpuIntfObject->m_displayImg = imgFrame.clone();
        }

        g_IpuIntfObject->m_aiInputImage = imgFrame.clone();

        // model inference
        // Single Thread function
        g_IpuIntfObject->m_yoloADAS->_run(g_IpuIntfObject->m_aiInputImage, g_IpuIntfObject->m_counters);

        g_IpuIntfObject->m_counters = g_IpuIntfObject->m_counters + 1;
        //---------------------------------------------------------------------------------------------

        if (g_IpuIntfObject->m_frameIdx_wnc >= 0)
        {
            m_logger->debug("");
            m_logger->debug("========================================");
            m_logger->debug("Frame Index: {}", g_IpuIntfObject->m_frameIdx_wnc);
            m_logger->debug("========================================");
            m_logger->debug("[gear] : {}", adasShm_client_getGear());
            m_logger->debug("[roadSpeed] : {}", adasShm_client_getRoadSpeed());
            m_logger->debug("[engineSpeed] : {}", adasShm_client_getEngineSpeed());
            m_logger->debug("[engineLoad] : {}", adasShm_client_getEngineLoad());

            int egoVelocity = static_cast<int>(adasShm_client_getEngineSpeed());

            // Get last prediction
            YOLOADAS_Prediction pred;
            int                 predFrameIdx;
            int                 resultFrameIdx;

            if (g_IpuIntfObject->m_yoloADAS->getLastestPrediction(pred, predFrameIdx))
                g_IpuIntfObject->m_yoloADASPostProc->updatePredictionBuffer(pred, predFrameIdx);

            // Run post-process (Func)
            // Single Thread function
            g_IpuIntfObject->m_yoloADASPostProc->runProcessing();

            bool resultBuffer =
                g_IpuIntfObject->m_yoloADASPostProc->getLastestResult(g_IpuIntfObject->m_procResult, resultFrameIdx);

            if (!resultBuffer)
            {
                if (MI_SUCCESS != MI_SYS_ChnOutputPortPutBuf(*hHandle)) // wnc modify to hHandle from stBufHandle
                {
                    m_logger->error("MI_SYS_ChnOutputPortPutBuf error!");
                }
                *source_image = 0;
                return -1;
            }

            if (resultBuffer)
            {
                success = g_IpuIntfObject->_laneLineDetection() && g_IpuIntfObject->_objectDetection()
                                  && g_IpuIntfObject->_objectFiltering()
                                  && g_IpuIntfObject->_objectTracking(egoVelocity)
                                  && g_IpuIntfObject->_laneDepartureDetection()
                                  && g_IpuIntfObject->_forwardCollisionDetection()
                              ? ADAS_SUCCESS
                              : ADAS_FAILURE;

                if (success == ADAS_FAILURE)
                    m_logger->warn("One or more of ADAS subtask failed");

                // Show Results
                g_IpuIntfObject->_showDetectionResults();

                // Save Results to Debug Logs
                if (g_IpuIntfObject->m_dbg_saveLogs)
                    g_IpuIntfObject->_saveLogResults();

                // Draw and Save Results
                if (g_IpuIntfObject->m_dsp_results && g_IpuIntfObject->m_dbg_saveImages && success == ADAS_SUCCESS)
                {
                    g_IpuIntfObject->_drawResults();
                    g_IpuIntfObject->_saveDrawResults();
                }

                // if (g_IpuIntfObject->m_dbg_saveRawImages)
                //     g_IpuIntfObject->_saveRawImages();

                g_IpuIntfObject->m_yoloADAS->getDebugProfiles(g_IpuIntfObject->m_inferenceTime,
                                                              g_IpuIntfObject->m_inputBufferSize);

                // if (success == ADAS_SUCCESS)
                // {
                // JSON Format Info
                g_IpuIntfObject->getResults(adasResult);
                std::string jsonLog = g_IpuIntfObject->m_jsonLog->logInfo(
                    adasResult, g_IpuIntfObject->m_humanBBoxList, g_IpuIntfObject->m_vehicleBBoxList,
                    g_IpuIntfObject->m_roadSignBBoxList, g_IpuIntfObject->m_tailingObject, resultFrameIdx,
                    g_IpuIntfObject->m_inferenceTime, g_IpuIntfObject->m_inputBufferSize);

                if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 0)
                {
                    // send_image_and_log(imagePath, json_log.c_str(), server_ip.c_str(), server_port,
                    //                    resultFrameIdx); // Alister add 2024-05-05

                    g_IpuIntfObject->m_socket->send_image_and_log_and_frameIdx_and_imgPath(
                        imagePath, jsonLog.c_str(), server_ip.c_str(), server_port, resultFrameIdx);
                    // send_image_and_log_live_mode(imgFrame_3ch, jsonLog.c_str(), server_ip.c_str(), server_port,
                    //                              resultFrameIdx); // Alister add 2024-05-05
                }
                else if (g_IpuIntfObject->m_config->HistoricalFeedModeConfig.visualizeMode == 1)
                {
                    // g_IpuIntfObject->m_jsonLog->send_json_log(jsonlog.c_str(), server_ip.c_str(), server_port);
                    g_IpuIntfObject->m_socket->send_json_log(jsonLog.c_str(), server_ip.c_str(), server_port);
                }

                // printf(json_log_str.c_str()); // Alister add 2024-05-23
                // printf("\n");
                g_IpuIntfObject->_updateFrameIndex();

                // }
            } // END if(resultBuffer)
        }
        else
        {
            usleep(10);
        }
        // g_IpuIntfObject->_updateFrameIndex();

        if (g_IpuIntfObject->m_estimateTime)
        {
            time_1 = std::chrono::high_resolution_clock::now();
            m_logger->info("");
            m_logger->info("Processing Time: {} ms",
                           std::chrono::duration_cast<std::chrono::nanoseconds>(time_1 - time_0).count()
                               / (1000.0 * 1000));
        }

        // Currently event Type is:ADAS_EVENT_LDW_LEFT ADAS_EVENT_LDW_RIGHT ADAS_EVENT_FCW
        if (adasResult.eventType != ADAS_EVENT_NORMAL)
        {
            now_time = time(NULL);
            if (adasResult.eventType == ADAS_EVENT_LDW_LEFT)
            {
                if (g_IpuIntfObject->m_dbg_notify_ldw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_LDW, sizeof(WAV_PATH_CARD_LDW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_LDW) + 1);
                }
                m_logger->debug("Detect LDW Left Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d now_time %ld\n", __func__, __LINE__, now_time);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_LDW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_LDW, 0.0, 0.0, 0);
                }
            }
            else if (adasResult.eventType == ADAS_EVENT_LDW_RIGHT)
            {
                if (g_IpuIntfObject->m_dbg_notify_ldw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_LDW, sizeof(WAV_PATH_CARD_LDW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_LDW) + 1);
                }
                m_logger->debug("Detect LDW Right Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d now_time %ld\n", __func__, __LINE__, now_time);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_LDW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_LDW, 0.0, 0.0, 1);
                }
            }
            else if (adasResult.eventType == ADAS_EVENT_FCW)
            {
                float currTTC        = 0;
                float followDistance = -1;
                for (const auto object : adasResult.objList)
                {
                    if (object.currTTC > 0)
                    {
                        currTTC = object.currTTC;
                        m_logger->debug("[TTC] : {}", currTTC);
                    }
                }
                followDistance = g_IpuIntfObject->m_tailingObject.distanceToCamera;
                m_logger->debug("[followDistance] : {}", followDistance);

                if (g_IpuIntfObject->m_dbg_notify_fcw)
                {
                    MI_S8 audioparam[64];
                    audioparam[0] = 1;
                    memcpy(&audioparam[1], WAV_PATH_CARD_FCW, sizeof(WAV_PATH_CARD_FCW));
                    cardv_send_cmd(CMD_AUDIO_OUT_PLAY, (MI_S8 *)audioparam, sizeof(WAV_PATH_CARD_FCW) + 1);
                }
                m_logger->debug("Detect FCW Event!");

                if ((now_time - g_last_notify) >= notify_interval)
                {
                    syslog(LOG_INFO, "%s  %d \n", __func__, __LINE__);
                    process_event_record(now_time, iInterval, MSG_CMD_EVENT_FCW);
                    notify_event_to_iox(now_time, MSG_CMD_EVENT_FCW, currTTC, followDistance, 0);
                }
            }
            else
            {
                syslog(LOG_ALERT, "%s  %d Unknow type \n", __func__, __LINE__);
            }
            g_last_notify = now_time;
        }

        if (MI_SUCCESS != MI_SYS_ChnOutputPortPutBuf(*hHandle)) // wnc modify to hHandle from stBufHandle
        {
            m_logger->error("MI_SYS_ChnOutputPortPutBuf error");
            *source_image = 0;
            return -1;
        }
        // 	[WNC] add WNC YOLOADAS service
    }
    else
    {
        m_logger->warn("Failed to fetch system buffer"); // 	[WNC] add WNC YOLOADAS service
        // g_IpuIntfObject->logInfo("Failed to fetch system buffer!", __FUNCTION__, LOG_WARNING);

        success = ADAS_FAILURE; // 	[WNC] add WNC YOLOADAS service
    }

    *source_image = 0;
    return -1;
}

static S32 ADAS_ReturnSrcImage(MI_SYS_BUF_HANDLE hHandle)
{
    MI_SYS_ChnOutputPortPutBuf(hHandle);
    return 0;
}

bool ADAS_IsAnyFeatureEnable(ADAS_ATTR_t *adas_attr)
{
    if (adas_attr->feature.ldws || adas_attr->feature.fcws || adas_attr->feature.sag || adas_attr->feature.bsd
        || adas_attr->feature.bcws)
        return TRUE;
    else
        return FALSE;
}

#if dis_WNC_ADAS
static ADAS_error_type ADAS_DoOneFrame(ADAS_Context *adas_ctx, unsigned char *source_image)
{
    ADAS_error_type ADAS_err;
    ADAS_results    ADAS_result;
    ADAS_set_info   ADAS_info;

#if 0 //(GPS_CONNECT_ENABLE)
    if (GPSCtrl_GPS_IsValidValue())
    {
        ADAS_info.gps_params.gps_state = 1; // With GPS and GPS signal
        ADAS_info.gps_params.gps_speed = GPSCtrl_GetSpeed(0);
    }
    else
    {
        ADAS_info.gps_params.gps_state = 0; // With GPS but no GPS signal
        ADAS_info.gps_params.gps_speed = -1;
    }
#else
    ADAS_info.gps_params.gps_state = 0; // Without GPS
    ADAS_info.gps_params.gps_speed = -1;
#endif
    ADAS_info.day_or_night = 1;

    // ADAS_err = ADAS_process(source_image, &ADAS_info);
    ADAS_err = adas_ctx->api.adas_process(source_image, &ADAS_info);
    if (ADAS_err == ADAS_ERR_NONE)
    {
        // ADAS_get_result(&ADAS_result);
        adas_ctx->api.adas_get_result(&ADAS_result);
        // if user disable certain function, the pointer of the function result will be NULL.
        if (ADAS_result.LDWS_result != NULL)
        {
            if ((ADAS_result.LDWS_result->ldws_params.state != LDWS_STATE_NODETECT)
                && (ADAS_result.LDWS_result->ldws_err_state == LDWS_ERR_NONE))
            {
                ADAS_DBG_MSG(adas_print_msg & 0x2,
                             "[LDWS] Err State [%d] State [%d] Left [%03d, %03d] to [%03d, %03d] Right [%03d, %03d] to "
                             "[%03d, %03d]\n",
                             ADAS_result.LDWS_result->ldws_err_state, ADAS_result.LDWS_result->ldws_params.state,
                             ADAS_result.LDWS_result->ldws_params.left_lane[0].x,
                             ADAS_result.LDWS_result->ldws_params.left_lane[0].y,
                             ADAS_result.LDWS_result->ldws_params.left_lane[1].x,
                             ADAS_result.LDWS_result->ldws_params.left_lane[1].y,
                             ADAS_result.LDWS_result->ldws_params.right_lane[0].x,
                             ADAS_result.LDWS_result->ldws_params.right_lane[0].y,
                             ADAS_result.LDWS_result->ldws_params.right_lane[1].x,
                             ADAS_result.LDWS_result->ldws_params.right_lane[1].y);
            }
#if (ADAS_DRAW_INFO)
            ldws_params_t cur_line_info;
            memcpy(&cur_line_info, &(ADAS_result.LDWS_result->ldws_params), sizeof(ldws_params_t));
            Draw_Lane_Line(cur_line_info, TRUE);
#else
            memcpy(&carInfo.stAdasInfo.stLdwsInfo, &(ADAS_result.LDWS_result->ldws_params), sizeof(ldws_params_t));
            carInfo.stAdasInfo.bLdwsVaild = TRUE;
#endif
        }
        else
        {
#if (ADAS_DRAW_INFO)
            ldws_params_t cur_line_info;
            memset(&cur_line_info, 0, sizeof(ldws_params_t));
            Draw_Lane_Line(cur_line_info, FALSE);
#else
            carInfo.stAdasInfo.bLdwsVaild = FALSE;
            memset(&carInfo.stAdasInfo.stLdwsInfo, 0, sizeof(ldws_params_t));
#endif
        }

        if (ADAS_result.FCWS_result_C != NULL)
        {
            if (ADAS_result.FCWS_result_C->state == FCWS_STATE_FIND && ADAS_result.FCWS_result_C->distance != 99)
            {
                ADAS_DBG_MSG(adas_print_msg & 0x2,
                             "[FCWS] State [%d] Pos [%03d, %03d] WH [%03d, %03d] Distance [%03d]\n",
                             ADAS_result.FCWS_result_C->state, ADAS_result.FCWS_result_C->car_x,
                             ADAS_result.FCWS_result_C->car_y, ADAS_result.FCWS_result_C->car_width,
                             ADAS_result.FCWS_result_C->car_height, ADAS_result.FCWS_result_C->distance);
#if (ADAS_DRAW_INFO)
                fcws_info_t cur_fcws_info;
                memcpy(&cur_fcws_info, ADAS_result.FCWS_result_C, sizeof(fcws_info_t));
                Draw_FCar_Rectangle(cur_fcws_info, TRUE);
                Draw_FCar_Distance(ADAS_result.FCWS_result_C->distance, TRUE);
#else
                memcpy(&carInfo.stAdasInfo.stFcwsInfo, ADAS_result.FCWS_result_C, sizeof(fcws_info_t));
                carInfo.stAdasInfo.bFcwsVaild = TRUE;
#endif
            }
            else if (ADAS_result.FCWS_result_C->state == FCWS_STATE_LOSE || ADAS_result.FCWS_result_C->distance == 99)
            {
#if (ADAS_DRAW_INFO)
                // find front car, but distance(99) is too long
                fcws_info_t cur_fcws_info;
                memset(&cur_fcws_info, 0, sizeof(fcws_info_t));
                Draw_FCar_Rectangle(cur_fcws_info, FALSE);
                Draw_FCar_Distance(99, FALSE);
#else
                carInfo.stAdasInfo.bFcwsVaild = FALSE;
                memset(&carInfo.stAdasInfo.stFcwsInfo, 0, sizeof(fcws_info_t));
#endif
            }
        }
        else
        {
#if (ADAS_DRAW_INFO)
            // not find front car
            fcws_info_t cur_fcws_info;
            Draw_FCar_Rectangle(cur_fcws_info, FALSE);
#else
            carInfo.stAdasInfo.bFcwsVaild = FALSE;
            memset(&carInfo.stAdasInfo.stFcwsInfo, 0, sizeof(fcws_info_t));
#endif
        }

        if (ADAS_result.SAG_result != NULL)
        {
            ADAS_DBG_MSG(adas_print_msg & 0x2, "[SAG] State [%d]\n", ADAS_result.SAG_result->true_state);
        }

#if !(ADAS_DRAW_INFO)
        IPC_CarInfo_Write_AdasInfo(&carInfo.stAdasInfo);
#endif
    }

    return ADAS_err;
}

#endif

static void *Adas_Task(void *args)
{
    int                buf_len;
    unsigned char *    buf_ptr;
    ADAS_init_params   stAdasInitParam;
    ADAS_enable_params stAdasEnableParam;
    adas_input_t       adas_input;
    LdwsSetupPosi      ldws_setup_posi;
    int                m_Calibrated_y_start, m_Calibrated_y_end, m_Camera_height;
    MI_U32             u32AdasWidth, u32AdasHeight;
    int                ret;
    ADAS_Context *     adas_ctx = (ADAS_Context *)args;

    CARDV_THREAD();

#if (ADAS_DRAW_INFO)
    ret = ST_Fb_Init();
    if (ret != 0)
    {
        CARDV_ERR("ST_Fb_Init err [%d]\n", ret);
    }

    // Test only begin!
    if (0)
    {
        MI_SYS_WindowRect_t stRect;
        MI_U32              u32Color = 0;
        u32Color                     = 0xFFFFFF; // white
        // u32Color = 0x0000FF;//blue
        stRect.u16X      = 0;
        stRect.u16Y      = 0;
        stRect.u16Width  = 896; // 432  -->896
        stRect.u16Height = 512; // 240 -->512
        ST_FB_SyncDirtyDown();
        ST_Fb_FillLine2(202 * 896 / 432, 134 * 512 / 240, 124 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(202,134) (124,195) left line
        ST_Fb_FillLine2(202 * 896 / 432, 134 * 512 / 240, 293 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(202,134) (293,195) right line
        ST_Fb_FillLine2(124 * 896 / 432, 195 * 512 / 240, 293 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(124,195) (293,195) base line
        ST_FB_SyncDirtyUp(&stRect);
        // ST_Fb_SetColorKey(ARGB888_BLUE);
        ST_Fb_SetColorKey(0);
        ST_FB_Show(TRUE);

        // Test only begin !
        // CARDV_WARN("yyj test car distance car\n");
        // Draw_FCar_Distance(79,TRUE);
        // Test only end !
    }
// Test only end !
#endif

    ret = ADAS_SourceImageWH(adas_ctx, &u32AdasWidth, &u32AdasHeight);
    if (ret < 0)
    {
        syslog(LOG_ALERT, "ADAS: get width, height error\n"); // goto err_exit;
        pthread_exit(NULL);
    }

    //////////////////////// value from user calibration program ////////////////////////
    m_Calibrated_y_start                     = 120;
    m_Calibrated_y_end                       = 210;
    m_Camera_height                          = 120; // cetimeter
    stAdasInitParam.user_calib_y_start       = m_Calibrated_y_start;
    stAdasInitParam.user_calib_y_end         = m_Calibrated_y_end;
    stAdasInitParam.user_calib_camera_height = m_Camera_height;
    //////////////////////// value from user calibration program ////////////////////////

    //////////////////////// value from LDWS calibration ////////////////////////
    ldws_setup_posi                                           = LDWS_SETUP_CENTER;
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationImageWidth  = 432;  // laneCalibrationImageWidth
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationImageHeight = 240;  // laneCalibrationImageHeight
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationUpPointX    = 202;  // laneCalibrationUpPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationUpPointY    = 134;  // laneCalibrationUpPointY
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationLeftPointX  = 124;  // laneCalibrationLeftPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationLeftPointY  = 195;  // laneCalibrationLeftPointY
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationRightPointX = 293;  // laneCalibrationRightPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationRightPointY = 195;  // laneCalibrationRightPointY
    carInfo.stAdasInfo.stCalibInfo.departureHighThr1          = 768;  // departureHighThr1
    carInfo.stAdasInfo.stCalibInfo.departureHighThr2          = 1024; // departureHighThr2
    carInfo.stAdasInfo.stCalibInfo.departureMiddleThr1        = 307;  // departureMiddleThr1
    carInfo.stAdasInfo.stCalibInfo.departureMiddleThr2        = 332;  // departureMiddleThr2
    carInfo.stAdasInfo.stCalibInfo.departureLowThr1           = 230;  // departureLowThr1
    carInfo.stAdasInfo.stCalibInfo.departureLowThr2           = 282;  // departureLowThr2
    carInfo.stAdasInfo.stCalibInfo.minLaneRatioX256           = 204;  // minLaneRatioX256
    carInfo.stAdasInfo.stCalibInfo.maxLaneRatioX256           = 512;  // maxLaneRatioX256
    carInfo.stAdasInfo.stCalibInfo.alarmShowCnt               = 10;   // alarmShowCnt

#if !(ADAS_DRAW_INFO)
    carInfo.stAdasInfo.bCalibVaild = TRUE;
    IPC_CarInfo_Write_AdasInfo(&carInfo.stAdasInfo);
#endif

    adas_input.image_width       = u32AdasWidth;  // input width of source image
    adas_input.image_height      = u32AdasHeight; // input height of source image
    adas_input.dz_N              = 9;             // downsample ratio N
    adas_input.dz_M              = 40;            // downsample ratio M
    adas_input.camera_focal      = 330;           // focal length (mm * 100)
    adas_input.sensor_cell_width = 280;           // sensor cell size (um * 100)

    stAdasInitParam.LDWS_input_params.LDWS_params = carInfo.stAdasInfo.stCalibInfo;
    stAdasInitParam.LDWS_input_params.LDWS_pos    = ldws_setup_posi;
    stAdasInitParam.ADAS_input_params             = adas_input;

    memset(&stAdasEnableParam, 0x00, sizeof(ADAS_enable_params));
    stAdasEnableParam.LDWS_enable = adas_ctx->feature.ldws;
    stAdasEnableParam.FCWS_enable = adas_ctx->feature.fcws;
    stAdasEnableParam.SAG_enable  = adas_ctx->feature.sag;
    stAdasEnableParam.BSD_enable  = adas_ctx->feature.bsd;
    stAdasEnableParam.BCWS_enable = adas_ctx->feature.bcws;
    ret                           = adas_ctx->api.adas_enable(&stAdasEnableParam);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "ADAS Enable Ret [%d]\n", ret);

    buf_len = adas_ctx->api.adas_get_buf_info(u32AdasWidth, u32AdasHeight);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "Buf Len [%d]\n", buf_len);

    buf_ptr = (unsigned char *)malloc(buf_len);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "Buf Ptr [%p]\n", buf_ptr);

    adas_ctx->api.adas_set_calibration(1);

    ADAS_init_error_type ADAS_init_err =
        adas_ctx->api.adas_init(u32AdasWidth, u32AdasHeight, buf_ptr, buf_len, &stAdasInitParam);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "ADAS Init Ret [%d]\n", ADAS_init_err);

    // get image data
    MI_S32            s32Ret = 0;
    MI_SYS_BUF_HANDLE hHandle;
    unsigned char *   source_image = NULL;

    MI_S32         s32Fd = -1;
    fd_set         read_fds;
    struct timeval TimeoutVal;
    // int total_frame=0;

    s32Ret = MI_SYS_GetFd(&adas_ctx->src_chn_port, &s32Fd);
    if (MI_SUCCESS != s32Ret)
    {
        ADAS_DBG_ERR(1, "MI_SYS_GetFd err [%x]\n", s32Ret);
    }
#if 0	
	struct timeval start, end;
	gettimeofday(&start, NULL);
#endif
    // auto time_0 = std::chrono::high_resolution_clock::now();
    while (adas_ctx->thread_param.thread_exit == FALSE)
    {
        FD_ZERO(&read_fds);
        FD_SET(s32Fd, &read_fds);

        TimeoutVal.tv_sec  = 0;
        TimeoutVal.tv_usec = 1000 * 10;

        s32Ret = select(s32Fd + 1, &read_fds, NULL, NULL, &TimeoutVal);
        if (s32Ret < 0)
        {
            ADAS_DBG_ERR(1, "select failed!\n");
            continue;
        }
        else if (s32Ret == 0)
        {
            // Time Out
            continue;
        }
        else
        {
            if (FD_ISSET(s32Fd, &read_fds))
            {
                ret = ADAS_GetSrcImage(adas_ctx, &source_image, &hHandle); // WNC YOLO-ADAS entry point
// total_frame++;
#if dis_WNC_ADAS
                if (ret >= 0)
                {
                    ADAS_error_type ADAS_err;

                    // syslog(LOG_INFO,"ADAS_DoOneFrame\n");

                    if ((ADAS_err = ADAS_DoOneFrame(adas_ctx, source_image)) != 0)
                    {
                        ADAS_DBG_ERR(1, "ADAS Run Error [%d]\n", ADAS_err);
                    }

                    // MI_SYS_ChnOutputPortPutBuf(hHandle);
                    //}
                    ADAS_ReturnSrcImage(hHandle);
                }
#endif
            }
            else
            {
                syslog(LOG_ALERT, "fd_isset fail\n");
            }
        }
    }
// auto time_1 = std::chrono::high_resolution_clock::now();
// cout << "Processing Time: "
//      << std::chrono::duration_cast<std::chrono::nanoseconds>(time_1 - time_0).count() / (1000.0 * 1000) << endl;
#if (ADAS_DRAW_INFO)
    ret = ST_Fb_DeInit();
    if (ret != 0)
    {
        CARDV_ERR("ST_Fb_Init err [%d]\n", ret);
    }
#endif
#if 0
	//cal fps for adas
	gettimeofday(&end, NULL);
	double elapsedTime = (end.tv_sec - start.tv_sec) + (end.tv_usec - start.tv_usec) / 1000000.0;
	syslog(LOG_INFO, "Captured %d frames in %f seconds.\n", total_frame, elapsedTime);
#endif
    MI_SYS_CloseFd(s32Fd);
    pthread_exit(NULL);
}

static void *Adas_Task_ImageMode(void *args)
{
    int                buf_len;
    unsigned char *    buf_ptr;
    ADAS_init_params   stAdasInitParam;
    ADAS_enable_params stAdasEnableParam;
    adas_input_t       adas_input;
    LdwsSetupPosi      ldws_setup_posi;
    int                m_Calibrated_y_start, m_Calibrated_y_end, m_Camera_height;
    MI_U32             u32AdasWidth, u32AdasHeight;
    int                ret;
    ADAS_Context *     adas_ctx = (ADAS_Context *)args;

    CARDV_THREAD();

#if (ADAS_DRAW_INFO)
    ret = ST_Fb_Init();
    if (ret != 0)
    {
        CARDV_ERR("ST_Fb_Init err [%d]\n", ret);
    }

    // Test only begin!
    if (0)
    {
        MI_SYS_WindowRect_t stRect;
        MI_U32              u32Color = 0;
        u32Color                     = 0xFFFFFF; // white
        // u32Color = 0x0000FF;//blue
        stRect.u16X      = 0;
        stRect.u16Y      = 0;
        stRect.u16Width  = 896; // 432  -->896
        stRect.u16Height = 512; // 240 -->512
        ST_FB_SyncDirtyDown();
        ST_Fb_FillLine2(202 * 896 / 432, 134 * 512 / 240, 124 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(202,134) (124,195) left line
        ST_Fb_FillLine2(202 * 896 / 432, 134 * 512 / 240, 293 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(202,134) (293,195) right line
        ST_Fb_FillLine2(124 * 896 / 432, 195 * 512 / 240, 293 * 896 / 432, 195 * 512 / 240, u32Color,
                        3); //(124,195) (293,195) base line
        ST_FB_SyncDirtyUp(&stRect);
        // ST_Fb_SetColorKey(ARGB888_BLUE);
        ST_Fb_SetColorKey(0);
        ST_FB_Show(TRUE);

        // Test only begin !
        // CARDV_WARN("yyj test car distance car\n");
        // Draw_FCar_Distance(79,TRUE);
        // Test only end !
    }
// Test only end !
#endif

    ret = ADAS_SourceImageWH(adas_ctx, &u32AdasWidth, &u32AdasHeight);
    if (ret < 0)
    {
        syslog(LOG_ALERT, "ADAS: get width, height error\n"); // goto err_exit;
        pthread_exit(NULL);
    }

    //////////////////////// value from user calibration program ////////////////////////
    m_Calibrated_y_start                     = 120;
    m_Calibrated_y_end                       = 210;
    m_Camera_height                          = 120; // cetimeter
    stAdasInitParam.user_calib_y_start       = m_Calibrated_y_start;
    stAdasInitParam.user_calib_y_end         = m_Calibrated_y_end;
    stAdasInitParam.user_calib_camera_height = m_Camera_height;
    //////////////////////// value from user calibration program ////////////////////////

    //////////////////////// value from LDWS calibration ////////////////////////
    ldws_setup_posi                                           = LDWS_SETUP_CENTER;
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationImageWidth  = 432;  // laneCalibrationImageWidth
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationImageHeight = 240;  // laneCalibrationImageHeight
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationUpPointX    = 202;  // laneCalibrationUpPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationUpPointY    = 134;  // laneCalibrationUpPointY
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationLeftPointX  = 124;  // laneCalibrationLeftPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationLeftPointY  = 195;  // laneCalibrationLeftPointY
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationRightPointX = 293;  // laneCalibrationRightPointX
    carInfo.stAdasInfo.stCalibInfo.laneCalibrationRightPointY = 195;  // laneCalibrationRightPointY
    carInfo.stAdasInfo.stCalibInfo.departureHighThr1          = 768;  // departureHighThr1
    carInfo.stAdasInfo.stCalibInfo.departureHighThr2          = 1024; // departureHighThr2
    carInfo.stAdasInfo.stCalibInfo.departureMiddleThr1        = 307;  // departureMiddleThr1
    carInfo.stAdasInfo.stCalibInfo.departureMiddleThr2        = 332;  // departureMiddleThr2
    carInfo.stAdasInfo.stCalibInfo.departureLowThr1           = 230;  // departureLowThr1
    carInfo.stAdasInfo.stCalibInfo.departureLowThr2           = 282;  // departureLowThr2
    carInfo.stAdasInfo.stCalibInfo.minLaneRatioX256           = 204;  // minLaneRatioX256
    carInfo.stAdasInfo.stCalibInfo.maxLaneRatioX256           = 512;  // maxLaneRatioX256
    carInfo.stAdasInfo.stCalibInfo.alarmShowCnt               = 10;   // alarmShowCnt

#if !(ADAS_DRAW_INFO)
    carInfo.stAdasInfo.bCalibVaild = TRUE;
    IPC_CarInfo_Write_AdasInfo(&carInfo.stAdasInfo);
#endif

    adas_input.image_width       = u32AdasWidth;  // input width of source image
    adas_input.image_height      = u32AdasHeight; // input height of source image
    adas_input.dz_N              = 9;             // downsample ratio N
    adas_input.dz_M              = 40;            // downsample ratio M
    adas_input.camera_focal      = 330;           // focal length (mm * 100)
    adas_input.sensor_cell_width = 280;           // sensor cell size (um * 100)

    stAdasInitParam.LDWS_input_params.LDWS_params = carInfo.stAdasInfo.stCalibInfo;
    stAdasInitParam.LDWS_input_params.LDWS_pos    = ldws_setup_posi;
    stAdasInitParam.ADAS_input_params             = adas_input;

    memset(&stAdasEnableParam, 0x00, sizeof(ADAS_enable_params));
    stAdasEnableParam.LDWS_enable = adas_ctx->feature.ldws;
    stAdasEnableParam.FCWS_enable = adas_ctx->feature.fcws;
    stAdasEnableParam.SAG_enable  = adas_ctx->feature.sag;
    stAdasEnableParam.BSD_enable  = adas_ctx->feature.bsd;
    stAdasEnableParam.BCWS_enable = adas_ctx->feature.bcws;
    ret                           = adas_ctx->api.adas_enable(&stAdasEnableParam);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "ADAS Enable Ret [%d]\n", ret);

    buf_len = adas_ctx->api.adas_get_buf_info(u32AdasWidth, u32AdasHeight);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "Buf Len [%d]\n", buf_len);

    buf_ptr = (unsigned char *)malloc(buf_len);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "Buf Ptr [%p]\n", buf_ptr);

    adas_ctx->api.adas_set_calibration(1);

    ADAS_init_error_type ADAS_init_err =
        adas_ctx->api.adas_init(u32AdasWidth, u32AdasHeight, buf_ptr, buf_len, &stAdasInitParam);
    ADAS_DBG_MSG(adas_print_msg & 0x1, "ADAS Init Ret [%d]\n", ADAS_init_err);

    // get image data
    MI_S32            s32Ret = 0;
    MI_SYS_BUF_HANDLE hHandle;
    unsigned char *   source_image = NULL;

    MI_S32         s32Fd = -1;
    fd_set         read_fds;
    struct timeval TimeoutVal;
    // int total_frame=0;

    s32Ret = MI_SYS_GetFd(&adas_ctx->src_chn_port, &s32Fd);
    if (MI_SUCCESS != s32Ret)
    {
        ADAS_DBG_ERR(1, "MI_SYS_GetFd err [%x]\n", s32Ret);
    }
#if 0	
	struct timeval start, end;
	gettimeofday(&start, NULL);
#endif
    // auto time_0 = std::chrono::high_resolution_clock::now();
    while (adas_ctx->thread_param.thread_exit == FALSE)
    {
        FD_ZERO(&read_fds);
        FD_SET(s32Fd, &read_fds);

        TimeoutVal.tv_sec  = 0;
        TimeoutVal.tv_usec = 1000 * 10;

        s32Ret = select(s32Fd + 1, &read_fds, NULL, NULL, &TimeoutVal);
        if (s32Ret < 0)
        {
            ADAS_DBG_ERR(1, "select failed!\n");
            continue;
        }
        else if (s32Ret == 0)
        {
            // Time Out
            continue;
        }
        else
        {
            if (FD_ISSET(s32Fd, &read_fds))
            {
                ret = ADAS_GetSrcImage_FromImage(adas_ctx, &source_image, &hHandle); // WNC YOLO-ADAS entry point
// total_frame++;
#if dis_WNC_ADAS
                if (ret >= 0)
                {
                    ADAS_error_type ADAS_err;

                    // syslog(LOG_INFO,"ADAS_DoOneFrame\n");

                    if ((ADAS_err = ADAS_DoOneFrame(adas_ctx, source_image)) != 0)
                    {
                        ADAS_DBG_ERR(1, "ADAS Run Error [%d]\n", ADAS_err);
                    }

                    // MI_SYS_ChnOutputPortPutBuf(hHandle);
                    //}
                    ADAS_ReturnSrcImage(hHandle);
                }
#endif
            }
            else
            {
                syslog(LOG_ALERT, "fd_isset fail\n");
            }
        }
    }
// auto time_1 = std::chrono::high_resolution_clock::now();
// cout << "Processing Time: "
//      << std::chrono::duration_cast<std::chrono::nanoseconds>(time_1 - time_0).count() / (1000.0 * 1000) << endl;
#if (ADAS_DRAW_INFO)
    ret = ST_Fb_DeInit();
    if (ret != 0)
    {
        CARDV_ERR("ST_Fb_Init err [%d]\n", ret);
    }
#endif
#if 0
	//cal fps for adas
	gettimeofday(&end, NULL);
	double elapsedTime = (end.tv_sec - start.tv_sec) + (end.tv_usec - start.tv_usec) / 1000000.0;
	syslog(LOG_INFO, "Captured %d frames in %f seconds.\n", total_frame, elapsedTime);
#endif
    MI_SYS_CloseFd(s32Fd);
    pthread_exit(NULL);
}

// Check adas enable/disable file
bool Enabled_ADAS_function(const char *file_path)
{
    struct stat buffer;

    // Check if the file exists
    if (stat(file_path, &buffer) != 0)
    {
        syslog(LOG_NOTICE, "[%s %d] File %s does not exist. Running command...\n", __func__, __LINE__, file_path);
        // run_ADAS_command(true);
    }
    else
    {
        // Read values ​​from file
        FILE *file = fopen(file_path, "r");
        if (file == NULL)
        {
            syslog(LOG_ERR, "[%s %d] Failed to open file: %s\n", __func__, __LINE__, strerror(errno));
            return false;
        }

        int value = 0;
        if (fscanf(file, "%d", &value) != 1)
        {
            syslog(LOG_ERR, "[%s %d] Failed to read value from file: %d, errno: %s\n", __func__, __LINE__, value,
                   strerror(errno));
            fclose(file);
            return false;
        }
        fclose(file);

        // Check if the value is 0
        if (value == 0)
        {
            syslog(LOG_NOTICE, "[%s %d] File %s exists and value is 0. Running command...\n", __func__, __LINE__,
                   file_path);
            // run_ADAS_command(true);
        }
        else
        {
            syslog(LOG_NOTICE, "[%s %d] File %s exists and value is not 0. No action taken.\n", __func__, __LINE__,
                   file_path);
            return false;
        }
    }
    return true;
}

MI_S32 adas_process_cmd(CarDVCmdId id, MI_S8 *param, MI_S32 paramLen)
{
    MI_S32         s32ret       = 0;
    MI_BOOL        bIsFrontAdas = 1;
    ADAS_ATTR_t    attr;
    ADAS_Context **pp_adas_ctx = &f_adas_ctx;

    // if (adas_attr->chn_port.eModId == E_MI_MODULE_ID_MAX)
    //    return -1;

    switch (id)
    {
    case CMD_ADAS_REAR_INIT:
        bIsFrontAdas = 0;
        pp_adas_ctx  = &r_adas_ctx;
    case CMD_ADAS_INIT:
        if (*pp_adas_ctx == NULL)
        {
            syslog(LOG_ALERT, "ADAS: SPD Going to Drop all\n"); // goto err_exit;
            syslog(LOG_NOTICE, "[%s %d] ADAS open\n", __func__, __LINE__);

            if (!Enabled_ADAS_function("/misc/disable_adas"))
            {
                syslog(LOG_ERR, "[%s %d] Failed to enable ADAS function.\n", __func__, __LINE__);
                break;
            }

            //[WNC]
            // [WNC init parameter star]
            gstDlaInfo.bDlaUse                   = 1;
            gstDlaInfo.stIpuInitInfo.enModelType = (IPU_Model_Type_E)3;
            if (gstDlaInfo.bDlaUse == TRUE)
            {
                adasShm_client_init();
                MI_U32 u32Ret = 0;
                // choose inculde ipu (Intelligent process unit) firmware star
                char tmpStr[128] = "wnc_human_tracking/ipu_firmware.bin";
                // char* defFirmware = (char*)"/config/dla/ipu_firmware.bin";
                memcpy(gstDlaInfo.stIpuInitInfo.szIpuFirmware, tmpStr,
                       strlen(tmpStr)); // gstDlaInfo.stIpuInitInfo.szIpuFirmware = "yolov4_vpe/ipu_firmware.bin";
                // choose inculde ipu firmware end

                // choose inculde AI mudom star
                char dlaModel0_str[128] = "wnc_human_tracking/model/yolov5n_30m_fixed.sim_sgsimg.img";
                memcpy(gstDlaInfo.stIpuInitInfo.szModelFile, dlaModel0_str,
                       strlen(dlaModel0_str)); // gstDlaInfo.stIpuInitInfo.szModelFile = dlaModel0;
                syslog(LOG_INFO, "Get IPU model:%s\n", gstDlaInfo.stIpuInitInfo.szModelFile);
                // choose inculde AI mudom end

                gstDlaInfo.bDlaUse = u32Ret ? FALSE : TRUE;
            }
            // [WNC init parameter end]

            IPUInitAndStart(gstDlaInfo);
            g_IpuIntfObject = new WNC_ADAS(gstDlaInfo);
            //[WNC]

            memcpy(&attr, param, sizeof(ADAS_ATTR_t));

            if (attr.stSrcChnPort.eModId == E_MI_MODULE_ID_MAX)
                return -1;

            *pp_adas_ctx = ADAS_Create(bIsFrontAdas, &attr);

            if (*pp_adas_ctx)
            {
                // ADAS_SetFeature(*pp_adas_ctx, attr.feature.ldws, attr.feature.fcws, attr.feature.sag,
                // attr.feature.bsd,
                //                attr.feature.bcws);
                // ADAS_SetChannelPort(*pp_adas_ctx, &attr.stSrcChnPort);
                // s32ret = ADAS_Run(*pp_adas_ctx);
                s32ret = ADAS_Run(*pp_adas_ctx, g_IpuIntfObject);
                if (s32ret < 0)
                {
                    if (g_IpuIntfObject)
                    {
                        delete g_IpuIntfObject;
                        g_IpuIntfObject = NULL;
                    }
#ifdef SPDLOG_USE_SYSLOG
                    spdlog::drop_all();
#else
                    //[WNC fix 2320/10/31]
                    spdlog::drop("ADAS");
                    spdlog::drop("ADAS_ConfigReader");
                    spdlog::drop("YOLO-ADAS");
                    spdlog::drop("LaneLineCalib");
                    spdlog::drop("OpticalFlow");
                    spdlog::drop("LaneFinder");
                    spdlog::drop("MAIN: IPUTask");
                    spdlog::drop("FCW");
                    spdlog::drop("JSON");
                    spdlog::drop("GEOTAB");
                    spdlog::drop("YOLO-ADAS-PostProc");
                    spdlog::drop("LDW");
                    spdlog::drop("HumanTracker");
                    spdlog::drop("RiderTracker");
                    spdlog::drop("VehicleTracker");
                    spdlog::drop("ADAS_DEBUG");
#endif
                    // spdlog::drop("");
                    //[WNC fix 2320/10/31]

                    ADAS_Destory(pp_adas_ctx);
                }
            }
        }
        break;

    case CMD_ADAS_REAR_DEINIT:
        pp_adas_ctx = &r_adas_ctx;
    case CMD_ADAS_DEINIT:
        if (*pp_adas_ctx)
        {
            syslog(LOG_ALERT, "ADAS: SPD Going to Drop all\n"); // goto err_exit;
            syslog(LOG_NOTICE, "[%s %d] ADAS close\n", __func__, __LINE__);

            ADAS_Stop(*pp_adas_ctx);
            if (g_IpuIntfObject)
            {
                delete g_IpuIntfObject;
                g_IpuIntfObject = NULL;
            }
#ifdef SPDLOG_USE_SYSLOG
            spdlog::drop_all();
#else
            //[WNC fix 2320/10/31]
            spdlog::drop("ADAS");
            spdlog::drop("ADAS_ConfigReader");
            spdlog::drop("YOLO-ADAS");
            spdlog::drop("LaneLineCalib");
            spdlog::drop("OpticalFlow");
            spdlog::drop("LaneFinder");
            spdlog::drop("MAIN: IPUTask");
            spdlog::drop("FCW");
            spdlog::drop("GEOTAB");
            spdlog::drop("JSON");
            spdlog::drop("YOLO-ADAS-PostProc");
            spdlog::drop("LDW");
            spdlog::drop("HumanTracker");
            spdlog::drop("RiderTracker");
            spdlog::drop("VehicleTracker");
            spdlog::drop("ADAS_DEBUG");
// spdlog::drop("");
//[WNC fix 2320/10/31]
#endif
            ADAS_Destory(pp_adas_ctx);
        }
        break;

    default:
        break;
    }

    return 0;
}
#endif
