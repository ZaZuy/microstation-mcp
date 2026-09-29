# QUY TẮC KỸ THUẬT ĐO ĐẠC VÀ BIÊN TẬP BẢN ĐỒ ĐỊA CHÍNH VIỆT NAM (MICROSTATION V8i)

Khi người dùng yêu cầu đo đạc, vẽ, biên tập thửa đất, phân lớp level, tạo nhãn thửa, trích lục địa chính, tính diện tích hoặc kiểm tra ranh giới thửa đất trên MicroStation V8i:

### 1. Căn cứ Pháp lý & Tiêu chuẩn Kỹ thuật bắt buộc

- **Thông tư số 26/2024/TT-BTNMT** ngày 26/11/2024 của Bộ Tài nguyên và Môi trường.
- **Thông tư số 23/2025/TT-BNNMT** ngày 20/06/2025 (sửa đổi, bổ sung TT 26/2024/TT-BTNMT và Văn bản hợp nhất số 34/VBHN-BNNMT).
- **Luật Đất đai năm 2024** (Luật số 31/2024/QH15).

### 2. Hệ Tọa độ & Đơn vị Thiết kế (Điều 3)

- Hệ quy chiếu quốc gia **VN-2000**, phép chiếu hình trụ ngang đồng góc, múi chiếu **3°**, hệ số co giãn chiều dài **k₀ = 0.9999**.
- Kinh tuyến trục theo từng tỉnh/thành phố quy định tại **Phụ lục 01** của Thông tư 26/2024 (và TT 23/2025).
- **MicroStation Working Units**:
  - Master Unit = Mét (`m`)
  - Sub Unit = Milimét (`mm`)
  - Resolution = 1000
- **Global Origin**: X = 500.000 m, Y = 1.000.000 m.

### 3. Bảng Phân lớp Level Bắt buộc (Phụ lục 21 TT 26/2024)

#### 3.1. Nhóm Địa hình
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 1 | Đường bình độ cơ bản, bình độ cái, nửa khoảng cao đều | 6 (Nâu) | 0 hoặc 1 | Độ cao |
| 3 | Ghi chú độ cao, ghi chú bình độ | 6 (Nâu) | 0 | |
| 5 | Tỷ sâu, tỷ cao | 6 | 0 | |

#### 3.2. Nhóm Điểm khống chế trắc địa
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 6 | Điểm thiên văn, điểm tọa độ Quốc gia, điểm độ cao Quốc gia | 0 | 0 | Số hiệu, độ cao |
| 7 | Điểm độ cao kỹ thuật | 0 | 0 | |
| 8 | Điểm địa chính, điểm khống chế đo vẽ, điểm trạm đo | 0 | 0 | |
| 9 | Ghi chú số hiệu điểm, độ cao | 4 | 0 | |

#### 3.3. Nhóm Thửa đất (quan trọng nhất)
| Level | Đối tượng | Color | Weight | Style | Ghi chú |
|-------|-----------|-------|--------|-------|---------|
| **10** | **Ranh giới thửa đất hiện trạng** (bờ thửa, đường bao khép kín liên tục) | **0** (Đen) | 0 hoặc 1 | 0 (nét liền) | Độ rộng bờ thửa |
| **61** | **Ranh giới thửa đất theo pháp lý** (theo GCN / sổ đỏ) | **3** (Đỏ) | 1 | 0 | |
| **11** | **Điểm nhãn thửa (tâm thửa đất)** | **4** (Vàng) | 0 | | Tọa độ tâm thửa |
| **13** | **Số thứ tự thửa đất + gạch ngang phân số** | **4** (Vàng) | 0 | | |
| **4** | **Diện tích thửa đất hiện trạng** (dưới gạch ngang) | **4** (Vàng) | 0 | | Làm tròn 1 chữ số thập phân (m²) |
| **2** | **Loại đất hiện trạng** (ODT, ONT, LUC, CLN, TSC…) | **4** (Vàng) | 0 | | Nằm trong đường bao thửa |
| 12 | Ký hiệu vị trí có độ rộng / ghi chú độ rộng bờ thửa | 4 | 0 | | Bắt điểm đầu/cuối cạnh thửa |
| 29 | Loại đất pháp lý (theo giấy tờ) | 4 | 0 | | |
| 49 | Thông tin lịch sử (loại đất trước chỉnh lý) | 4 | 0 | | |

#### 3.4. Nhóm Nhà, khối nhà
| Level | Đối tượng | Color | Weight | Style | Ghi chú |
|-------|-----------|-------|--------|-------|---------|
| **14** | **Tường nhà, ranh giới nhà** | **0** (Đen) | 0 | **2** (nét đứt) | Nếu trùng ranh thửa → vẽ nét liền Level 10 |
| **15** | **Nhãn nhà** (kết cấu + số tầng: b2, g1, s3…) | **4** (Vàng) | 0 | | b=bê tông, g=gạch, s=sắt thép, go=gỗ, t=tạm |
| 16 | Ký hiệu tường chung/riêng + ghi chú về nhà | 4 | 0 | | |

#### 3.5. Nhóm Giao thông
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 20 | Đường ray (đường sắt) | 1 | 0 | |
| 21 | Chỉ giới đường sắt | 1 | 0 | Là ranh giới thửa |
| 22 | Phần trải mặt, lòng đường, chỗ thay đổi chất liệu | 1 | 0 | |
| 23 | Chỉ giới đường | 1 | 0 | Là ranh giới thửa |
| 24 | Chỉ giới đường nằm trong thửa | 1 | 0 | Không phải ranh thửa |
| 25 | Đường theo nửa tỷ lệ (1 nét) | 1 | 0 | |
| 26 | Ký hiệu độ rộng đường + ghi chú | 1 | 0 | |
| 27 | Cầu | 1 | 0 | |
| 28 | Tên đường, tên phố, tính chất đường | 1 | 0 | |

#### 3.6. Nhóm Thủy hệ
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 30 | Đường mép nước | 2 (Xanh lá) | 0 | Cố định / không cố định |
| 31 | Đường bờ | 2 | 0 | Là ranh giới thửa |
| 32 | Kênh, mương, rãnh thoát nước | 2 | 0 | Là ranh giới thửa |
| 33 | Đường giới hạn thủy văn nằm trong thửa | 2 | 0 | Không tham gia tạo thửa |
| 34 | Suối, kênh nửa tỷ lệ (1 nét) | 2 | 0 | |
| 35 | Ký hiệu độ rộng + hướng dòng chảy | 2 | 0 | |
| 36 | Cống, đập | 2 | 0 | |
| 37 | Đường mặt đê | 0 | 0 | |
| 38 | Đường giới hạn chân đê | 0 | 0 | Là ranh giới thửa |
| 39 | Tên sông, hồ, ao, suối, kênh, mương | 2 | 0 | |

#### 3.7. Nhóm Địa giới hành chính
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 40 | Biên giới quốc gia (xác định / chưa xác định) | 0 | 0 | |
| 41 | Mốc biên giới quốc gia + số hiệu | 0 | 0 | |
| 42 | Địa giới tỉnh (xác định / chưa xác định) | 0 | 0 | |
| 43 | Mốc địa giới tỉnh | 0 | 0 | |
| 44 | Địa giới huyện | 0 | 0 | |
| 45 | Mốc địa giới huyện | 0 | 0 | |
| 46 | Địa giới xã (xác định / chưa xác định) | 0 | 0 | Lưu ý ĐVHC 2 cấp theo TT 23/2025 |
| 47 | Mốc địa giới xã | 0 | 0 | |
| 48 | Tên địa danh, cụm dân cư | 4 | 0 | |

#### 3.8. Nhóm Quy hoạch & Khung
| Level | Đối tượng | Color | Weight | Ghi chú |
|-------|-----------|-------|--------|---------|
| 50 | Chỉ giới đường quy hoạch, hành lang giao thông | **3** (Đỏ) | 0 | |
| 51 | Mốc giới quy hoạch | **3** (Đỏ) | 0 | |
| **63** | **Khung bản đồ, lưới km, bảng chắp 9 mảnh, ghi chú ngoài khung** | **0** | 0 | |

#### 3.9. Các level tùy chọn khác
- Level 17–19: Đối tượng điểm quan trọng (kinh tế, văn hóa, xã hội)
- Level 52–54: Phân vùng địa danh / chất lượng / phân mảnh
- Level 55–59: Cơ sở hạ tầng (điện, nước thải, viễn thông, cấp nước, hành lang lưới điện)

### 4. Bảng Quy chuẩn Màu sắc (Color Code) – theo Phụ lục 22

| Color | Tên màu | RGB chính thức | Sử dụng cho |
|-------|---------|----------------|-------------|
| **0** | Đen / Trắng | 255,255,255 | Ranh thửa hiện trạng (Level 10), tường nhà (Level 14), đê, khung bản đồ, điểm khống chế, địa giới |
| **1** | Xanh lơ | - | Giao thông (Level 20–28) – theo thực tế ngành |
| **2** | Xanh lá | 0,255,0 | Thủy hệ (Level 30–39) |
| **3** | Đỏ | 255,0,0 | Ranh thửa pháp lý (Level 61), chỉ giới quy hoạch (Level 50–51) |
| **4** | Vàng | - | Nhãn thửa, số thửa, diện tích, loại đất, ghi chú điểm (Level 2,4,11,13,15…) |
| **6** | Nâu / Cam | 255,117,0 | Đường bình độ + ghi chú độ cao (Level 1, 3, 5) |

### 5. Quy cách Trình bày Nhãn Thửa Đất (Điều 13 & Phụ lục 22)

- Nhãn thửa có dạng phân số:  
  $$\frac{\text{Số thứ tự thửa}}{\text{Diện tích}}$$  
  và dòng dưới là **Loại đất** (ví dụ: $\frac{25}{245,8}$ và bên dưới `ODT`).
- Đặt tại **tâm thửa đất** (Level 11).
- Số thứ tự thửa nằm **trên** gạch ngang (Level 13).
- Diện tích nằm **dưới** gạch ngang (Level 4), làm tròn **1 chữ số thập phân** (m²).
- Loại đất hiện trạng (Level 2) nằm dưới cùng.
- **Đánh số thứ tự thửa**: Số Ả Rập từ 1 đến hết, từ cực Bắc xuống Nam, dích dắc từ Tây sang Đông.
- Khi tách/hợp thửa có lối đi → thể hiện lối đi riêng.

### 6. Quy tắc Vẽ Ranh giới & Nhà (Phụ lục 22)

- Ranh giới thửa đất **phải khép kín liên tục** (Level 10).
- Khi ranh thửa **trùng** với thủy hệ hoặc đường giao thông → **không vẽ** ranh thửa Level 10, coi đối tượng thủy hệ/giao thông là ranh giới thửa.
- Tường nhà (Level 14) vẽ **nét đứt (Style 2)**.  
  Nếu tường nhà trùng ranh thửa → **chỉ vẽ nét liền Level 10**, không vẽ nét đứt.
- Nhà nhiều tầng có phạm vi khác nhau → thể hiện ký hiệu riêng từng tầng.

### 7. BẮT BUỘC SỬ DỤNG MCP TOOL – TUYỆT ĐỐI CẤM CHẠY SCRIPT PYTHON

- **TUYỆT ĐỐI KHÔNG ĐƯỢC** tự ý viết script Python, lệnh `python -c ...`, hoặc script PowerShell qua terminal để gọi COM `win32com.client` kết nối MicroStation.
- **BẮT BUỘC 100%** phải sử dụng các công cụ có sẵn của MCP Server `microstation-v8i`.
- **Ưu tiên hàng đầu**: Sử dụng công cụ trọn gói `cad_draw_workflow` để thiết lập Level/Color/Weight + vẽ Shape/Line/Text + Fit View trong 1 lượt gọi duy nhất.
- Luôn kiểm tra tính **khép kín** của thửa đất bằng `measure_area`. Nếu không khép kín → cảnh báo ngay cho người dùng.

### 8. Quy tắc Tự động khi Nhận Yêu cầu "Số Hóa" từ Ảnh

Khi người dùng gửi ảnh và yêu cầu *"số hóa"*, *"chuyển ảnh thành CAD"*, *"vẽ từ ảnh"*:

1. **Đọc dữ liệu kỹ thuật từ ảnh (OCR)**: Ưu tiên đọc Bảng tọa độ góc ranh (X, Y VN-2000), hoặc đọc chính xác chiều dài các cạnh và góc. Tuyệt đối không ước lượng pixel bằng mắt.
2. **Chèn ảnh nền raster**: Gọi `attach_raster_image` chèn file ảnh vào MicroStation làm lớp nền đối soát.
3. **Vẽ vector chính xác**: Gọi `cad_draw_workflow` dựng thửa đất theo tọa độ/kích thước đã đọc, gán đúng:
   - Level 10 (ranh thửa hiện trạng)
   - Level 11, 13, 4, 2 (nhãn thửa đầy đủ)
4. **Đối soát & Fit view**: Gọi `measure_area` đo diện tích hình vừa dựng, so sánh với diện tích trên ảnh và gọi `fit_view`.

### 9. Các quy định bổ sung quan trọng khác

- Sai số vị trí điểm trên ranh giới thửa so với điểm khống chế gần nhất không được vượt quá giới hạn theo tỷ lệ bản đồ (Điều 8).
- Khung bản đồ và lưới km phải tuân thủ Điều 4 và mẫu tại Phụ lục 22.
- Khi biên tập phải đảm bảo thứ tự ưu tiên thể hiện: ký hiệu dạng điểm → nhãn thửa → các yếu tố khác.

### 10. QUY TẮC BẮT BUỘC: VỪA CODE VỪA TEST THỰC ĐỊA (VERIFICATION-FIRST)

**TUYỆT ĐỐI KHÔNG ĐOÁN MÒ HOẶC BÀN GIAO KHI CHƯA CHẠY KIỂM THỬ TRỰC TIẾP TRÊN DỮ LIỆU THẬT.**

Mọi thao tác tạo công cụ, viết addon WinForms, trích xuất dữ liệu hoặc vẽ CAD bắt buộc phải tuân theo chu trình kiểm thử:
1. **Kiểm tra kết nối và nhận diện file DGN**: Chạy thử hàm đọc trạng thái file (`GetCurrentFileState` hoặc `get_drawing_info`). Bắt buộc phải xác nhận đúng tên file DGN đang mở trước khi thao tác.
2. **Kiểm thử logic bằng lệnh chạy thực tế (`dotnet run -- --test` hoặc gọi MCP tool)**: Phải chạy thực tế và in ra màn hình các thông số (Số thửa, Tờ BĐ, Diện tích, Danh sách tọa độ đỉnh X/Y, Chiều dài cạnh). So sánh đối chiếu với dữ liệu thật, nếu sai lệch phải debug sửa ngay lập tức trước khi thông báo cho người dùng.
3. **Kiểm tra tính khép kín & diện tích**: Luôn gọi hàm tính diện tích/chu vi, đảm bảo đỉnh khép góc trùng khớp đỉnh đầu tiên (sai số $\le 0.001\text{m}$).
4. **Kiểm thử ứng dụng GUI & File EXE sau khi build**:
   - Sau khi biên dịch `dotnet build`, chạy thử tiến trình ứng dụng bằng PowerShell để kiểm tra xem form có nảy lên không, có crash ngầm không (`Responding: True`, không có file lỗi `app_error.txt`).
   - Sau khi `dotnet publish` ra file `.exe` độc lập trong `Publish/`, phải kiểm tra kích thước và tính toàn vẹn của file trước khi bàn giao.