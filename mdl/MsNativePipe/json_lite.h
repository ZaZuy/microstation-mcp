/*===========================================================================
 * json_lite.h  -  Tiny header-only JSON encoder/decoder
 *
 * Muc dich: Cung cap parser va builder JSON toi gian, khong phu thuoc
 *           thu vien ngoai, dung trong moi truong MDL/MicroStation V8i.
 *
 * Ho tro kieu du lieu:
 *   - Object   : { "key": value, ... }
 *   - Array    : [ value, ... ]
 *   - String   : "..."  (escape: \\ \" \n \r \t \/)
 *   - Number   : double (integer va floating-point)
 *   - Bool     : true / false
 *   - Null     : null
 *
 * Tac gia: MsNativePipe MDL Project
 * Phien ban: 1.0
 *===========================================================================*/
#pragma once

#include <string>
#include <vector>
#include <stdexcept>
#include <sstream>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <cctype>

// ======================================================================
// Kieu du lieu JSON
// ======================================================================
enum JsonType
{
    JSON_NULL    = 0,   // null
    JSON_BOOL    = 1,   // true / false
    JSON_NUMBER  = 2,   // so thuc double
    JSON_STRING  = 3,   // chuoi ky tu
    JSON_ARRAY   = 4,   // mang
    JSON_OBJECT  = 5    // object (key-value)
};

// ======================================================================
// Forward declarations
// ======================================================================
struct JsonValue;
typedef std::vector<JsonValue>                              JsonArray;
typedef std::vector<std::pair<std::string, JsonValue> >    JsonObject;

// ======================================================================
// Struct JsonValue - bieu dien mot node trong cay JSON
// ======================================================================
struct JsonValue
{
    JsonType    type;

    // Cac truong luu gia tri - chi mot truong duoc dung tai mot thoi diem
    bool        boolVal;
    double      numVal;
    std::string strVal;

    // Con tro den mang/object dung heap de tranh de quy trong struct
    JsonArray*  arrVal;
    JsonObject* objVal;

    // -- Constructors ------------------------------------------------------

    // Constructor mac dinh: null
    JsonValue()
        : type(JSON_NULL), boolVal(false), numVal(0.0),
          arrVal(NULL), objVal(NULL) {}

    // Constructor bool
    explicit JsonValue(bool v)
        : type(JSON_BOOL), boolVal(v), numVal(0.0),
          arrVal(NULL), objVal(NULL) {}

    // Constructor so nguyen (chuyen ve double)
    explicit JsonValue(int v)
        : type(JSON_NUMBER), boolVal(false), numVal((double)v),
          arrVal(NULL), objVal(NULL) {}

    // Constructor long long
    explicit JsonValue(long long v)
        : type(JSON_NUMBER), boolVal(false), numVal((double)v),
          arrVal(NULL), objVal(NULL) {}

    // Constructor unsigned long long
    explicit JsonValue(unsigned long long v)
        : type(JSON_NUMBER), boolVal(false), numVal((double)v),
          arrVal(NULL), objVal(NULL) {}

    // Constructor double
    explicit JsonValue(double v)
        : type(JSON_NUMBER), boolVal(false), numVal(v),
          arrVal(NULL), objVal(NULL) {}

    // Constructor chuoi (const char*)
    explicit JsonValue(const char* v)
        : type(JSON_STRING), boolVal(false), numVal(0.0),
          strVal(v ? v : ""), arrVal(NULL), objVal(NULL) {}

    // Constructor chuoi (std::string)
    explicit JsonValue(const std::string& v)
        : type(JSON_STRING), boolVal(false), numVal(0.0),
          strVal(v), arrVal(NULL), objVal(NULL) {}

    // Constructor mang
    explicit JsonValue(const JsonArray& arr)
        : type(JSON_ARRAY), boolVal(false), numVal(0.0),
          arrVal(NULL), objVal(NULL)
    {
        arrVal = new JsonArray(arr);
    }

    // Constructor object
    explicit JsonValue(const JsonObject& obj)
        : type(JSON_OBJECT), boolVal(false), numVal(0.0),
          arrVal(NULL), objVal(NULL)
    {
        objVal = new JsonObject(obj);
    }

    // -- Copy Constructor --------------------------------------------------
    JsonValue(const JsonValue& other)
        : type(other.type), boolVal(other.boolVal), numVal(other.numVal),
          strVal(other.strVal), arrVal(NULL), objVal(NULL)
    {
        if (other.arrVal) arrVal = new JsonArray(*other.arrVal);
        if (other.objVal) objVal = new JsonObject(*other.objVal);
    }

    // -- Assignment Operator -----------------------------------------------
    JsonValue& operator=(const JsonValue& other)
    {
        if (this == &other) return *this;
        // Giai phong bo nho cu
        delete arrVal; arrVal = NULL;
        delete objVal; objVal = NULL;
        // Sao chep du lieu moi
        type    = other.type;
        boolVal = other.boolVal;
        numVal  = other.numVal;
        strVal  = other.strVal;
        if (other.arrVal) arrVal = new JsonArray(*other.arrVal);
        if (other.objVal) objVal = new JsonObject(*other.objVal);
        return *this;
    }

    // -- Destructor --------------------------------------------------------
    ~JsonValue()
    {
        delete arrVal; arrVal = NULL;
        delete objVal; objVal = NULL;
    }

    // -- Accessor helpers --------------------------------------------------

    bool isNull()   const { return type == JSON_NULL;   }
    bool isBool()   const { return type == JSON_BOOL;   }
    bool isNumber() const { return type == JSON_NUMBER; }
    bool isString() const { return type == JSON_STRING; }
    bool isArray()  const { return type == JSON_ARRAY;  }
    bool isObject() const { return type == JSON_OBJECT; }

    bool        getBool()   const { return (type == JSON_BOOL)   ? boolVal : false; }
    double      getNumber() const { return (type == JSON_NUMBER) ? numVal  : 0.0;   }
    int         getInt()    const { return (int)getNumber(); }
    long long   getInt64()  const { return (long long)getNumber(); }
    const std::string& getString() const { return strVal; }

    JsonArray*  getArray()       { return arrVal; }
    const JsonArray*  getArray()  const { return arrVal; }
    JsonObject* getObject()      { return objVal; }
    const JsonObject* getObject() const { return objVal; }

    // Truy cap phan tu trong object theo key
    const JsonValue& operator[](const std::string& key) const
    {
        static JsonValue nullVal;
        if (type != JSON_OBJECT || !objVal) return nullVal;
        for (size_t i = 0; i < objVal->size(); ++i)
        {
            if ((*objVal)[i].first == key)
                return (*objVal)[i].second;
        }
        return nullVal;
    }

    const JsonValue& operator[](const char* key) const
    {
        return (*this)[std::string(key)];
    }

    // Truy cap phan tu trong array theo index
    const JsonValue& operator[](int idx) const
    {
        static JsonValue nullVal;
        if (type != JSON_ARRAY || !arrVal) return nullVal;
        if (idx < 0 || idx >= (int)arrVal->size()) return nullVal;
        return (*arrVal)[idx];
    }

    // Kiem tra object co chua key khong
    bool hasKey(const std::string& key) const
    {
        if (type != JSON_OBJECT || !objVal) return false;
        for (size_t i = 0; i < objVal->size(); ++i)
        {
            if ((*objVal)[i].first == key) return true;
        }
        return false;
    }

    // So phan tu trong array hoac object
    size_t size() const
    {
        if (type == JSON_ARRAY  && arrVal) return arrVal->size();
        if (type == JSON_OBJECT && objVal) return objVal->size();
        return 0;
    }
};

// ======================================================================
// JsonParser - phan tich cu phap chuoi JSON
// ======================================================================
class JsonParser
{
public:
    // Phan tich chuoi JSON, tra ve JsonValue goc.
    // Nem std::runtime_error neu JSON khong hop le.
    static JsonValue parse(const std::string& json)
    {
        JsonParser p(json);
        p.skipWhitespace();
        JsonValue val = p.parseValue();
        return val;
    }

private:
    const std::string& src_;
    size_t             pos_;

    explicit JsonParser(const std::string& src) : src_(src), pos_(0) {}

    char current() const
    {
        if (pos_ >= src_.size()) return '\0';
        return src_[pos_];
    }

    char consume()
    {
        if (pos_ >= src_.size())
            throw std::runtime_error("JSON: doc ngoai cuoi chuoi");
        return src_[pos_++];
    }

    void expect(char ch)
    {
        skipWhitespace();
        if (current() != ch)
        {
            char msg[64];
            std::sprintf(msg, "JSON: mong doi '%c' nhung gap '%c'", ch, current());
            throw std::runtime_error(msg);
        }
        ++pos_;
    }

    void skipWhitespace()
    {
        while (pos_ < src_.size() &&
               (src_[pos_] == ' '  || src_[pos_] == '\t' ||
                src_[pos_] == '\n' || src_[pos_] == '\r'))
        {
            ++pos_;
        }
    }

    // Parse gia tri bat ky
    JsonValue parseValue()
    {
        skipWhitespace();
        char ch = current();

        if (ch == '"')  return parseString();
        if (ch == '{')  return parseObject();
        if (ch == '[')  return parseArray();
        if (ch == 't')  return parseLiteral("true",  JsonValue(true));
        if (ch == 'f')  return parseLiteral("false", JsonValue(false));
        if (ch == 'n')  return parseLiteral("null",  JsonValue());
        if (ch == '-' || (ch >= '0' && ch <= '9'))
                        return parseNumber();

        char msg[64];
        std::sprintf(msg, "JSON: ky tu khong mong doi '%c' tai vi tri %zu", ch, pos_);
        throw std::runtime_error(msg);
    }

    // Parse literal: true, false, null
    JsonValue parseLiteral(const char* lit, JsonValue result)
    {
        size_t len = std::strlen(lit);
        if (src_.compare(pos_, len, lit) != 0)
            throw std::runtime_error("JSON: khong nhan ra literal");
        pos_ += len;
        return result;
    }

    // Parse string JSON
    JsonValue parseString()
    {
        return JsonValue(parseRawString());
    }

    std::string parseRawString()
    {
        expect('"');
        std::string result;
        result.reserve(64);

        while (pos_ < src_.size())
        {
            unsigned char ch = (unsigned char)src_[pos_++];
            if (ch == '"') break;

            if (ch == '\\')
            {
                if (pos_ >= src_.size())
                    throw std::runtime_error("JSON: escape khong hoan chinh");
                unsigned char esc = (unsigned char)src_[pos_++];
                switch (esc)
                {
                case '"':  result += '"';  break;
                case '\\': result += '\\'; break;
                case '/':  result += '/';  break;
                case 'b':  result += '\b'; break;
                case 'f':  result += '\f'; break;
                case 'n':  result += '\n'; break;
                case 'r':  result += '\r'; break;
                case 't':  result += '\t'; break;
                case 'u':
                {
                    // Doc 4 hex digits
                    unsigned int cp = 0;
                    for (int i = 0; i < 4; ++i)
                    {
                        if (pos_ >= src_.size())
                            throw std::runtime_error("JSON: \\u khong hoan chinh");
                        unsigned char hx = (unsigned char)src_[pos_++];
                        cp <<= 4;
                        if      (hx >= '0' && hx <= '9') cp |= (hx - '0');
                        else if (hx >= 'a' && hx <= 'f') cp |= (hx - 'a' + 10);
                        else if (hx >= 'A' && hx <= 'F') cp |= (hx - 'A' + 10);
                        else throw std::runtime_error("JSON: \\u hex khong hop le");
                    }
                    // Encode UTF-8
                    if (cp <= 0x7F)
                    {
                        result += (char)cp;
                    }
                    else if (cp <= 0x7FF)
                    {
                        result += (char)(0xC0 | (cp >> 6));
                        result += (char)(0x80 | (cp & 0x3F));
                    }
                    else
                    {
                        result += (char)(0xE0 | (cp >> 12));
                        result += (char)(0x80 | ((cp >> 6) & 0x3F));
                        result += (char)(0x80 | (cp & 0x3F));
                    }
                    break;
                }
                default:
                    result += (char)esc;
                    break;
                }
            }
            else
            {
                result += (char)ch;
            }
        }
        return result;
    }

    // Parse number
    JsonValue parseNumber()
    {
        size_t start = pos_;
        if (current() == '-') ++pos_;
        if (current() == '0') { ++pos_; }
        else
        {
            while (pos_ < src_.size() && src_[pos_] >= '0' && src_[pos_] <= '9')
                ++pos_;
        }
        if (pos_ < src_.size() && src_[pos_] == '.')
        {
            ++pos_;
            while (pos_ < src_.size() && src_[pos_] >= '0' && src_[pos_] <= '9')
                ++pos_;
        }
        if (pos_ < src_.size() && (src_[pos_] == 'e' || src_[pos_] == 'E'))
        {
            ++pos_;
            if (pos_ < src_.size() && (src_[pos_] == '+' || src_[pos_] == '-'))
                ++pos_;
            while (pos_ < src_.size() && src_[pos_] >= '0' && src_[pos_] <= '9')
                ++pos_;
        }
        std::string numStr = src_.substr(start, pos_ - start);
        double val = std::atof(numStr.c_str());
        return JsonValue(val);
    }

    // Parse array
    JsonValue parseArray()
    {
        expect('[');
        JsonArray arr;
        skipWhitespace();
        if (current() == ']') { ++pos_; return JsonValue(arr); }
        while (true)
        {
            skipWhitespace();
            arr.push_back(parseValue());
            skipWhitespace();
            if (current() == ']') { ++pos_; break; }
            if (current() == ',') { ++pos_; continue; }
            throw std::runtime_error("JSON: mong doi ',' hoac ']' trong array");
        }
        return JsonValue(arr);
    }

    // Parse object
    JsonValue parseObject()
    {
        expect('{');
        JsonObject obj;
        skipWhitespace();
        if (current() == '}') { ++pos_; return JsonValue(obj); }
        while (true)
        {
            skipWhitespace();
            if (current() != '"')
                throw std::runtime_error("JSON: mong doi key string trong object");
            std::string key = parseRawString();
            skipWhitespace();
            expect(':');
            skipWhitespace();
            JsonValue val = parseValue();
            obj.push_back(std::make_pair(key, val));
            skipWhitespace();
            if (current() == '}') { ++pos_; break; }
            if (current() == ',') { ++pos_; continue; }
            throw std::runtime_error("JSON: mong doi ',' hoac '}' trong object");
        }
        return JsonValue(obj);
    }
};

// ======================================================================
// JsonBuilder - tao chuoi JSON tu du lieu C++
// ======================================================================
class JsonBuilder
{
public:
    // Chuyen JsonValue thanh chuoi JSON
    static std::string stringify(const JsonValue& val)
    {
        std::string out;
        out.reserve(256);
        writeValue(out, val);
        return out;
    }

    // Escape mot chuoi thanh JSON string (co dau nhay kep)
    static std::string escapeString(const std::string& s)
    {
        std::string out;
        out.reserve(s.size() + 2);
        out += '"';
        for (size_t i = 0; i < s.size(); ++i)
        {
            unsigned char ch = (unsigned char)s[i];
            switch (ch)
            {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b";  break;
            case '\f': out += "\\f";  break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (ch < 0x20)
                {
                    char buf[8];
                    std::sprintf(buf, "\\u%04X", (unsigned)ch);
                    out += buf;
                }
                else
                {
                    out += (char)ch;
                }
                break;
            }
        }
        out += '"';
        return out;
    }

    // Chuyen double thanh chuoi so
    static std::string numberToString(double v)
    {
        // Kiem tra so nguyen
        if (v >= -9.0e18 && v <= 9.0e18 && v == (double)(long long)v)
        {
            char buf[32];
            std::sprintf(buf, "%lld", (long long)v);
            return buf;
        }
        char buf[64];
        std::sprintf(buf, "%.15g", v);
        return buf;
    }

private:
    static void writeValue(std::string& out, const JsonValue& val)
    {
        switch (val.type)
        {
        case JSON_NULL:
            out += "null";
            break;
        case JSON_BOOL:
            out += val.boolVal ? "true" : "false";
            break;
        case JSON_NUMBER:
            out += numberToString(val.numVal);
            break;
        case JSON_STRING:
            out += escapeString(val.strVal);
            break;
        case JSON_ARRAY:
            writeArray(out, val);
            break;
        case JSON_OBJECT:
            writeObject(out, val);
            break;
        }
    }

    static void writeArray(std::string& out, const JsonValue& val)
    {
        out += '[';
        if (val.arrVal)
        {
            for (size_t i = 0; i < val.arrVal->size(); ++i)
            {
                if (i > 0) out += ',';
                writeValue(out, (*val.arrVal)[i]);
            }
        }
        out += ']';
    }

    static void writeObject(std::string& out, const JsonValue& val)
    {
        out += '{';
        if (val.objVal)
        {
            for (size_t i = 0; i < val.objVal->size(); ++i)
            {
                if (i > 0) out += ',';
                out += escapeString((*val.objVal)[i].first);
                out += ':';
                writeValue(out, (*val.objVal)[i].second);
            }
        }
        out += '}';
    }
};

// ======================================================================
// Ham tien ich tao response JSON chuan
// ======================================================================

// Tao response thanh cong: {"id":N,"success":true,"data":{...},"message":"OK"}
inline std::string MakeSuccessResponse(long long id,
                                       const std::string& dataJson,
                                       const std::string& message = "OK")
{
    std::string out;
    out.reserve(256);
    char buf[32];
    std::sprintf(buf, "%lld", id);
    out += "{\"id\":";
    out += buf;
    out += ",\"success\":true,\"data\":";
    out += dataJson.empty() ? "null" : dataJson;
    out += ",\"message\":";
    out += JsonBuilder::escapeString(message);
    out += "}";
    return out;
}

// Tao response loi: {"id":N,"success":false,"data":null,"message":"..."}
inline std::string MakeErrorResponse(long long id, const std::string& message)
{
    std::string out;
    out.reserve(128);
    char buf[32];
    std::sprintf(buf, "%lld", id);
    out += "{\"id\":";
    out += buf;
    out += ",\"success\":false,\"data\":null,\"message\":";
    out += JsonBuilder::escapeString(message);
    out += "}";
    return out;
}

// ======================================================================
// Ham doc field an toan tu JsonValue
// ======================================================================

inline double JsonGetDouble(const JsonValue& obj, const char* key,
                            double def = 0.0)
{
    const JsonValue& v = obj[key];
    return v.isNumber() ? v.getNumber() : def;
}

inline int JsonGetInt(const JsonValue& obj, const char* key, int def = 0)
{
    const JsonValue& v = obj[key];
    return v.isNumber() ? v.getInt() : def;
}

inline long long JsonGetInt64(const JsonValue& obj, const char* key,
                              long long def = 0LL)
{
    const JsonValue& v = obj[key];
    return v.isNumber() ? v.getInt64() : def;
}

inline std::string JsonGetString(const JsonValue& obj, const char* key,
                                 const std::string& def = "")
{
    const JsonValue& v = obj[key];
    return v.isString() ? v.getString() : def;
}

inline bool JsonGetBool(const JsonValue& obj, const char* key, bool def = false)
{
    const JsonValue& v = obj[key];
    return v.isBool() ? v.getBool() : def;
}
