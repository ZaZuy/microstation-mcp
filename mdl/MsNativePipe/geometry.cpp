/*===========================================================================
 * geometry.cpp  -  MDL geometry creation & modification implementation
 *
 * Muc dich: Implement cac ham helper tao va chinh sua element su dung
 *           MDL API cua MicroStation V8i.
 *
 * MDL API chinh su dung:
 *   - mdlLine_create        : tao doan thang
 *   - mdlLineString_create  : tao polyline
 *   - mdlShape_create       : tao polygon
 *   - mdlArc_create         : tao arc/circle
 *   - mdlEllipse_create     : tao ellipse
 *   - mdlText_create        : tao text
 *   - mdlElmdscr_add        : them element vao model
 *   - mdlElmdscr_freeAll    : giai phong MSElementDescr
 *   - mdlModelRef_scanElements : quet element
 *   - mdlElmdscr_transform  : bien doi (move/rotate/scale)
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/

#include "geometry.h"
#include "json_lite.h"

extern "C" {
#include <mdl.h>
#include <mselems.h>
#include <msmodel.h>
#include <mssettng.h>
#include <tcb.h>
#include <msundo.h>
#include <mstext.h>
#include <msscan.h>
#include <dlogman.fdf>
}

#include <cstdio>
#include <cstring>
#include <cmath>
#include <string>
#include <vector>

// Pi hang so
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// -----------------------------------------------------------------------
// Ham tien ich noi bo
// -----------------------------------------------------------------------

/**
 * Chuyen file position thanh chuoi string.
 */
std::string FileposToString(UInt32 filePos)
{
    char buf[32];
    std::sprintf(buf, "%lu", (unsigned long)filePos);
    return std::string(buf);
}

/**
 * Chuyen chuoi string sang file position.
 * Tra ve 0xFFFFFFFF (INVALID_FILEPOS) neu khong hop le.
 */
UInt32 StringToFilepos(const std::string& s)
{
    if (s.empty()) return 0xFFFFFFFFu;
    char* end = NULL;
    unsigned long val = std::strtoul(s.c_str(), &end, 10);
    if (!end || *end != '\0') return 0xFFFFFFFFu;
    return (UInt32)val;
}

/**
 * Tra ve ten kieu element dang string.
 */
const char* ElementTypeName(int elemType)
{
    switch (elemType)
    {
    case LINE_ELM:        return "line";
    case LINE_STRING_ELM: return "linestring";
    case SHAPE_ELM:       return "shape";
    case ELLIPSE_ELM:     return "ellipse";  // arc va circle cung la ELLIPSE_ELM
    case ARC_ELM:         return "arc";
    case TEXT_ELM:        return "text";
    case TEXT_NODE_ELM:   return "text_node";
    case POINT_STRING_ELM:return "point";
    case CURVE_ELM:       return "curve";
    case BSPLINE_CURVE_ELM: return "bspline_curve";
    case BSPLINE_SURFACE_ELM: return "bspline_surface";
    case CELL_HEADER_ELM: return "cell";
    case SHARED_CELL_ELM: return "shared_cell";
    case COMPLEX_CHAIN_ELM: return "complex_chain";
    case COMPLEX_SHAPE_ELM: return "complex_shape";
    default:
    {
        static char buf[32];
        std::sprintf(buf, "type_%d", elemType);
        return buf;
    }
    }
}

// -----------------------------------------------------------------------
// ApplySymbology - ap dung thuoc tinh symbology len element
// -----------------------------------------------------------------------
void ApplySymbology(MSElementDescrP elDscr, int level, int color,
                    int weight, int style)
{
    if (!elDscr || !elDscr->el) return;

    // Level: 0 hoac -1 = dung active level
    if (level > 0)
    {
        mdlElement_setLevel(elDscr->el,
                            mdlModelRef_getActive(),
                            (LevelId)level);
    }
    else
    {
        // Dung active level tu TCB
        mdlElement_setLevel(elDscr->el,
                            mdlModelRef_getActive(),
                            (LevelId)tcb->level);
    }

    // Color
    if (color >= 0 && color <= 255)
        mdlElement_setColor(elDscr->el, NULL, (UShort)color);

    // Weight (line thickness)
    if (weight >= 0 && weight <= 31)
        mdlElement_setWeight(elDscr->el, NULL, (UShort)weight);

    // Style (line style index)
    if (style >= 0)
        mdlElement_setStyle(elDscr->el, NULL, (UShort)style);
}

// -----------------------------------------------------------------------
// AddElementToModel - them element vao active model
//
// Giai phong elDscr sau khi them thanh cong.
// Tra ve element ID (file position) dang string, hoac "" neu loi.
// -----------------------------------------------------------------------
// -----------------------------------------------------------------------
// AddElementToModel - them element descriptor vao active model
// -----------------------------------------------------------------------
std::string AddElementToModel(MSElementDescrP elDscr, bool deferRedraw)
{
    if (!elDscr) return "";

    ModelRefP activeModel = mdlModelRef_getActive();
    if (!activeModel)
    {
        mdlElmdscr_freeAll(&elDscr);
        return "";
    }

    // Them element vao model
    int rc = mdlElmdscr_add(elDscr, activeModel);
    if (rc != SUCCESS)
    {
        mdlElmdscr_freeAll(&elDscr);
        return "";
    }

    // Lay 64-bit Element ID (hoac file position neu ID = 0)
    UInt32 filePos = 0;
    ElementID elemId = 0;
    if (elDscr && elDscr->el)
    {
        mdlElement_getFilePosition(&filePos, elDscr->el);
        elemId = mdlElement_getID(elDscr->el);
    }

    // Chi redraw khi khong phai batch operation
    if (!deferRedraw)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
    }

    mdlElmdscr_freeAll(&elDscr);

    if (elemId != 0)
    {
        char buf[32];
        std::sprintf(buf, "%lld", (long long)elemId);
        return std::string(buf);
    }
    return FileposToString(filePos);
}

// -----------------------------------------------------------------------
// AddPureElementToModel - them pure stack MSElement vao model (Zero Heap)
// -----------------------------------------------------------------------
std::string AddPureElementToModel(MSElement* el, bool deferRedraw)
{
    if (!el) return "";

    UInt32 filePos = mdlElement_add(el);
    ElementID elemId = mdlElement_getID(el);

    if (!deferRedraw)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
    }

    if (elemId != 0)
    {
        char buf[32];
        std::sprintf(buf, "%lld", (long long)elemId);
        return std::string(buf);
    }
    return FileposToString(filePos);
}

// -----------------------------------------------------------------------
// TriggerModelRedraw - ve lai view 1 lan sau khi hoan tat batch
// -----------------------------------------------------------------------
void TriggerModelRedraw()
{
    mdlOutput_reDraw(NULL, REDRAW_ALL);
}

// -----------------------------------------------------------------------
// CreateLine - tao doan thang (Pure MDL Stack Allocation)
// -----------------------------------------------------------------------
std::string CreateLine(double x1, double y1, double z1,
                       double x2, double y2, double z2,
                       int level, int color, int weight, int style,
                       bool deferRedraw)
{
    DPoint3d pts[2];
    pts[0].x = x1; pts[0].y = y1; pts[0].z = z1;
    pts[1].x = x2; pts[1].y = y2; pts[1].z = z2;

    MSElementDescr* elDscr = NULL;
    int rc = mdlLine_create(&elDscr, NULL, &pts[0], &pts[1]);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateLineString - tao polyline tu mang diem
// -----------------------------------------------------------------------
std::string CreateLineString(const double* xs, const double* ys, const double* zs,
                             int nPts,
                             int level, int color, int weight, int style,
                             bool deferRedraw)
{
    if (!xs || !ys || !zs || nPts < 2) return "";

    std::vector<DPoint3d> pts((size_t)nPts);
    for (int i = 0; i < nPts; ++i)
    {
        pts[i].x = xs[i];
        pts[i].y = ys[i];
        pts[i].z = zs[i];
    }

    MSElementDescr* elDscr = NULL;
    int rc = mdlLineString_create(&elDscr, NULL, &pts[0], nPts);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateShape - tao polygon (shape) tu mang diem
// -----------------------------------------------------------------------
std::string CreateShape(const double* xs, const double* ys, const double* zs,
                        int nPts, bool filled, int fillColor,
                        int level, int color, int weight, int style,
                        bool deferRedraw)
{
    if (!xs || !ys || !zs || nPts < 3) return "";

    std::vector<DPoint3d> pts((size_t)nPts);
    for (int i = 0; i < nPts; ++i)
    {
        pts[i].x = xs[i];
        pts[i].y = ys[i];
        pts[i].z = zs[i];
    }

    MSElementDescr* elDscr = NULL;
    int rc = mdlShape_create(&elDscr, NULL, filled ? TRUE : FALSE,
                              &pts[0], nPts);
    if (rc != SUCCESS || !elDscr)
        return "";

    if (filled)
    {
        if (fillColor >= 0 && fillColor <= 255 && elDscr->el)
            mdlElement_setFillColor(elDscr->el, (UShort)fillColor);
        if (elDscr->el)
            mdlElement_setFilled(elDscr->el, TRUE);
    }

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateCircle - tao duong tron
// -----------------------------------------------------------------------
std::string CreateCircle(double cx, double cy, double cz, double radius,
                         int level, int color, int weight, int style,
                         bool deferRedraw)
{
    if (radius <= 0.0) return "";

    DPoint3d center;
    center.x = cx; center.y = cy; center.z = cz;

    RotMatrix rMatrix;
    mdlRMatrix_identity(&rMatrix);

    MSElementDescr* elDscr = NULL;
    int rc = mdlArc_create(&elDscr, NULL, &center, &rMatrix,
                            radius, radius,
                            0.0, 2.0 * M_PI);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateArc - tao cung tron
// -----------------------------------------------------------------------
std::string CreateArc(double cx, double cy, double cz, double radius,
                      double startAngle, double sweepAngle,
                      int level, int color, int weight, int style,
                      bool deferRedraw)
{
    if (radius <= 0.0) return "";

    DPoint3d center;
    center.x = cx; center.y = cy; center.z = cz;

    RotMatrix rMatrix;
    mdlRMatrix_identity(&rMatrix);

    MSElementDescr* elDscr = NULL;
    int rc = mdlArc_create(&elDscr, NULL, &center, &rMatrix,
                            radius, radius,
                            startAngle, sweepAngle);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateEllipse - tao hinh elip
// -----------------------------------------------------------------------
std::string CreateEllipse(double cx, double cy, double cz,
                          double primaryR, double secondaryR, double rotation,
                          int level, int color, int weight, int style,
                          bool deferRedraw)
{
    if (primaryR <= 0.0 || secondaryR <= 0.0) return "";

    DPoint3d center;
    center.x = cx; center.y = cy; center.z = cz;

    RotMatrix rMatrix;
    mdlRMatrix_fromAxisAndRotationAngle(&rMatrix, 2, rotation);

    MSElementDescr* elDscr = NULL;
    int rc = mdlArc_create(&elDscr, NULL, &center, &rMatrix,
                            primaryR, secondaryR,
                            0.0, 2.0 * M_PI);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreatePoint - tao diem (PointString voi 1 diem)
// -----------------------------------------------------------------------
std::string CreatePoint(double x, double y, double z,
                        int level, int color, int weight,
                        bool deferRedraw)
{
    DPoint3d pt;
    pt.x = x; pt.y = y; pt.z = z;

    MSElementDescr* elDscr = NULL;
    int rc = mdlPointString_create(&elDscr, NULL, &pt, NULL, 1, FALSE);
    if (rc != SUCCESS || !elDscr)
        return "";

    ApplySymbology(elDscr, level, color, weight, 0);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateText - tao text element
// -----------------------------------------------------------------------
std::string CreateText(double x, double y, double z,
                       const char* text, double height, double rotation,
                       int level, int color,
                       bool deferRedraw)
{
    if (!text || text[0] == '\0' || height <= 0.0) return "";

    TextParam tp;
    ZeroMemory(&tp, sizeof(tp));
    tp.height = height;
    tp.width  = height;
    tp.angle  = rotation;

    DPoint3d origin;
    origin.x = x; origin.y = y; origin.z = z;

    MSElementDescr* elDscr = NULL;
    int rc = mdlText_create(&elDscr, NULL, text, &tp, &origin);
    if (rc != SUCCESS || !elDscr)
        return "";

    if (color >= 0 && color <= 255 && elDscr->el)
        mdlElement_setColor(elDscr->el, NULL, (UShort)color);

    if (level > 0 && elDscr->el)
        mdlElement_setLevel(elDscr->el, mdlModelRef_getActive(), (LevelId)level);
    else if (elDscr->el)
        mdlElement_setLevel(elDscr->el, mdlModelRef_getActive(), (LevelId)tcb->level);

    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// CreateCell - dat cell tu library hoac cell container
// -----------------------------------------------------------------------
std::string CreateCell(double x, double y, double z,
                       const char* cellName, double scale, double rotationDeg,
                       int level, int color, int weight, int style,
                       bool deferRedraw)
{
    if (!cellName || !*cellName) return "";

    DPoint3d origin;
    origin.x = x; origin.y = y; origin.z = z;

    DPoint3d scaleVec;
    double sVal = (scale > 0.0) ? scale : 1.0;
    scaleVec.x = sVal; scaleVec.y = sVal; scaleVec.z = sVal;

    RotMatrix rMatrix;
    mdlRMatrix_fromAxisAndRotationAngle(&rMatrix, 2, rotationDeg * (M_PI / 180.0));

    MSElementDescr* elDscr = NULL;
    ModelRefP activeModel = mdlModelRef_getActive();

    // Thu dat cell tu cell library dang mo
    int rc = mdlCell_place(&elDscr, &origin, &scaleVec, &rMatrix, (char*)cellName, activeModel);
    if (rc != SUCCESS || !elDscr)
    {
        // Fallback: Tao Cell Header container rong
        MSElement cellHdr;
        rc = mdlCell_create(&cellHdr, (char*)cellName, &origin, FALSE);
        if (rc != SUCCESS) return "";
        rc = mdlElmdscr_new(&elDscr, NULL, &cellHdr);
        if (rc != SUCCESS || !elDscr) return "";
    }

    ApplySymbology(elDscr, level, color, weight, style);
    return AddElementToModel(elDscr, deferRedraw);
}

// -----------------------------------------------------------------------
// Ham ho tro: lay MSElementDescr tu elementId (file position)
// -----------------------------------------------------------------------
static MSElementDescrP GetElementDescrById(long long elementId, ModelRefP model)
{
    if (elementId <= 0) return NULL;
    UInt32 filePos = (UInt32)elementId;

    MSElementDescr* elDscr = NULL;
    int rc = mdlElmdscr_read(&elDscr, filePos, model);
    if (rc != SUCCESS || !elDscr)
        return NULL;

    return elDscr;
}

// -----------------------------------------------------------------------
// MoveElement - di chuyen element theo vector
// -----------------------------------------------------------------------
bool MoveElement(long long elementId, double dx, double dy, double dz)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    // Tao transform matrix dich chuyen
    Transform3d xfm;
    DPoint3d delta;
    delta.x = dx; delta.y = dy; delta.z = dz;
    mdlTMatrix_fromTranslation(&xfm, &delta);

    // Ap dung transform
    mdlElmdscr_transform(elDscr, &xfm);

    // Ghi lai element da thay doi
    UInt32 filePos = (UInt32)elementId;
    int rc = mdlElmdscr_rewrite(elDscr, NULL, filePos, model);

    mdlElmdscr_freeAll(&elDscr);

    if (rc == SUCCESS)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------
// CopyElement - sao chep element
// -----------------------------------------------------------------------
bool CopyElement(long long elementId, double dx, double dy, double dz,
                 std::string& newId)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    // Sao chep element descriptor
    MSElementDescrP copyDscr = NULL;
    mdlElmdscr_duplicate(&copyDscr, elDscr);
    mdlElmdscr_freeAll(&elDscr);

    if (!copyDscr) return false;

    // Dich chuyen ban sao
    Transform3d xfm;
    DPoint3d delta;
    delta.x = dx; delta.y = dy; delta.z = dz;
    mdlTMatrix_fromTranslation(&xfm, &delta);
    mdlElmdscr_transform(copyDscr, &xfm);

    // Them ban sao vao model
    newId = AddElementToModel(copyDscr);
    return !newId.empty();
}

// -----------------------------------------------------------------------
// RotateElement - xoay element quanh mot diem (2D, quanh truc Z)
// -----------------------------------------------------------------------
bool RotateElement(long long elementId, double cx, double cy, double cz,
                   double angleDeg)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    // Chuyen do sang radian
    double angleRad = angleDeg * M_PI / 180.0;

    // Tao transform: xoay quanh diem (cx, cy, cz)
    // B1: Dich ve goc (0,0,0)
    // B2: Xoay
    // B3: Dich lai vi tri cu
    DPoint3d pivot;
    pivot.x = cx; pivot.y = cy; pivot.z = cz;

    RotMatrix rotMat;
    // Xoay quanh truc Z (axis = 2)
    mdlRMatrix_fromAxisAndRotationAngle(&rotMat, 2, angleRad);

    Transform3d xfm;
    // Tao transform xoay quanh pivot point
    mdlTMatrix_fromOriginAndRotMatrix(&xfm, &pivot, &rotMat);

    // Ap dung: translate to origin, rotate, translate back
    // MicroStation API mdlElmdscr_rotateAboutPoint hoac dung transform matrix thu cong
    // Dung phuong phap: T(-pivot) * R * T(pivot)
    Transform3d tToOrigin, tBack, rotate3d, combined;
    DPoint3d negPivot;
    negPivot.x = -cx; negPivot.y = -cy; negPivot.z = -cz;

    mdlTMatrix_fromTranslation(&tToOrigin, &negPivot);
    mdlTMatrix_fromTranslation(&tBack,     &pivot);
    mdlTMatrix_fromRotMatrix(&rotate3d, &rotMat);

    // combined = tBack * rotate3d * tToOrigin
    mdlTMatrix_multiply(&combined, &tBack,     &rotate3d);
    mdlTMatrix_multiply(&combined, &combined,  &tToOrigin);

    mdlElmdscr_transform(elDscr, &combined);

    UInt32 filePos = (UInt32)elementId;
    int rc = mdlElmdscr_rewrite(elDscr, NULL, filePos, model);
    mdlElmdscr_freeAll(&elDscr);

    if (rc == SUCCESS)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------
// ScaleElement - phong to/thu nho element quanh mot diem
// -----------------------------------------------------------------------
bool ScaleElement(long long elementId, double cx, double cy, double cz,
                  double sx, double sy, double sz)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    DPoint3d pivot;
    pivot.x = cx; pivot.y = cy; pivot.z = cz;

    DPoint3d negPivot;
    negPivot.x = -cx; negPivot.y = -cy; negPivot.z = -cz;

    // Scale matrix
    RotMatrix scaleMat;
    ZeroMemory(&scaleMat, sizeof(scaleMat));
    scaleMat.form3d[0][0] = sx;
    scaleMat.form3d[1][1] = sy;
    scaleMat.form3d[2][2] = sz;

    Transform3d tToOrigin, tBack, scaleXfm, combined;
    mdlTMatrix_fromTranslation(&tToOrigin, &negPivot);
    mdlTMatrix_fromTranslation(&tBack,     &pivot);
    mdlTMatrix_fromRotMatrix(&scaleXfm, &scaleMat);

    mdlTMatrix_multiply(&combined, &tBack,    &scaleXfm);
    mdlTMatrix_multiply(&combined, &combined, &tToOrigin);

    mdlElmdscr_transform(elDscr, &combined);

    UInt32 filePos = (UInt32)elementId;
    int rc = mdlElmdscr_rewrite(elDscr, NULL, filePos, model);
    mdlElmdscr_freeAll(&elDscr);

    if (rc == SUCCESS)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------
// DeleteElement - xoa element khoi active model
// -----------------------------------------------------------------------
bool DeleteElement(long long elementId)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    UInt32 filePos = (UInt32)elementId;

    // Doc element de xac nhan ton tai
    MSElementDescrP elDscr = NULL;
    int rc = mdlElmdscr_read(&elDscr, filePos, model);
    if (rc != SUCCESS || !elDscr)
        return false;

    mdlElmdscr_freeAll(&elDscr);

    // Xoa bang cach danh dau deleted
    rc = mdlElement_delete(filePos, model);
    if (rc == SUCCESS)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------
// ChangeSymbology - thay doi thuoc tinh hien thi element
// -----------------------------------------------------------------------
bool ChangeSymbology(long long elementId, int level, int color,
                     int weight, int style)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    if (elDscr->el)
    {
        // Level
        if (level > 0)
            mdlElement_setLevel(elDscr->el, model, (LevelId)level);

        // Color
        if (color >= 0 && color <= 255)
            mdlElement_setColor(elDscr->el, NULL, (UShort)color);

        // Weight
        if (weight >= 0 && weight <= 31)
            mdlElement_setWeight(elDscr->el, NULL, (UShort)weight);

        // Style
        if (style >= 0)
            mdlElement_setStyle(elDscr->el, NULL, (UShort)style);
    }

    UInt32 filePos = (UInt32)elementId;
    int rc = mdlElmdscr_rewrite(elDscr, NULL, filePos, model);
    mdlElmdscr_freeAll(&elDscr);

    if (rc == SUCCESS)
    {
        mdlOutput_reDraw(NULL, REDRAW_ALL);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------
// GetElementDetails - lay thong tin chi tiet cua mot element
// -----------------------------------------------------------------------
bool GetElementDetails(long long elementId, std::string& jsonOut)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    MSElementDescrP elDscr = GetElementDescrById(elementId, model);
    if (!elDscr) return false;

    MSElement* el = elDscr->el;
    if (!el)
    {
        mdlElmdscr_freeAll(&elDscr);
        return false;
    }

    // Doc cac thuoc tinh co ban
    int elemType = (int)el->ehdr.type;

    UShort color  = 0;
    UShort weight = 0;
    UShort style  = 0;
    mdlElement_getColor(&color,  el, NULL);
    mdlElement_getWeight(&weight, el, NULL);
    mdlElement_getStyle(&style,  el, NULL);

    LevelId levelId = INVALID_LEVELID;
    mdlElement_getLevel(&levelId, el, model);

    char levelName[256] = "";
    if (levelId != INVALID_LEVELID)
        mdlLevel_getName(model, levelId, levelName, sizeof(levelName) - 1);

    // Lay range (bounding box)
    DRange3d range;
    ZeroMemory(&range, sizeof(range));
    mdlElmdscr_getRange(&range, elDscr, NULL);

    char buf[64];
    jsonOut  = "{";
    jsonOut += "\"element_id\":";
    std::sprintf(buf, "%lld", elementId);
    jsonOut += buf;
    jsonOut += ",\"type\":";
    jsonOut += JsonBuilder::escapeString(ElementTypeName(elemType));
    jsonOut += ",\"level_id\":";
    std::sprintf(buf, "%d", (int)levelId);
    jsonOut += buf;
    jsonOut += ",\"level_name\":";
    jsonOut += JsonBuilder::escapeString(levelName);
    jsonOut += ",\"color\":";
    std::sprintf(buf, "%d", (int)color);
    jsonOut += buf;
    jsonOut += ",\"weight\":";
    std::sprintf(buf, "%d", (int)weight);
    jsonOut += buf;
    jsonOut += ",\"style\":";
    std::sprintf(buf, "%d", (int)style);
    jsonOut += buf;
    // Bounding box
    jsonOut += ",\"range\":{";
    std::sprintf(buf, "%.6g", range.low.x);  jsonOut += "\"min_x\":"; jsonOut += buf;
    std::sprintf(buf, "%.6g", range.low.y);  jsonOut += ",\"min_y\":"; jsonOut += buf;
    std::sprintf(buf, "%.6g", range.low.z);  jsonOut += ",\"min_z\":"; jsonOut += buf;
    std::sprintf(buf, "%.6g", range.high.x); jsonOut += ",\"max_x\":"; jsonOut += buf;
    std::sprintf(buf, "%.6g", range.high.y); jsonOut += ",\"max_y\":"; jsonOut += buf;
    std::sprintf(buf, "%.6g", range.high.z); jsonOut += ",\"max_z\":"; jsonOut += buf;
    jsonOut += "}}";

    mdlElmdscr_freeAll(&elDscr);
    return true;
}

// -----------------------------------------------------------------------
// ScanElements - quet element trong active model theo bo loc
//
// Su dung ScanCriteria API cua MDL V8i.
// -----------------------------------------------------------------------

// Struct du lieu truyen vao scan callback
struct ScanCallbackData
{
    std::string* jsonArray; // Output JSON array
    const char*  typeFilter;
    int          maxCount;
    int          count;
};

// Ham callback goi khi tim thay moi element
static int ScanCallback(MSElementDescrP elDscr, void* userData)
{
    ScanCallbackData* data = (ScanCallbackData*)userData;
    if (!data || !elDscr || !elDscr->el) return FALSE;

    if (data->count >= data->maxCount)
        return FALSE; // Dung scan

    MSElement* el = elDscr->el;
    int elemType = (int)el->ehdr.type;

    // Ap dung bo loc kieu element
    if (data->typeFilter && data->typeFilter[0] != '\0')
    {
        if (std::strcmp(ElementTypeName(elemType), data->typeFilter) != 0)
            return TRUE; // Bo qua, tiep tuc
    }

    // Doc thuoc tinh
    UShort color = 0, weight = 0, style = 0;
    mdlElement_getColor(&color, el, NULL);
    mdlElement_getWeight(&weight, el, NULL);
    mdlElement_getStyle(&style, el, NULL);

    LevelId levelId = INVALID_LEVELID;
    ModelRefP model = mdlModelRef_getActive();
    mdlElement_getLevel(&levelId, el, model);

    UInt32 filePos = 0;
    mdlElement_getFilePosition(&filePos, el);

    // Them vao JSON array
    if (data->count > 0)
        *data->jsonArray += ",";

    char buf[64];
    *data->jsonArray += "{\"element_id\":";
    std::sprintf(buf, "%lu", (unsigned long)filePos);
    *data->jsonArray += buf;
    *data->jsonArray += ",\"type\":";
    *data->jsonArray += JsonBuilder::escapeString(ElementTypeName(elemType));
    *data->jsonArray += ",\"level_id\":";
    std::sprintf(buf, "%d", (int)levelId);
    *data->jsonArray += buf;
    *data->jsonArray += ",\"color\":";
    std::sprintf(buf, "%d", (int)color);
    *data->jsonArray += buf;
    *data->jsonArray += ",\"weight\":";
    std::sprintf(buf, "%d", (int)weight);
    *data->jsonArray += buf;
    *data->jsonArray += ",\"style\":";
    std::sprintf(buf, "%d", (int)style);
    *data->jsonArray += buf;
    *data->jsonArray += "}";

    data->count++;
    return TRUE; // Tiep tuc scan
}

bool ScanElements(const char* typeFilter, int maxCount, std::string& jsonArrayOut)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    jsonArrayOut = "[";

    ScanCallbackData cbData;
    cbData.jsonArray = &jsonArrayOut;
    cbData.typeFilter = typeFilter;
    cbData.maxCount  = maxCount;
    cbData.count     = 0;

    // Tao scan criteria
    ScanCriteriaP sc = mdlScanCriteria_create();
    if (!sc) return false;

    // Scan tat ca element (khong loc theo type o day - loc trong callback)
    mdlScanCriteria_setIncludeNulledElements(sc, FALSE);

    // Thuc hien scan
    mdlModelRef_scanElements(model, sc, ScanCallback, &cbData, NULL);
    mdlScanCriteria_free(sc);

    jsonArrayOut += "]";
    return true;
}

// -----------------------------------------------------------------------
// GetModelSnapshot - lay toan bo snapshot cua active model
// -----------------------------------------------------------------------
bool GetModelSnapshot(std::string& jsonOut)
{
    ModelRefP model = mdlModelRef_getActive();
    if (!model) return false;

    char modelName[256] = "";
    mdlModelRef_getActiveName(model, modelName, sizeof(modelName) - 1);

    std::string elementsJson;
    if (!ScanElements("", 10000, elementsJson))
        return false;

    jsonOut  = "{";
    jsonOut += "\"model_name\":";
    jsonOut += JsonBuilder::escapeString(modelName);
    jsonOut += ",\"elements\":";
    jsonOut += elementsJson;
    jsonOut += "}";

    return true;
}
