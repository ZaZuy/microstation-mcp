/*===========================================================================
 * batch.h  -  Batch element creation cho MsNativePipe MDL (header)
 *
 * Muc dich: Khai bao ham BatchCreate() xu ly lenh batch_create,
 *           tao nhieu element trong mot lan goi, ho tro undo group.
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/
#pragma once

#include <string>

/**
 * Xu ly lenh batch_create - tao nhieu element trong mot transaction.
 *
 * Dinh dang elementsJson (JSON array):
 * [
 *   {"type":"line",       "params":{x1,y1,z1,x2,y2,z2,level,color,weight,style}},
 *   {"type":"linestring", "params":{points:[[x,y,z],...],level,color,weight,style}},
 *   {"type":"circle",     "params":{cx,cy,cz,radius,level,color,weight,style}},
 *   {"type":"arc",        "params":{cx,cy,cz,radius,start_angle,sweep_angle,...}},
 *   {"type":"ellipse",    "params":{cx,cy,cz,primary_r,secondary_r,rotation,...}},
 *   {"type":"shape",      "params":{points:[[x,y,z],...],filled,fill_color,...}},
 *   {"type":"text",       "params":{x,y,z,text,height,rotation,level,color}},
 *   {"type":"point",      "params":{x,y,z,level,color,weight}}
 * ]
 *
 * Ket qua tra ve (JSON array):
 * [
 *   {"index":0,"success":true,"element_id":"12345","message":"OK"},
 *   {"index":1,"success":false,"element_id":"","message":"Loi..."},
 *   ...
 * ]
 *
 * @param elementsJson  JSON array string mo ta cac element can tao
 * @param useUndoGroup  true: boc trong mdlUndo_startGroup/endGroup
 * @return              JSON array string ket qua tung element
 */
std::string BatchCreate(const std::string& elementsJson, bool useUndoGroup);
