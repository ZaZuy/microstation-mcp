/*===========================================================================
 * handlers.cpp  -  Dispatcher va toan bo command handlers
 *
 * Muc dich: Implement HandleRequest() va tat ca handler tuong ung voi
 *           cac lenh duoc ho tro boi MsNativePipe MDL server.
 *
 * Cac lenh duoc ho tro:
 *   ping, draw_line, draw_linestring, draw_shape, draw_circle, draw_arc,
 *   draw_ellipse, draw_point, place_text, move_element, copy_element,
 *   rotate_element, scale_element, delete_element, change_symbology,
 *   get_drawing_info, get_active_settings, set_active_level,
 *   set_active_color, set_active_weight, scan_elements, get_element_details,
 *   batch_create, begin_transaction, end_transaction, get_model_snapshot
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/

#include "handlers.h"
#include "json_lite.h"
#include "geometry.h"
#include "batch.h"

// MDL SDK headers
extern "C" {
#include <mdl.h>
#include <mselems.h>
#include <msmodel.h>
#include <mssettng.h>
#include <tcb.h>
#include <msundo.h>
#include <dlogman.fdf>
}

#include <cstdio>
#include <cstring>
#include <cmath>
#include <string>

// -----------------------------------------------------------------------
// Ham tien ich
// -----------------------------------------------------------------------

// Lay active level number tu TCB (Task Control Block)
static int GetActiveLevel()
{
    return (int)tcb->level; // truong 'level' trong TCB
}

// Lay active color tu TCB
static int GetActiveColor()
{
    return (int)tcb->color;
}

// Lay active weight tu TCB
static int GetActiveWeight()
{
    return (int)tcb->weight;
}

// Lay active line style tu TCB
static int GetActiveStyle()
{
    return (int)tcb->style;
}

// -----------------------------------------------------------------------
// Handler: ping
// Kiem tra ket noi cua server
// -----------------------------------------------------------------------
static std::string H_Ping(long long id, const JsonValue& /*params*/)
{
    return MakeSuccessResponse(id, "{\"pong\":true}");
}

// -----------------------------------------------------------------------
// Handler: draw_line
// Ve doan thang tu (x1,y1,z1) den (x2,y2,z2)
// -----------------------------------------------------------------------
static std::string H_DrawLine(long long id, const JsonValue& params)
{
    double x1 = JsonGetDouble(params, "x1");
    double y1 = JsonGetDouble(params, "y1");
    double z1 = JsonGetDouble(params, "z1");
    double x2 = JsonGetDouble(params, "x2");
    double y2 = JsonGetDouble(params, "y2");
    double z2 = JsonGetDouble(params, "z2");
    int level  = JsonGetInt(params, "level",  0);
    int color  = JsonGetInt(params, "color",  -1);
    int weight = JsonGetInt(params, "weight", -1);
    int style  = JsonGetInt(params, "style",  0);

    std::string elemId = CreateLine(x1, y1, z1, x2, y2, z2,
                                    level, color, weight, style);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao line element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_linestring
// Ve polyline tu mang diem [[x,y,z],...]
// -----------------------------------------------------------------------
static std::string H_DrawLinestring(long long id, const JsonValue& params)
{
    const JsonValue& pts = params["points"];
    if (!pts.isArray() || pts.size() < 2)
        return MakeErrorResponse(id, "params.points phai la array co it nhat 2 phan tu");

    int nPts = (int)pts.size();
    std::vector<double> xs(nPts), ys(nPts), zs(nPts);

    for (int i = 0; i < nPts; ++i)
    {
        const JsonValue& pt = pts[i];
        if (!pt.isArray() || pt.size() < 2)
            return MakeErrorResponse(id, "Moi phan tu points phai la array [x,y] hoac [x,y,z]");
        xs[i] = pt[0].getNumber();
        ys[i] = pt[1].getNumber();
        zs[i] = (pt.size() >= 3) ? pt[2].getNumber() : 0.0;
    }

    int level  = JsonGetInt(params, "level",  0);
    int color  = JsonGetInt(params, "color",  -1);
    int weight = JsonGetInt(params, "weight", -1);
    int style  = JsonGetInt(params, "style",  0);

    std::string elemId = CreateLineString(
        &xs[0], &ys[0], &zs[0], nPts, level, color, weight, style);

    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao linestring element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_shape
// Ve polygon (co the to mau) tu mang diem
// -----------------------------------------------------------------------
static std::string H_DrawShape(long long id, const JsonValue& params)
{
    const JsonValue& pts = params["points"];
    if (!pts.isArray() || pts.size() < 3)
        return MakeErrorResponse(id, "params.points phai co it nhat 3 diem");

    int nPts = (int)pts.size();
    std::vector<double> xs(nPts), ys(nPts), zs(nPts);

    for (int i = 0; i < nPts; ++i)
    {
        const JsonValue& pt = pts[i];
        if (!pt.isArray() || pt.size() < 2)
            return MakeErrorResponse(id, "Moi phan tu points phai la [x,y] hoac [x,y,z]");
        xs[i] = pt[0].getNumber();
        ys[i] = pt[1].getNumber();
        zs[i] = (pt.size() >= 3) ? pt[2].getNumber() : 0.0;
    }

    bool filled    = JsonGetBool(params, "filled", false);
    int  fillColor = JsonGetInt(params, "fill_color", 0);
    int  level     = JsonGetInt(params, "level",  0);
    int  color     = JsonGetInt(params, "color",  -1);
    int  weight    = JsonGetInt(params, "weight", -1);
    int  style     = JsonGetInt(params, "style",  0);

    std::string elemId = CreateShape(
        &xs[0], &ys[0], &zs[0], nPts,
        filled, fillColor, level, color, weight, style);

    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao shape element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_circle
// Ve duong tron
// -----------------------------------------------------------------------
static std::string H_DrawCircle(long long id, const JsonValue& params)
{
    double cx     = JsonGetDouble(params, "cx");
    double cy     = JsonGetDouble(params, "cy");
    double cz     = JsonGetDouble(params, "cz");
    double radius = JsonGetDouble(params, "radius");
    int level     = JsonGetInt(params, "level",  0);
    int color     = JsonGetInt(params, "color",  -1);
    int weight    = JsonGetInt(params, "weight", -1);
    int style     = JsonGetInt(params, "style",  0);

    if (radius <= 0.0)
        return MakeErrorResponse(id, "radius phai > 0");

    std::string elemId = CreateCircle(cx, cy, cz, radius, level, color, weight, style);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao circle element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_arc
// Ve cung tron
// -----------------------------------------------------------------------
static std::string H_DrawArc(long long id, const JsonValue& params)
{
    double cx          = JsonGetDouble(params, "cx");
    double cy          = JsonGetDouble(params, "cy");
    double cz          = JsonGetDouble(params, "cz");
    double radius      = JsonGetDouble(params, "radius");
    double startAngle  = JsonGetDouble(params, "start_angle"); // radian
    double sweepAngle  = JsonGetDouble(params, "sweep_angle"); // radian
    int level          = JsonGetInt(params, "level",  0);
    int color          = JsonGetInt(params, "color",  -1);
    int weight         = JsonGetInt(params, "weight", -1);
    int style          = JsonGetInt(params, "style",  0);

    if (radius <= 0.0)
        return MakeErrorResponse(id, "radius phai > 0");

    std::string elemId = CreateArc(cx, cy, cz, radius,
                                   startAngle, sweepAngle,
                                   level, color, weight, style);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao arc element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_ellipse
// Ve hinh elip
// -----------------------------------------------------------------------
static std::string H_DrawEllipse(long long id, const JsonValue& params)
{
    double cx        = JsonGetDouble(params, "cx");
    double cy        = JsonGetDouble(params, "cy");
    double cz        = JsonGetDouble(params, "cz");
    double primaryR  = JsonGetDouble(params, "primary_r");
    double secondaryR= JsonGetDouble(params, "secondary_r");
    double rotation  = JsonGetDouble(params, "rotation", 0.0); // radian
    int level        = JsonGetInt(params, "level",  0);
    int color        = JsonGetInt(params, "color",  -1);
    int weight       = JsonGetInt(params, "weight", -1);
    int style        = JsonGetInt(params, "style",  0);

    if (primaryR <= 0.0 || secondaryR <= 0.0)
        return MakeErrorResponse(id, "primary_r va secondary_r phai > 0");

    std::string elemId = CreateEllipse(cx, cy, cz, primaryR, secondaryR,
                                       rotation, level, color, weight, style);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao ellipse element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: draw_point
// Ve diem
// -----------------------------------------------------------------------
static std::string H_DrawPoint(long long id, const JsonValue& params)
{
    double x   = JsonGetDouble(params, "x");
    double y   = JsonGetDouble(params, "y");
    double z   = JsonGetDouble(params, "z");
    int level  = JsonGetInt(params, "level",  0);
    int color  = JsonGetInt(params, "color",  -1);
    int weight = JsonGetInt(params, "weight", -1);

    std::string elemId = CreatePoint(x, y, z, level, color, weight);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao point element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: place_text
// Dat chu vao ban ve
// -----------------------------------------------------------------------
static std::string H_PlaceText(long long id, const JsonValue& params)
{
    double x        = JsonGetDouble(params, "x");
    double y        = JsonGetDouble(params, "y");
    double z        = JsonGetDouble(params, "z");
    std::string txt = JsonGetString(params, "text");
    double height   = JsonGetDouble(params, "height", 1.0);
    double rotation = JsonGetDouble(params, "rotation", 0.0);
    int level       = JsonGetInt(params, "level", 0);
    int color       = JsonGetInt(params, "color", -1);

    if (txt.empty())
        return MakeErrorResponse(id, "params.text khong duoc rong");
    if (height <= 0.0)
        return MakeErrorResponse(id, "height phai > 0");

    std::string elemId = CreateText(x, y, z, txt.c_str(),
                                    height, rotation, level, color);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao text element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: place_cell
// Dat cell tu cell library hoac tao cell container
// -----------------------------------------------------------------------
static std::string H_PlaceCell(long long id, const JsonValue& params)
{
    double x         = JsonGetDouble(params, "x");
    double y         = JsonGetDouble(params, "y");
    double z         = JsonGetDouble(params, "z");
    std::string name = JsonGetString(params, "name");
    if (name.empty()) name = JsonGetString(params, "cell_name", "CELL1");
    double scale     = JsonGetDouble(params, "scale", 1.0);
    double rotation  = JsonGetDouble(params, "rotation", 0.0);
    int level        = JsonGetInt(params, "level", 0);
    int color        = JsonGetInt(params, "color", -1);
    int weight       = JsonGetInt(params, "weight", -1);
    int style        = JsonGetInt(params, "style", 0);

    std::string elemId = CreateCell(x, y, z, name.c_str(), scale, rotation,
                                    level, color, weight, style, false);
    if (elemId.empty())
        return MakeErrorResponse(id, "Khong the tao cell element");

    std::string data = "{\"element_id\":" +
                       JsonBuilder::escapeString(elemId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: move_element
// Di chuyen element theo vector (dx, dy, dz)
// -----------------------------------------------------------------------
static std::string H_MoveElement(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");
    double dx = JsonGetDouble(params, "dx");
    double dy = JsonGetDouble(params, "dy");
    double dz = JsonGetDouble(params, "dz");

    if (!MoveElement(elemId, dx, dy, dz))
        return MakeErrorResponse(id, "Khong the move element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: copy_element
// Sao chep element va di chuyen ban sao
// -----------------------------------------------------------------------
static std::string H_CopyElement(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");
    double dx = JsonGetDouble(params, "dx");
    double dy = JsonGetDouble(params, "dy");
    double dz = JsonGetDouble(params, "dz");

    std::string newId;
    if (!CopyElement(elemId, dx, dy, dz, newId))
        return MakeErrorResponse(id, "Khong the copy element ID=" +
                                 std::to_string(elemId));

    std::string data = "{\"new_element_id\":" +
                       JsonBuilder::escapeString(newId) + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: rotate_element
// Xoay element quanh mot diem
// -----------------------------------------------------------------------
static std::string H_RotateElement(long long id, const JsonValue& params)
{
    long long elemId   = JsonGetInt64(params, "element_id");
    double cx          = JsonGetDouble(params, "cx");
    double cy          = JsonGetDouble(params, "cy");
    double cz          = JsonGetDouble(params, "cz");
    double angleDeg = JsonGetDouble(params, "angle_degrees", 0.0);
    if (angleDeg == 0.0) angleDeg = JsonGetDouble(params, "angle_deg", 0.0);
    if (angleDeg == 0.0) angleDeg = JsonGetDouble(params, "angle", 0.0);

    if (!RotateElement(elemId, cx, cy, cz, angleDeg))
        return MakeErrorResponse(id, "Khong the rotate element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: scale_element
// Phong to/thu nho element
// -----------------------------------------------------------------------
static std::string H_ScaleElement(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");
    double cx  = JsonGetDouble(params, "cx");
    double cy  = JsonGetDouble(params, "cy");
    double cz  = JsonGetDouble(params, "cz");
    double sx  = JsonGetDouble(params, "scale_x", 0.0);
    if (sx == 0.0) sx = JsonGetDouble(params, "sx", 1.0);
    double sy  = JsonGetDouble(params, "scale_y", 0.0);
    if (sy == 0.0) sy = JsonGetDouble(params, "sy", 1.0);
    double sz  = JsonGetDouble(params, "scale_z", 0.0);
    if (sz == 0.0) sz = JsonGetDouble(params, "sz", 1.0);

    if (sx == 0.0 || sy == 0.0 || sz == 0.0)
        return MakeErrorResponse(id, "He so scale khong duoc bang 0");

    if (!ScaleElement(elemId, cx, cy, cz, sx, sy, sz))
        return MakeErrorResponse(id, "Khong the scale element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: delete_element
// Xoa element khoi model
// -----------------------------------------------------------------------
static std::string H_DeleteElement(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");

    if (!DeleteElement(elemId))
        return MakeErrorResponse(id, "Khong the xoa element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: change_symbology
// Thay doi thuoc tinh hien thi (level, color, weight, style)
// -----------------------------------------------------------------------
static std::string H_ChangeSymbology(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");
    int level  = JsonGetInt(params, "level",  -1);
    int color  = JsonGetInt(params, "color",  -1);
    int weight = JsonGetInt(params, "weight", -1);
    int style  = JsonGetInt(params, "style",  -1);

    if (!ChangeSymbology(elemId, level, color, weight, style))
        return MakeErrorResponse(id, "Khong the thay doi symbology element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: get_drawing_info
// Tra ve thong tin ban ve dang mo
// -----------------------------------------------------------------------
static std::string H_GetDrawingInfo(long long id, const JsonValue& /*params*/)
{
    // Lay ten file thiet ke
    char fileName[512] = "";
    mdlFile_getDesignFilename(fileName, sizeof(fileName) - 1, NULL);

    // Lay ten model dang active
    char modelName[256] = "";
    ModelRefP activeModel = mdlModelRef_getActive();
    if (activeModel)
        mdlModelRef_getActiveName(activeModel, modelName, sizeof(modelName) - 1);

    // Lay thong so UOR (Units Of Resolution)
    double uorPerMaster = 1.0;
    double masterPerSub = 1.0;
    if (activeModel)
    {
        DgnModelP dgnModel = mdlModelRef_getDgnModel(activeModel);
        if (dgnModel)
        {
            // Lay thong tin don vi tu model
            // API V8i: mdlModel_getUORPerMaster
            mdlModel_getUORPerMaster(&uorPerMaster, dgnModel);
        }
    }

    // Xay dung data JSON
    std::string data = "{";
    data += "\"file_path\":";
    data += JsonBuilder::escapeString(fileName);
    data += ",\"model_name\":";
    data += JsonBuilder::escapeString(modelName);
    data += ",\"uor_per_master\":";
    data += JsonBuilder::numberToString(uorPerMaster);
    data += "}";

    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: get_active_settings
// Tra ve cac thiet lap hien hanh (level, color, weight, style)
// -----------------------------------------------------------------------
static std::string H_GetActiveSettings(long long id, const JsonValue& /*params*/)
{
    int activeLevel  = GetActiveLevel();
    int activeColor  = GetActiveColor();
    int activeWeight = GetActiveWeight();
    int activeStyle  = GetActiveStyle();

    // Lay ten level tu level number
    char levelName[256] = "";
    ModelRefP activeModel = mdlModelRef_getActive();
    if (activeModel)
    {
        LevelId levelId = (LevelId)activeLevel;
        mdlLevel_getName(activeModel, levelId, levelName, sizeof(levelName) - 1);
    }

    std::string data = "{";
    data += "\"level\":";
    char buf[32]; std::sprintf(buf, "%d", activeLevel);
    data += buf;
    data += ",\"level_name\":";
    data += JsonBuilder::escapeString(levelName);
    data += ",\"color\":";
    std::sprintf(buf, "%d", activeColor);
    data += buf;
    data += ",\"weight\":";
    std::sprintf(buf, "%d", activeWeight);
    data += buf;
    data += ",\"style\":";
    std::sprintf(buf, "%d", activeStyle);
    data += buf;
    data += "}";

    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: set_active_level
// Dat level hien hanh theo ten
// -----------------------------------------------------------------------
static std::string H_SetActiveLevel(long long id, const JsonValue& params)
{
    std::string levelName = JsonGetString(params, "level_name");
    if (levelName.empty())
        return MakeErrorResponse(id, "params.level_name khong duoc rong");

    ModelRefP activeModel = mdlModelRef_getActive();
    if (!activeModel)
        return MakeErrorResponse(id, "Khong co active model");

    // Tim level ID tu ten
    LevelId levelId = INVALID_LEVELID;
    int rc = mdlLevel_getIdFromName(&levelId, activeModel, NULL,
                                    levelName.c_str());
    if (rc != SUCCESS || levelId == INVALID_LEVELID)
    {
        return MakeErrorResponse(id, "Khong tim thay level: " + levelName);
    }

    // Set active level
    tcb->level = (short)levelId;
    // Thong bao MicroStation cap nhat
    mdlOutput_reDraw(NULL, REDRAW_ALL);

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: set_active_color
// Dat mau hien hanh
// -----------------------------------------------------------------------
static std::string H_SetActiveColor(long long id, const JsonValue& params)
{
    int color = JsonGetInt(params, "color", -1);
    if (color < 0 || color > 255)
        return MakeErrorResponse(id, "color phai tu 0 den 255");

    tcb->color = (UShort)color;

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: set_active_weight
// Dat do day net hien hanh
// -----------------------------------------------------------------------
static std::string H_SetActiveWeight(long long id, const JsonValue& params)
{
    int weight = JsonGetInt(params, "weight", -1);
    if (weight < 0 || weight > 31)
        return MakeErrorResponse(id, "weight phai tu 0 den 31");

    tcb->weight = (UShort)weight;

    return MakeSuccessResponse(id, "{}");
}

// -----------------------------------------------------------------------
// Handler: scan_elements
// Quet cac element trong active model
// -----------------------------------------------------------------------
static std::string H_ScanElements(long long id, const JsonValue& params)
{
    std::string typeFilter = JsonGetString(params, "type_filter", "");
    int maxCount           = JsonGetInt(params, "max_count", 1000);

    if (maxCount <= 0) maxCount = 1000;
    if (maxCount > 10000) maxCount = 10000;

    std::string jsonArray;
    if (!ScanElements(typeFilter.c_str(), maxCount, jsonArray))
        return MakeErrorResponse(id, "Loi khi quet elements");

    std::string data = "{\"elements\":" + jsonArray + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: get_element_details
// Lay thong tin chi tiet mot element
// -----------------------------------------------------------------------
static std::string H_GetElementDetails(long long id, const JsonValue& params)
{
    long long elemId = JsonGetInt64(params, "element_id");

    std::string jsonDetail;
    if (!GetElementDetails(elemId, jsonDetail))
        return MakeErrorResponse(id, "Khong tim thay element ID=" +
                                 std::to_string(elemId));

    return MakeSuccessResponse(id, jsonDetail);
}

// -----------------------------------------------------------------------
// Handler: batch_create
// Tao nhieu element cung luc
// -----------------------------------------------------------------------
static std::string H_BatchCreate(long long id, const JsonValue& params)
{
    const JsonValue& elemsVal = params["elements"].isArray() ? params["elements"] : params["commands"];
    if (!elemsVal.isArray())
        return MakeErrorResponse(id, "params.elements hoac params.commands phai la JSON array");

    bool useUndoGroup = JsonGetBool(params, "undo_group", true);
    if (!JsonHasKey(params, "undo_group") && JsonHasKey(params, "use_undo_group"))
        useUndoGroup = JsonGetBool(params, "use_undo_group", true);

    // Chuyen lai sang JSON string de truyen vao BatchCreate
    std::string elementsJson = JsonBuilder::stringify(elemsVal);

    std::string result = BatchCreate(elementsJson, useUndoGroup);
    std::string data   = "{\"results\":" + result + "}";
    return MakeSuccessResponse(id, data);
}

// -----------------------------------------------------------------------
// Handler: begin_transaction
// Bat dau undo group
// -----------------------------------------------------------------------
static std::string H_BeginTransaction(long long id, const JsonValue& /*params*/)
{
    mdlUndo_startGroup();
    return MakeSuccessResponse(id, "{}", "Undo group bat dau");
}

// -----------------------------------------------------------------------
// Handler: end_transaction
// Ket thuc undo group
// -----------------------------------------------------------------------
static std::string H_EndTransaction(long long id, const JsonValue& /*params*/)
{
    mdlUndo_endGroup();
    return MakeSuccessResponse(id, "{}", "Undo group ket thuc");
}

// -----------------------------------------------------------------------
// Handler: get_model_snapshot
// Lay snapshot toan bo active model
// -----------------------------------------------------------------------
static std::string H_GetModelSnapshot(long long id, const JsonValue& /*params*/)
{
    std::string snapshotJson;
    if (!GetModelSnapshot(snapshotJson))
        return MakeErrorResponse(id, "Loi khi lay model snapshot");

    return MakeSuccessResponse(id, snapshotJson);
}

// -----------------------------------------------------------------------
// HandleRequest - Dispatcher chinh
//
// Phan tich JSON request, goi handler tuong ung va tra ve JSON response.
// -----------------------------------------------------------------------
std::string HandleRequest(const std::string& jsonRequest)
{
    long long reqId = 0;

    // --- Parse JSON ---
    JsonValue root;
    try
    {
        root = JsonParser::parse(jsonRequest);
    }
    catch (const std::exception& ex)
    {
        // JSON parse loi - khong lay duoc id
        std::string msg = "JSON parse loi: ";
        msg += ex.what();
        return MakeErrorResponse(0, msg);
    }

    // Lay request ID
    reqId = JsonGetInt64(root, "id", 0);

    // Lay ten lenh (ho tro ca "command" va "cmd")
    std::string command = JsonGetString(root, "command");
    if (command.empty())
        command = JsonGetString(root, "cmd");
    if (command.empty())
        return MakeErrorResponse(reqId, "Thieu truong 'command' hoac 'cmd'");

    // Lay params (ho tro ca "params" va "arguments", mac dinh rong)
    const JsonValue& paramsVal = root["params"];
    const JsonValue& params = paramsVal.isNull() ? root["arguments"] : paramsVal;

    // --- Dispatch den handler tuong ung ---

    if (command == "ping")
        return H_Ping(reqId, params);

    if (command == "draw_line")
        return H_DrawLine(reqId, params);

    if (command == "draw_linestring")
        return H_DrawLinestring(reqId, params);

    if (command == "draw_shape")
        return H_DrawShape(reqId, params);

    if (command == "draw_circle")
        return H_DrawCircle(reqId, params);

    if (command == "draw_arc")
        return H_DrawArc(reqId, params);

    if (command == "draw_ellipse")
        return H_DrawEllipse(reqId, params);

    if (command == "draw_point")
        return H_DrawPoint(reqId, params);

    if (command == "place_text")
        return H_PlaceText(reqId, params);

    if (command == "place_cell")
        return H_PlaceCell(reqId, params);

    if (command == "move_element")
        return H_MoveElement(reqId, params);

    if (command == "copy_element")
        return H_CopyElement(reqId, params);

    if (command == "rotate_element")
        return H_RotateElement(reqId, params);

    if (command == "scale_element")
        return H_ScaleElement(reqId, params);

    if (command == "delete_element")
        return H_DeleteElement(reqId, params);

    if (command == "change_symbology")
        return H_ChangeSymbology(reqId, params);

    if (command == "get_drawing_info")
        return H_GetDrawingInfo(reqId, params);

    if (command == "get_active_settings")
        return H_GetActiveSettings(reqId, params);

    if (command == "set_active_level")
        return H_SetActiveLevel(reqId, params);

    if (command == "set_active_color")
        return H_SetActiveColor(reqId, params);

    if (command == "set_active_weight")
        return H_SetActiveWeight(reqId, params);

    if (command == "scan_elements")
        return H_ScanElements(reqId, params);

    if (command == "get_element_details")
        return H_GetElementDetails(reqId, params);

    if (command == "batch_create")
        return H_BatchCreate(reqId, params);

    if (command == "begin_transaction")
        return H_BeginTransaction(reqId, params);

    if (command == "end_transaction")
        return H_EndTransaction(reqId, params);

    if (command == "get_model_snapshot")
        return H_GetModelSnapshot(reqId, params);

    // Lenh khong nhan biet
    return MakeErrorResponse(reqId, "Lenh khong duoc ho tro: " + command);
}
