# QUY TẮC KỸ THUẬT ĐO ĐẠC VÀ BIÊN TẬP BẢN ĐỒ ĐỊA CHÍNH VIỆT NAM (MICROSTATION V8i)

Áp dụng cho mọi tác vụ biên tập, vẽ, chuẩn hóa, phân lớp và xử lý dữ liệu không gian bản đồ địa chính trên nền tảng MicroStation V8i:

## 1. Căn cứ Pháp lý & Tiêu chuẩn Bắt buộc
- **Thông tư số 26/2024/TT-BTNMT** ngày 26/11/2024 của Bộ Tài nguyên và Môi trường: "Quy định kỹ thuật về đo đạc lập bản đồ địa chính".
- **Thông tư số 23/2025/TT-BNNMT** ngày 20/06/2025 của Bộ Nông nghiệp và Môi trường (sửa đổi, bổ sung TT 26/2024/TT-BTNMT và Văn bản hợp nhất số 34/VBHN-BNNMT).
- **Luật Đất đai năm 2024** (Luật số 31/2024/QH15).

## 2. Quy chuẩn Hệ Tọa độ & Đơn vị Thiết kế
- **Hệ quy chiếu**: Quốc gia **VN-2000**, múi chiếu $3^\circ$, hệ số tỷ lệ biến dạng chiều dài $k_0 = 0.9999$.
- **Kinh tuyến trục**: Bắt buộc tra cứu theo đúng tỉnh/thành phố quy định tại Phụ lục 01 Thông tư 26/2024 & Thông tư 23/2025.
- **Working Units MicroStation**: Master Unit = Mét (`m`), Sub Unit = Milimét (`mm`), Resolution = 1000.
- **Tọa độ gốc Global Origin**: $X = 500.000\text{ m}$, $Y = 1.000.000\text{ m}$.

## 3. Bảng Phân lớp Level Đối tượng Bắt buộc (Phụ lục 21)
- **Level 1**: Độ cao (đường bình độ cơ bản, bình độ cái, nửa khoảng cao đều) - Color 6 (Nâu), Style 0/2, Weight 0/1.
- **Level 2**: **Loại đất hiện trạng** (mã loại đất ODT, ONT, LUC, CLN, TSC... trong ranh thửa) - Color 4 (Vàng), Style 0, Weight 0.
- **Level 3**: Ghi chú độ cao, bình độ - Color 6 (Nâu), Style 0, Weight 0.
- **Level 4**: **Diện tích thửa đất hiện trạng** (trong ranh thửa) - Color 4 (Vàng), Style 0, Weight 0.
- **Level 6**: Điểm khống chế trắc địa cơ sở (tọa độ, độ cao nhà nước) - Color 0, Weight 2.
- **Level 7**: Điểm địa chính cơ sở, trạm đo - Color 0, Weight 1.
- **Level 8**: Điểm khống chế đo vẽ - Color 0, Weight 1.
- **Level 9**: Ghi chú điểm trắc địa, địa chính - Color 4, Weight 0.
- **Level 10**: **Ranh giới thửa đất hiện trạng** (bờ thửa, đường bao khép kín liên tục) - Color 0 (Trắng/Đen), Style 0 (Nét liền), Weight 0 hoặc 1.
- **Level 11**: **Điểm nhãn thửa (tâm thửa đất)** - Color 4 (Vàng), Style 0, Weight 0.
- **Level 13**: **Số thứ tự thửa đất hiện trạng & đường kẻ ngang phân số** - Color 4 (Vàng), Style 0, Weight 0.
- **Level 14**: Tường nhà, ranh giới nhà - Color 0, Style 2 (Nét đứt), Weight 0. Nếu trùng ranh thửa đất thì vẽ nét liền ranh thửa.
- **Level 15**: Nhãn nhà, kết cấu xây dựng (ví dụ `b2`, `g1`) - Color 4, Style 0, Weight 0.
- **Level 20**: Tim đường giao thông, đường ray - Color 1 (Xanh lơ), Style 4, Weight 0.
- **Level 21**: Mép đường, lòng đường giao thông - Color 1 (Xanh lơ), Style 0, Weight 0.
- **Level 22**: Vỉa hè, rãnh thoát nước đường bộ - Color 1 (Xanh lơ), Style 2, Weight 0.
- **Level 23**: Cầu cống giao thông - Color 1, Style 0, Weight 1.
- **Level 28**: Địa danh giao thông, tên đường phố, quốc lộ - Color 1, Style 0, Weight 0.
- **Level 30**: Thủy hệ - Đường mép nước sông, suối, hồ, đầm, ao - Color 2 (Xanh lá), Style 0, Weight 0.
- **Level 31**: Thủy hệ - Đường bờ ranh thửa mặt nước - Color 2 (Xanh lá), Style 0, Weight 0.
- **Level 32**: Kênh mương tưới tiêu thủy lợi - Color 2 (Xanh lá), Style 0, Weight 0.
- **Level 33**: Đê điều, kè sông hồ - Color 0, Style 0, Weight 1.
- **Level 39**: Địa danh thủy hệ, tên sông, hồ, suối - Color 2, Style 0, Weight 0.
- **Level 40**: Địa giới quốc gia, mốc quốc giới - Color 0, Style 4, Weight 3.
- **Level 42**: Địa giới cấp tỉnh, TP trực thuộc TW - Color 0, Style 4, Weight 2.
- **Level 44**: Địa giới cấp huyện/thị xã (tuân thủ TT 23/2025 về tinh gọn ĐVHC 2 cấp) - Color 0, Style 4, Weight 1.
- **Level 46**: Địa giới cấp xã, phường, thị trấn - Color 0, Style 4, Weight 1.
- **Level 50**: Chỉ giới quy hoạch, hành lang bảo vệ an toàn công trình - Color 3 (Đỏ), Style 3, Weight 1.
- **Level 51**: Cọc mốc quy hoạch, mốc GPMB - Color 3 (Đỏ), Style 0, Weight 1.
- **Level 61**: **Ranh giới thửa đất theo pháp lý** (ranh cấp GCN / sổ đỏ biến động) - Color 3 (Đỏ), Style 0, Weight 1.
- **Level 63**: **Khung bản đồ, lưới km, bảng chắp 9 mảnh** - Color 0, Style 0, Weight 0 hoặc 1.

## 4. Bảng Quy chuẩn Màu sắc (Color Code MicroStation V8i)
- **Color 0**: Trắng/Đen (Ranh thửa Level 10, nhà Level 14, đê, khung bản đồ).
- **Color 1**: Xanh lơ (Giao thông Level 20, 21, 22, 28).
- **Color 2**: Xanh lá cây (Thủy hệ Level 30, 31, 32, 39).
- **Color 3**: Đỏ (Ranh pháp lý Level 61, ranh quy hoạch Level 50).
- **Color 4**: Vàng (Nhãn thửa, số thửa, diện tích, loại đất, ghi chú điểm).
- **Color 6**: Nâu/Cam (Độ cao, đường bình độ Level 1, 3).

## 5. Quy cách Trình bày Nhãn Thửa Đất (Điều 13 & Phụ lục 22)
- Cấu trúc nhãn thửa chuẩn:
  - Phía trên đường gạch ngang: **Số thứ tự thửa** (`Level 13`).
  - Đường kẻ ngang phân số: `Level 13`.
  - Phía dưới đường gạch ngang: **Diện tích thửa đất** (`Level 4`), làm tròn 1 chữ số thập phân ($m^2$).
  - Dòng dưới cùng: **Loại đất hiện trạng** (`Level 2`), viết hoa (ví dụ: `ODT`, `ONT`, `LUC`, `CLN`).
- Vị trí đặt: Đặt tại tâm hình học thửa đất (`Level 11`).
- Đánh số thứ tự thửa: Số Ả Rập từ 1 đến hết, từ cực Bắc xuống Nam, dích dắc từ Tây sang Đông.

## 6. BẮT BUỘC SỬ DỤNG MCP TOOL - TUYỆT ĐỐI CẤM SCRIPT PYTHON TERMINAL
- **TUYỆT ĐỐI KHÔNG ĐƯỢC** tự viết script Python, lệnh `python -c ...`, hoặc PowerShell qua terminal để gọi `win32com` truy cập MicroStation.
- **BẮT BUỘC 100%** phải gọi công cụ của MCP Server `microstation-v8i` (hoặc qua `call_mcp_tool`).
- Ưu tiên sử dụng tool trọn gói `cad_draw_workflow` để gộp thiết lập Level/Color/Weight + vẽ Shape/Line/Text + Fit View trong 1 lệnh duy nhất.
- Kiểm tra tính khép kín của thửa đất bằng `measure_area`. Nếu không khép kín, cảnh báo ngay và cung cấp tọa độ hở.

## 7. QUY TẮC TỰ ĐỘNG KHI NHẬN YÊU CẦU "SỐ HÓA" TỪ ẢNH
Khi người dùng gửi ảnh và yêu cầu *"số hóa"*, *"chuyển ảnh sang CAD"*, *"vẽ từ ảnh"*:
1. **Trích xuất dữ liệu kỹ thuật từ ảnh (OCR)**:
   - Ưu tiên 1: Đọc Bảng kê tọa độ góc ranh ($X, Y$ hệ VN-2000).
   - Ưu tiên 2: Đọc Kích thước cạnh & góc từ ảnh.
   - Tuyệt đối không ước lượng pixel bằng mắt thường.
2. **Chèn ảnh nền raster**:
   - Gọi `attach_raster_image` đưa file ảnh vào MicroStation làm lớp nền tham chiếu.
3. **Dựng hình vector chuẩn xác**:
   - Dùng `cad_draw_workflow` dựng ranh đất (Level 10) và nhãn thửa (Level 11, 13, 4, 2) theo số liệu thực tế đã đọc.
4. **Đối soát & Fit view**:
   - Dùng `measure_area` tính diện tích hình vừa dựng, đối chiếu với diện tích trên ảnh gốc và gọi `fit_view`.
