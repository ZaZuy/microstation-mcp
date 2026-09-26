---
name: microstation-cad
description: "Chuyên gia CAD đo đạc, biên tập và kiểm tra bản đồ địa chính trên MicroStation V8i tuân thủ Thông tư 26/2024/TT-BTNMT, Thông tư 23/2025/TT-BNNMT và Luật Đất đai 2024. Kích hoạt khi người dùng yêu cầu vẽ, biên tập thửa đất, phân lớp level, tạo nhãn thửa, trích lục địa chính, tính diện tích, kiểm tra ranh giới thửa đất hoặc thao tác MicroStation qua MCP."
---

# Kỹ năng Đo đạc & Biên tập Bản đồ Địa chính MicroStation V8i (Chuẩn TT 26/2024 & TT 23/2025)

Kỹ năng này hướng dẫn AI Agent sử dụng hệ thống công cụ MicroStation MCP Server (`microstation-v8i`) để thao tác, đo đạc, vẽ và kiểm tra bản đồ địa chính, đảm bảo tuân thủ 100% quy chuẩn kỹ thuật của:
1. **Thông tư số 26/2024/TT-BTNMT** ngày 26/11/2024 của Bộ Tài nguyên và Môi trường.
2. **Thông tư số 23/2025/TT-BNNMT** ngày 20/06/2025 của Bộ Nông nghiệp và Môi trường (sửa đổi, bổ sung TT 26/2024 và Văn bản hợp nhất số 34/VBHN-BNNMT).
3. **Luật Đất đai năm 2024** (Luật số 31/2024/QH15).

---

## 1. Quy chuẩn Hệ Tọa độ & Đơn vị Đo (Điều 3 TT 26/2024 & TT 23/2025)

Mọi bản đồ địa chính và hồ sơ trích lục địa chính bắt buộc phải được thiết lập theo quy chuẩn sau:

- **Hệ quy chiếu & Tọa độ**: Hệ quy chiếu quốc gia **VN-2000**, elipsoid WGS-84 toàn cầu.
- **Phép chiếu**: Bản đồ địa chính sử dụng phép chiếu hình trụ ngang đồng góc UTM, **múi chiếu 3°**, hệ số co giãn chiều dài $k_0 = 0.9999$.
- **Kinh tuyến trục**: Tuân thủ theo từng tỉnh, thành phố trực thuộc Trung ương quy định tại Phụ lục 01 Thông tư 26/2024 (và cập nhật điều chỉnh tại Thông tư 23/2025).
- **Thông số đơn vị đo trong MicroStation V8i**:
  - `Master Unit (MU)`: Mét (`m`).
  - `Sub Unit (SU)`: Milimét (`mm`).
  - `Resolution`: 1000 Sub Units / 1 Master Unit (1m = 1000mm).
  - `Global Origin / Design Plane Center`: Toạ độ gốc $X = 500.000\text{ m}$, $Y = 1.000.000\text{ m}$.

---

## 2. Bảng Phân lớp Đối tượng (Level Table) Chuẩn Phụ lục 21

Khi thực hiện lệnh vẽ hoặc biên tập, AI Agent **bắt buộc** phải gán đúng số hiệu Level, Màu sắc (Color), Kiểu nét (Style) và Độ dày nét (Weight):

| Level | Tên lớp đối tượng | Color | Style | Weight | Quy cách kỹ thuật |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | Độ cao (bình độ cơ bản, bình độ cái) | 6 (Nâu) | 0 / 2 | 0 / 1 | Đường đẳng cao nửa khoảng cao đều |
| **2** | **Loại đất hiện trạng** | **4 (Vàng)** | **0** | **0** | Ký hiệu mã loại đất: ODT, ONT, LUC, CLN, TSC... |
| **3** | Ghi chú độ cao, bình độ | 6 (Nâu) | 0 | 0 | Chữ số cao độ, font VNI-Helve hoặc VnArial |
| **4** | **Diện tích thửa đất hiện trạng** | **4 (Vàng)** | **0** | **0** | Diện tích làm tròn 1 chữ số thập phân ($m^2$) |
| **6** | Điểm khống chế trắc địa cơ sở | 0 (Trắng/Đen) | 0 | 2 | Tam giác/vuông mốc tọa độ, độ cao nhà nước |
| **7** | Điểm địa chính cơ sở, trạm đo | 0 (Trắng/Đen) | 0 | 1 | Mốc địa chính các cấp |
| **8** | Điểm khống chế đo vẽ | 0 (Trắng/Đen) | 0 | 1 | Điểm trạm đo chi tiết ngoài thực địa |
| **9** | Ghi chú điểm trắc địa, địa chính | 4 (Vàng) | 0 | 0 | Số hiệu mốc, giá trị tọa độ X, Y, H |
| **10** | **Ranh giới thửa đất hiện trạng** | **0 (Trắng/Đen)** | **0 (Liền)** | **0 hoặc 1** | **Bờ thửa, ranh giới khép kín liên tục** |
| **11** | **Điểm nhãn thửa (Tâm thửa)** | **4 (Vàng)** | **0** | **0** | **Điểm tâm hình học hoặc cell nhãn thửa** |
| **13** | **Số thứ tự thửa & đường kẻ nhãn** | **4 (Vàng)** | **0** | **0** | **Số thứ tự thửa đất trên gạch ngang nhãn** |
| **14** | Tường nhà, ranh giới nhà | 0 (Trắng/Đen) | 2 (Nét đứt) | 0 | Nếu trùng ranh thửa đất thì vẽ nét liền ranh thửa |
| **15** | Nhãn nhà, kết cấu xây dựng | 4 (Vàng) | 0 | 0 | Ví dụ: `b2` (bê tông 2 tầng), `g1` (gạch 1 tầng) |
| **20** | Tim đường giao thông, đường sắt | 1 (Xanh lơ) | 4 (Chấm gạch) | 0 | Trục giao thông chính, tim đường |
| **21** | Mép đường, lòng đường giao thông | 1 (Xanh lơ) | 0 (Liền) | 0 | Mép đường nhựa, bê tông, đường rải cấp phối |
| **22** | Vỉa hè, rãnh thoát nước đường bộ | 1 (Xanh lơ) | 2 (Nét đứt) | 0 | Bó vỉa, rãnh thoát nước dọc đường |
| **23** | Cầu cống giao thông | 1 (Xanh lơ) | 0 (Liền) | 1 | Mố cầu, cống chui, bản mặt cầu |
| **28** | Địa danh giao thông, tên đường | 1 (Xanh lơ) | 0 | 0 | Tên đường phố, Quốc lộ, Tỉnh lộ, ngõ hẻm |
| **30** | Thủy hệ - Đường mép nước | 2 (Xanh lá) | 0 (Liền) | 0 | Mép nước thực tế sông, hồ, ao, đầm |
| **31** | Thủy hệ - Ranh thửa mặt nước | 2 (Xanh lá) | 0 (Liền) | 0 | Bờ sông hồ thuộc ranh giới quản lý sử dụng |
| **32** | Kênh mương tưới tiêu thủy lợi | 2 (Xanh lá) | 0 (Liền) | 0 | Kênh mương máng nội đồng, rãnh thủy lợi |
| **33** | Đê điều, kè bảo vệ bờ sông hồ | 0 (Trắng/Đen) | 0 (Liền) | 1 | Chân đê, đỉnh đê, kè bê tông/đá |
| **39** | Địa danh thủy hệ, tên sông hồ | 2 (Xanh lá) | 0 | 0 | Tên sông, suối, hồ, đầm, kênh chính |
| **40** | Địa giới quốc gia | 0 (Trắng/Đen) | 4 | 3 | Đường biên giới và mốc quốc giới |
| **42** | Địa giới tỉnh, TP trực thuộc TW | 0 (Trắng/Đen) | 4 | 2 | Đường địa giới cấp tỉnh |
| **44** | Địa giới cấp huyện/thị xã | 0 (Trắng/Đen) | 4 | 1 | Đường địa giới cấp huyện (TT 23/2025) |
| **46** | Địa giới xã, phường, thị trấn | 0 (Trắng/Đen) | 4 | 1 | Đường địa giới hành chính cấp xã |
| **50** | Chỉ giới quy hoạch, hành lang an toàn | 3 (Đỏ) | 3 | 1 | Chỉ giới đường đỏ, hành lang lưới điện, đê |
| **51** | Mốc quy hoạch, mốc giải phóng MB | 3 (Đỏ) | 0 | 1 | Cọc mốc quy hoạch, mốc GPMB |
| **61** | **Ranh giới thửa đất theo pháp lý** | **3 (Đỏ)** | **0 (Liền)** | **1** | **Ranh đất theo GCN (sổ đỏ) biến động** |
| **63** | **Khung bản đồ, lưới km, bảng chắp** | **0 (Trắng/Đen)** | **0** | **0 / 1** | **Khung trong, khung ngoài, góc lưới km** |

---

## 3. Quy cách Thể hiện Nhãn Thửa Đất (Điều 13 & Phụ lục 22)

Nhãn thửa đất là trung tâm thông tin của từng thửa đất trên bản đồ địa chính. Cấu trúc nhãn thửa chuẩn như sau:

```
         Số thứ tự thửa (Level 13)
        ────────────────────────────  (Đường gạch ngang, Level 13)
            Diện tích (Level 4)

             Loại đất (Level 2)
```

### Các nguyên tắc bắt buộc:
1. **Vị trí**: Đặt tại tâm hình học của thửa đất (`Level 11`). Nếu thửa đất quá hẹp không đủ chỗ đặt nhãn, kéo mũi tên chỉ dẫn ra ngoài vùng trống gần nhất.
2. **Số thứ tự thửa đất (`Level 13`)**:
   - Dùng chữ số Ả Rập từ 1 đến hết trong phạm vi mảnh bản đồ hoặc đơn vị đo đạc.
   - Nguyên tắc đánh số: Bắt đầu từ cực Bắc (góc trên cùng bên trái), dích dắc từ Tây sang Đông và từ Bắc xuống Nam.
   - Thửa đất mới tách ra trong quá trình biến động: Giữ nguyên số thửa cũ và thêm số phụ hoặc đánh số tiếp theo số thửa lớn nhất của tờ bản đồ (theo TT 23/2025).
3. **Đường kẻ ngang phân số (`Level 13`)**: Nét liền, độ dài vừa vặn ôm trọn số thửa hoặc số diện tích (chọn số dài hơn).
4. **Diện tích thửa đất (`Level 4`)**:
   - Đơn vị tính: Mét vuông ($m^2$).
   - Làm tròn: Đối với bản đồ tỷ lệ 1:500, 1:1000, 1:2000, diện tích làm tròn đến **1 chữ số thập phân** (ví dụ: `156.4`).
5. **Loại đất hiện trạng (`Level 2`)**:
   - Viết hoa theo đúng bảng mã danh mục phân loại đất của Luật Đất đai 2024:
     - Đất ở: `ODT` (đô thị), `ONT` (nông thôn).
     - Đất nông nghiệp: `LUC` (trồng lúa), `CLN` (cây lâu năm), `HNK` (hàng năm khác), `RSX` (rừng sản xuất), `RPH` (rừng phòng hộ), `NTS` (nuôi trồng thủy sản).
     - Đất phi nông nghiệp: `TSC` (trụ sở cơ quan), `TMD` (thương mại dịch vụ), `SKC` (cơ sở sản xuất phi nông nghiệp), `DGT` (giao thông), `DTL` (thủy lợi)...

---

## 4. Bảng Quy chuẩn Mã Màu MicroStation V8i

MicroStation V8i sử dụng bảng màu chuẩn (Standard Color Table):
- **Color 0** (`White/Black`): Ranh đất hiện trạng (Level 10), nhà (Level 14), đê điều, khung bản đồ.
- **Color 1** (`Blue/Cyan`): Giao thông, chỉ giới đường, vỉa hè (Level 20, 21, 22).
- **Color 2** (`Green`): Thủy hệ sông hồ kênh rạch, tên sông (Level 30, 31, 32, 39).
- **Color 3** (`Red`): Ranh đất pháp lý biến động (Level 61), ranh quy hoạch (Level 50).
- **Color 4** (`Yellow`): Nhãn thửa, số thửa, diện tích, loại đất (Level 2, 4, 11, 13).
- **Color 6** (`Brown/Orange`): Đường đẳng cao, độ cao, ghi chú bình độ (Level 1, 3).

---

## 5. Quy trình Vận hành MCP MicroStation AI

> [!CAUTION]
> **BẮT BUỘC DÙNG MCP TOOL - TUYỆT ĐỐI CẤM CHẠY SCRIPT PYTHON QUA TERMINAL**:
> - **TUYỆT ĐỐI KHÔNG ĐƯỢC** tự viết mã Python (`python -c "import win32com.client..."`) hoặc chạy script PowerShell để can thiệp vào MicroStation qua lệnh dòng lệnh / terminal.
> - **BẮT BUỘC 100%** phải sử dụng các công cụ MCP chuyên dụng có sẵn của server `microstation-v8i` (hoặc `call_mcp_tool`). Các công cụ này đã được đóng gói và tối ưu tốc độ 0.05ms qua Native C++ DLL/Pipe.

Khi người dùng yêu cầu vẽ hoặc biên tập bản đồ địa chính:

1. **Vẽ Thửa Đất Nhanh Trọn Gói**:
   - Sử dụng công cụ `cad_draw_workflow` để thiết lập Level, Color, Weight và vẽ đường bao thửa đất, sau đó tự động Fit View trong một lệnh duy nhất.
   - Ví dụ vẽ thửa đất:
     ```json
     {
       "level": 10,
       "color": 0,
       "weight": 1,
       "style": 0,
       "elements": [
         {
           "type": "shape",
           "points": [
             [586100.25, 2321450.10],
             [586120.50, 2321455.30],
             [586118.00, 2321420.00],
             [586095.00, 2321415.80],
             [586100.25, 2321450.10]
           ]
         }
       ],
       "fit_view": true
     }
     ```

2. **Tạo Nhãn Thửa Đất (Gộp 1 Bước)**:
   - Sử dụng `cad_draw_workflow` để vẽ điểm tâm (`Level 11`), gạch ngang (`Level 13`), số thửa (`Level 13`), diện tích (`Level 4`), loại đất (`Level 2`).
   ```json
   {
     "level": 13,
     "color": 4,
     "weight": 0,
     "style": 0,
     "elements": [
       {"type": "point", "x": 586108.0, "y": 2321435.0},
       {"type": "text", "text": "25", "origin": [586108.0, 2321437.0], "height": 1.5, "width": 1.5},
       {"type": "line", "start": [586105.0, 2321435.0], "end": [586111.0, 2321435.0]},
       {"type": "text", "text": "245.8", "origin": [586108.0, 2321433.0], "height": 1.5, "width": 1.5},
       {"type": "text", "text": "ODT", "origin": [586108.0, 2321430.5], "height": 1.5, "width": 1.5}
     ],
     "fit_view": false
   }
   ```

3. **Kiểm tra và Báo cáo Trích lục Địa chính**:
   - Sử dụng `measure_area` để kiểm tra diện tích chính xác của thửa đất khép kín.
   - Sử dụng `scan_elements` theo Level 10 để đếm số lượng thửa đất trong tờ bản đồ.
   - Khi phát hiện ranh đất bị hở (không khép kín), thông báo cho người dùng vị trí tọa độ hở và đề xuất dùng `extend_to_intersection` hoặc nối điểm để tạo shape khép kín hoàn chỉnh.

---

## 6. Quy trình Tự Động khi Nhận Yêu Cầu "Số Hóa" từ Ảnh

Khi người dùng gửi ảnh hoặc yêu cầu **"số hóa"**, **"số hóa ảnh"**, **"chuyển ảnh sang CAD"**, **"vẽ từ ảnh"**:
AI Agent **BẮT BUỘC** tự động kích hoạt quy trình 4 bước chuẩn hóa sau:

### Bước 1: Phân tích & Trích xuất Dữ liệu Kỹ thuật từ Ảnh (OCR)
AI tự động phân tích ảnh theo thứ tự ưu tiên:
1. **Ưu tiên 1 (Có Bảng tọa độ góc ranh)**:
   - Trích xuất toàn bộ bảng tọa độ các đỉnh: Điểm 1, 2, 3... với tọa độ $X, Y$ (hệ VN-2000).
   - Đọc các thông tin: Số thửa, Diện tích ($m^2$), Loại đất, Địa chỉ, Chỉ giới quy hoạch.
2. **Ưu tiên 2 (Không có bảng tọa độ, chỉ có Kích thước cạnh & góc)**:
   - Đọc chiều dài từng cạnh (ví dụ: $5.0m$, $18.2m$, $20.0m...$), góc vuông, khoảng lùi, tim đường.
3. **Ưu tiên 3 (Ảnh sơ đồ tổng thể)**:
   - Đọc tỷ lệ bản đồ (1:500, 1:1000, 1:2000) và lưới kilômét (nếu có).

### Bước 2: Chèn Ảnh làm Nền Tham Chiếu Raster (`attach_raster_image`)
- Gọi MCP tool `attach_raster_image` để chèn trực tiếp file ảnh vào nền bản vẽ MicroStation.
- Định vị ảnh tại tọa độ thực tế hoặc gốc tọa độ để làm lớp tham chiếu kiểm chứng trực quan.

### Bước 3: Dựng Hình học Vector Chuẩn Xác (Không Đoán Mò)
- Tuyệt đối không ước lượng pixel bằng mắt thường.
- Dùng `cad_draw_workflow` để:
  - Nếu có tọa độ X, Y: Dựng Shape đường bao thửa đất theo đúng tọa độ thực tế tại `Level 10`, Color 0, Weight 1.
  - Nếu có kích thước cạnh: Dựng đa giác khép kín theo đúng chiều dài từng cạnh.
  - Tạo nhãn thửa chuẩn phân số $\frac{\text{Số thứ tự thửa}}{\text{Diện tích}}$ và dòng dưới `Loại đất` tại tâm thửa (`Level 11`, `Level 13`, `Level 4`, `Level 2`).

### Bước 4: Kiểm Tra Đối Soát & Fit View
- Dùng `measure_area` tính diện tích thửa đất vừa dựng.
- Đối chiếu diện tích tính toán với diện tích ghi trên ảnh gốc và báo cáo kết quả cho người dùng.
- Tự động gọi `fit_view` để hiển thị toàn bộ thửa đất vector đè lên ảnh raster nền.

