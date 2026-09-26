/*===========================================================================
 * geometry.h  -  MDL geometry creation & modification helpers (header)
 *
 * Muc dich: Khai bao cac ham helper tao va chinh sua element hinh hoc
 *           su dung MDL API cua MicroStation V8i.
 *
 * Tat ca ham phai duoc goi tu MDL main thread.
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/
#pragma once

#include <string>

// MDL SDK headers
extern "C" {
#include <mdl.h>
#include <mselems.h>
#include <msmodel.h>
}

// -----------------------------------------------------------------------
// Ham tao element
// -----------------------------------------------------------------------

/**
 * Tao doan thang va them vao active model.
 * @param deferRedraw  true: khong redraw ngay (dung cho batch create)
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateLine(double x1, double y1, double z1,
                       double x2, double y2, double z2,
                       int level, int color, int weight, int style,
                       bool deferRedraw = false);

/**
 * Tao polyline (linestring) tu mang diem.
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateLineString(const double* xs, const double* ys, const double* zs,
                             int nPts,
                             int level, int color, int weight, int style,
                             bool deferRedraw = false);

/**
 * Tao polygon (shape) tu mang diem.
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateShape(const double* xs, const double* ys, const double* zs,
                        int nPts, bool filled, int fillColor,
                        int level, int color, int weight, int style,
                        bool deferRedraw = false);

/**
 * Tao duong tron.
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateCircle(double cx, double cy, double cz, double radius,
                         int level, int color, int weight, int style,
                         bool deferRedraw = false);

/**
 * Tao cung tron.
 * @param startAngle  Goc bat dau (radian)
 * @param sweepAngle  Goc quet (radian, duong = nguoc chieu kim dong ho)
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateArc(double cx, double cy, double cz, double radius,
                      double startAngle, double sweepAngle,
                      int level, int color, int weight, int style,
                      bool deferRedraw = false);

/**
 * Tao hinh elip.
 * @param primaryR   Ban kinh truc chinh
 * @param secondaryR Ban kinh truc phu
 * @param rotation   Goc xoay truc chinh (radian)
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateEllipse(double cx, double cy, double cz,
                          double primaryR, double secondaryR, double rotation,
                          int level, int color, int weight, int style,
                          bool deferRedraw = false);

/**
 * Tao diem (point element).
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreatePoint(double x, double y, double z,
                        int level, int color, int weight,
                        bool deferRedraw = false);

/**
 * Tao text element.
 * @param height    Chieu cao chu (UOR)
 * @param rotation  Goc xoay (radian)
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateText(double x, double y, double z,
                       const char* text, double height, double rotation,
                       int level, int color,
                       bool deferRedraw = false);

/**
 * Tao cell element (cell placement tu library hoac cell container).
 * @return Element ID dang string, hoac "" neu loi
 */
std::string CreateCell(double x, double y, double z,
                       const char* cellName, double scale, double rotationDeg,
                       int level, int color, int weight, int style,
                       bool deferRedraw = false);

// -----------------------------------------------------------------------
// Ham helper noi bo
// -----------------------------------------------------------------------

/**
 * Ap dung thuoc tinh symbology len element descriptor.
 * Neu gia tri = -1 thi dung thuoc tinh mac dinh (by level / active).
 */
void ApplySymbology(MSElementDescrP elDscr, int level, int color,
                    int weight, int style);

/**
 * Them element descriptor vao active model.
 * Giai phong MSElementDescr sau khi them.
 * @return Element ID dang string, hoac "" neu loi
 */
std::string AddElementToModel(MSElementDescrP elDscr, bool deferRedraw = false);

/**
 * Them pure MSElement (stack struct) vao active model.
 * Khong ton chi phi dynamic memory allocation tren heap.
 * @return Element ID dang string, hoac "" neu loi
 */
std::string AddPureElementToModel(MSElement* el, bool deferRedraw = false);

/**
 * Kich hoat redraw view MicroStation 1 lan duy nhat (sau khi ket thuc batch).
 */
void TriggerModelRedraw();

// -----------------------------------------------------------------------
// Ham chinh sua element
// -----------------------------------------------------------------------

/** Di chuyen element. @return true neu thanh cong */
bool MoveElement(long long elementId, double dx, double dy, double dz);

/** Sao chep element. @param newId [out] ID element moi */
bool CopyElement(long long elementId, double dx, double dy, double dz,
                 std::string& newId);

/** Xoay element quanh mot diem. @param angleDeg Do (khong phai radian) */
bool RotateElement(long long elementId, double cx, double cy, double cz,
                   double angleDeg);

/** Phong to/thu nho element. */
bool ScaleElement(long long elementId, double cx, double cy, double cz,
                  double sx, double sy, double sz);

/** Xoa element. @return true neu thanh cong */
bool DeleteElement(long long elementId);

/** Thay doi symbology (-1 = giu nguyen). @return true neu thanh cong */
bool ChangeSymbology(long long elementId, int level, int color,
                     int weight, int style);

// -----------------------------------------------------------------------
// Ham truy van element
// -----------------------------------------------------------------------

/** Lay thong tin chi tiet element. @param jsonOut [out] JSON object string */
bool GetElementDetails(long long elementId, std::string& jsonOut);

/** Quet elements theo bo loc. @param jsonArrayOut [out] JSON array */
bool ScanElements(const char* typeFilter, int maxCount,
                  std::string& jsonArrayOut);

/** Lay snapshot toan bo model. @param jsonOut [out] JSON object */
bool GetModelSnapshot(std::string& jsonOut);

// -----------------------------------------------------------------------
// Ham tien ich
// -----------------------------------------------------------------------

/** Chuyen file position sang string ID */
std::string FileposToString(UInt32 filePos);

/** Chuyen string ID sang file position. INVALID_FILEPOS neu khong hop le */
UInt32 StringToFilepos(const std::string& s);

/** Lay ten kieu element (LINE_ELM, ARC_ELM, ...) dang string */
const char* ElementTypeName(int elemType);
