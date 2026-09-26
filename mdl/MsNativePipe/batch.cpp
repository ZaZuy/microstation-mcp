/*===========================================================================
 * batch.cpp  -  Batch element creation implementation
 *
 * Muc dich: Implement BatchCreate() - tao nhieu element trong mot lan goi,
 *           ho tro wrap trong undo group de co the undo/redo toan bo batch.
 *
 * Logic:
 *   1. Parse JSON array cac element definitions
 *   2. Neu useUndoGroup: goi mdlUndo_startGroup()
 *   3. Vong lap: goi ham Create* tuong ung theo "type"
 *   4. Neu useUndoGroup: goi mdlUndo_endGroup()
 *   5. Tra ve JSON array ket qua
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/

#include "batch.h"
#include "json_lite.h"
#include "geometry.h"

extern "C" {
#include <mdl.h>
#include <msundo.h>
}

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// -----------------------------------------------------------------------
// Ham tao mot element theo dinh nghia JSON
//
// @param typeName  Ten kieu element ("line", "circle", ...)
// @param params    JsonValue chua tham so
// @param errMsg    [out] Thong bao loi neu that bai
// @return          Element ID string, hoac "" neu loi
// -----------------------------------------------------------------------
static std::string CreateOneElement(const std::string& typeName,
                                    const JsonValue& params,
                                    std::string& errMsg)
{
    errMsg = "";

    // ---- line ----
    if (typeName == "line")
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

        std::string id = CreateLine(x1, y1, z1, x2, y2, z2,
                                    level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateLine that bai";
        return id;
    }

    // ---- linestring ----
    if (typeName == "linestring")
    {
        const JsonValue& pts = params["points"];
        if (!pts.isArray() || pts.size() < 2)
        {
            errMsg = "points phai co it nhat 2 phan tu";
            return "";
        }
        int nPts = (int)pts.size();
        std::vector<DPoint3d> ptsVec((size_t)nPts);
        std::vector<double> xs(nPts), ys(nPts), zs(nPts);
        for (int i = 0; i < nPts; ++i)
        {
            const JsonValue& p = pts[i];
            xs[i] = p.isArray() && p.size() >= 1 ? p[0].getNumber() : 0.0;
            ys[i] = p.isArray() && p.size() >= 2 ? p[1].getNumber() : 0.0;
            zs[i] = p.isArray() && p.size() >= 3 ? p[2].getNumber() : 0.0;
        }
        int level  = JsonGetInt(params, "level",  0);
        int color  = JsonGetInt(params, "color",  -1);
        int weight = JsonGetInt(params, "weight", -1);
        int style  = JsonGetInt(params, "style",  0);

        std::string id = CreateLineString(&xs[0], &ys[0], &zs[0], nPts,
                                          level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateLineString that bai";
        return id;
    }

    // ---- shape ----
    if (typeName == "shape")
    {
        const JsonValue& pts = params["points"];
        if (!pts.isArray() || pts.size() < 3)
        {
            errMsg = "shape can it nhat 3 diem";
            return "";
        }
        int nPts = (int)pts.size();
        std::vector<double> xs(nPts), ys(nPts), zs(nPts);
        for (int i = 0; i < nPts; ++i)
        {
            const JsonValue& p = pts[i];
            xs[i] = p.isArray() && p.size() >= 1 ? p[0].getNumber() : 0.0;
            ys[i] = p.isArray() && p.size() >= 2 ? p[1].getNumber() : 0.0;
            zs[i] = p.isArray() && p.size() >= 3 ? p[2].getNumber() : 0.0;
        }
        bool filled    = JsonGetBool(params, "filled", false);
        int  fillColor = JsonGetInt(params, "fill_color", 0);
        int  level     = JsonGetInt(params, "level",  0);
        int  color     = JsonGetInt(params, "color",  -1);
        int  weight    = JsonGetInt(params, "weight", -1);
        int  style     = JsonGetInt(params, "style",  0);

        std::string id = CreateShape(&xs[0], &ys[0], &zs[0], nPts,
                                     filled, fillColor,
                                     level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateShape that bai";
        return id;
    }

    // ---- circle ----
    if (typeName == "circle")
    {
        double cx     = JsonGetDouble(params, "cx");
        double cy     = JsonGetDouble(params, "cy");
        double cz     = JsonGetDouble(params, "cz");
        double radius = JsonGetDouble(params, "radius");
        int level     = JsonGetInt(params, "level",  0);
        int color     = JsonGetInt(params, "color",  -1);
        int weight    = JsonGetInt(params, "weight", -1);
        int style     = JsonGetInt(params, "style",  0);

        if (radius <= 0.0) { errMsg = "radius phai > 0"; return ""; }

        std::string id = CreateCircle(cx, cy, cz, radius,
                                      level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateCircle that bai";
        return id;
    }

    // ---- arc ----
    if (typeName == "arc")
    {
        double cx         = JsonGetDouble(params, "cx");
        double cy         = JsonGetDouble(params, "cy");
        double cz         = JsonGetDouble(params, "cz");
        double radius     = JsonGetDouble(params, "radius");
        double startAngle = JsonGetDouble(params, "start_angle");
        double sweepAngle = JsonGetDouble(params, "sweep_angle");
        int level         = JsonGetInt(params, "level",  0);
        int color         = JsonGetInt(params, "color",  -1);
        int weight        = JsonGetInt(params, "weight", -1);
        int style         = JsonGetInt(params, "style",  0);

        if (radius <= 0.0) { errMsg = "radius phai > 0"; return ""; }

        std::string id = CreateArc(cx, cy, cz, radius,
                                   startAngle, sweepAngle,
                                   level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateArc that bai";
        return id;
    }

    // ---- ellipse ----
    if (typeName == "ellipse")
    {
        double cx        = JsonGetDouble(params, "cx");
        double cy        = JsonGetDouble(params, "cy");
        double cz        = JsonGetDouble(params, "cz");
        double primaryR  = JsonGetDouble(params, "primary_r");
        double secondaryR= JsonGetDouble(params, "secondary_r");
        double rotation  = JsonGetDouble(params, "rotation", 0.0);
        int level        = JsonGetInt(params, "level",  0);
        int color        = JsonGetInt(params, "color",  -1);
        int weight       = JsonGetInt(params, "weight", -1);
        int style        = JsonGetInt(params, "style",  0);

        if (primaryR <= 0.0 || secondaryR <= 0.0)
        {
            errMsg = "primary_r va secondary_r phai > 0";
            return "";
        }

        std::string id = CreateEllipse(cx, cy, cz, primaryR, secondaryR,
                                       rotation, level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateEllipse that bai";
        return id;
    }

    // ---- text ----
    if (typeName == "text")
    {
        double x        = JsonGetDouble(params, "x");
        double y        = JsonGetDouble(params, "y");
        double z        = JsonGetDouble(params, "z");
        std::string txt = JsonGetString(params, "text");
        double height   = JsonGetDouble(params, "height", 1.0);
        double rotation = JsonGetDouble(params, "rotation", 0.0);
        int level       = JsonGetInt(params, "level", 0);
        int color       = JsonGetInt(params, "color", -1);

        if (txt.empty()) { errMsg = "text khong duoc rong"; return ""; }
        if (height <= 0.0) { errMsg = "height phai > 0"; return ""; }

        std::string id = CreateText(x, y, z, txt.c_str(),
                                    height, rotation, level, color, true);
        if (id.empty()) errMsg = "CreateText that bai";
        return id;
    }

    // ---- point ----
    if (typeName == "point")
    {
        double x   = JsonGetDouble(params, "x");
        double y   = JsonGetDouble(params, "y");
        double z   = JsonGetDouble(params, "z");
        int level  = JsonGetInt(params, "level",  0);
        int color  = JsonGetInt(params, "color",  -1);
        int weight = JsonGetInt(params, "weight", -1);

        std::string id = CreatePoint(x, y, z, level, color, weight, true);
        if (id.empty()) errMsg = "CreatePoint that bai";
        return id;
    }

    // ---- cell ----
    if (typeName == "cell")
    {
        double x         = JsonGetDouble(params, "x");
        double y         = JsonGetDouble(params, "y");
        double z         = JsonGetDouble(params, "z");
        std::string name = JsonGetString(params, "name", "CELL1");
        double scale     = JsonGetDouble(params, "scale", 1.0);
        double rotation  = JsonGetDouble(params, "rotation", 0.0);
        int level        = JsonGetInt(params, "level", 0);
        int color        = JsonGetInt(params, "color", -1);
        int weight       = JsonGetInt(params, "weight", -1);
        int style        = JsonGetInt(params, "style", 0);

        std::string id = CreateCell(x, y, z, name.c_str(), scale, rotation,
                                    level, color, weight, style, true);
        if (id.empty()) errMsg = "CreateCell that bai";
        return id;
    }

    // Kieu khong duoc ho tro
    errMsg = "Kieu element khong duoc ho tro: " + typeName;
    return "";
}

// -----------------------------------------------------------------------
// BatchCreate - xu ly lenh batch_create (High-Performance Engine)
// -----------------------------------------------------------------------
std::string BatchCreate(const std::string& elementsJson, bool useUndoGroup)
{
    // --- Parse JSON array ---
    JsonValue root;
    try
    {
        root = JsonParser::parse(elementsJson);
    }
    catch (const std::exception& ex)
    {
        std::string errMsg = "JSON parse loi: ";
        errMsg += ex.what();
        std::string errArr = "[{\"index\":0,\"success\":false,\"element_id\":\"\",\"message\":";
        errArr += JsonBuilder::escapeString(errMsg);
        errArr += "}]";
        return errArr;
    }

    if (!root.isArray() || root.size() == 0)
        return "[]";

    size_t totalCount = root.size();

    // --- Bat dau undo group neu can (gom toan bo batch vao 1 lan Ctrl+Z) ---
    if (useUndoGroup)
        mdlUndo_startGroup();

    // --- Pre-allocate buffer de toi uu toc do chuoi JSON ---
    std::string result;
    result.reserve(totalCount * 64);
    result = "[";

    for (size_t i = 0; i < totalCount; ++i)
    {
        if (i > 0) result += ",";

        const JsonValue& elem = root[(int)i];

        std::string typeName = JsonGetString(elem, "type");
        const JsonValue& params = elem["params"];

        result += "{\"index\":";
        char buf[32];
        std::sprintf(buf, "%zu", i);
        result += buf;

        if (typeName.empty())
        {
            result += ",\"success\":false,\"element_id\":\"\","
                      "\"message\":\"Thieu truong 'type'\"}";
            continue;
        }

        std::string errMsg;
        // deferRedraw = true de khong redraw man hinh sau tung element
        std::string elemId = CreateOneElement(typeName, params, errMsg);

        if (elemId.empty())
        {
            result += ",\"success\":false,\"element_id\":\"\",\"message\":";
            result += JsonBuilder::escapeString(errMsg.empty() ?
                      "Khong ro loi" : errMsg);
            result += "}";
        }
        else
        {
            result += ",\"success\":true,\"element_id\":";
            result += JsonBuilder::escapeString(elemId);
            result += ",\"message\":\"OK\"}";
        }
    }

    result += "]";

    // --- Ket thuc undo group ---
    if (useUndoGroup)
        mdlUndo_endGroup();

    // --- Redraw 1 lan duy nhat cho toan bo view sau khi ghi xong DGN cache ---
    TriggerModelRedraw();

    return result;
}
