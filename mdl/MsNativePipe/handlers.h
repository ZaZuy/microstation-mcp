/*===========================================================================
 * handlers.h  -  Request dispatcher cho MsNativePipe MDL
 *
 * Muc dich: Khai bao ham HandleRequest() phan tich JSON request va
 *           dieu phoi toi handler tuong ung.
 *
 * Tat ca handlers duoc goi tu MDL main thread (timer callback).
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/
#pragma once

#include <string>

/**
 * Phan tich JSON request string va goi handler tuong ung.
 *
 * Dinh dang request:
 *   {"id": <int>, "command": "<ten>", "params": {...}}
 *
 * Dinh dang response thanh cong:
 *   {"id": <int>, "success": true, "data": {...}, "message": "OK"}
 *
 * Dinh dang response loi:
 *   {"id": <int>, "success": false, "data": null, "message": "<mo ta loi>"}
 *
 * @param jsonRequest  Chuoi JSON request tu client
 * @return             Chuoi JSON response gui ve client
 */
std::string HandleRequest(const std::string& jsonRequest);
