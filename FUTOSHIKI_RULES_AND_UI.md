# Futoshiki: Luat Choi Va Giao Dien

## 1) Futoshiki la gi?

Futoshiki la mot tro choi logic dang luoi (thuong la `4x4`, `5x5`, `6x6`, ...).  
Muc tieu la dien so vao cac o trong sao cho:

- Moi hang chua du cac so tu `1` den `N`, khong lap.
- Moi cot chua du cac so tu `1` den `N`, khong lap.
- Tat ca dau bat dang thuc giua hai o lien ke (`<`, `>`, hoac dau doc) deu dung.

No co the xem nhu “Latin square + rang buoc bat dang thuc”.

---

## 2) Luat choi co ban

Gia su ban dang choi luoi `N x N`:

1. **Tap gia tri hop le**
   - Moi o chi duoc nhap mot gia tri trong khoang `1..N`.

2. **Rang buoc hang**
   - Trong cung mot hang, khong co 2 o giong nhau.

3. **Rang buoc cot**
   - Trong cung mot cot, khong co 2 o giong nhau.

4. **Rang buoc bat dang thuc**
   - Neu giua 2 o co dau `<`, thi o ben trai nho hon o ben phai.
   - Neu giua 2 o co dau `>`, thi o ben trai lon hon o ben phai.
   - Tuong tu voi dau doc: o tren/duoi phai thoa dung huong dau.

5. **O goi y (given clue)**
   - Cac o de bai cho san khong duoc sua.

---

## 3) Cach suy luan giai Futoshiki

Nguoi choi thuong dung cac ky thuat:

- **Loai tru theo hang/cot**: bo cac gia tri da xuat hien trong hang/cot.
- **Loai tru theo bat dang thuc**: vi du o trai `<` o phai thi o trai khong the la `N`, o phai khong the la `1`.
- **Chan tren/chan duoi**: ket hop nhieu dau bat dang thuc lien tiep de gioi han mien gia tri.
- **Tim o don gia tri**: khi o chi con 1 kha nang thi dien ngay.
- **Kiem tra xung dot som**: neu vua dien so ma vi pham hang/cot/inequality thi quay lai.

---

## 4) Quy uoc ky hieu trong de bai

Trong implementation thong dung (bao gom project nay), quy uoc hay gap:

- `hcons[i][j]` la rang buoc giua `(i,j)` va `(i,j+1)`.
  - `1` nghia la trai `<` phai.
  - `-1` nghia la trai `>` phai.
- `vcons[i][j]` la rang buoc giua `(i,j)` va `(i+1,j)`.
  - `1` nghia la tren `<` duoi.
  - `-1` nghia la tren `>` duoi.

Quy uoc nay can thong nhat giua parser, solver va renderer de tranh “mui ten bi nguoc”.

---

## 5) Nguyen tac giao dien tot cho Futoshiki

Mot giao dien Futoshiki de choi va de debug can co:

1. **Do ro rang uu tien so 1**
   - O, so, va dau rang buoc phai doc duoc ngay khi zoom binh thuong.
   - Mau chu va nen co do tuong phan tot.

2. **Phan biet trang thai o**
   - O clue co style rieng (khong sua duoc).
   - O nguoi dung nhap co style rieng.
   - O xung dot (sai logic) phai bao do ro rang.

3. **Phan hoi tuc thi**
   - Khi nhap so, he thong nen kiem tra conflict ngay.
   - Cac dau rang buoc lien quan nen doi mau khi vi pham.

4. **Nhap lieu linh hoat**
   - Co the ho tro:
     - click de cycle so,
     - hoac selector popup,
     - hoac ban phim.
   - Co bo chon “On click mode” de nguoi choi tuy chon.

5. **Tranh che khuat UI**
   - Dropdown/popup phai duoc ve lop tren cung (z-order cao).
   - Khong de control bi de boi danh sach hoac panel khac.

6. **Thong tin giai bai tach biet**
   - Panel log cho tien trinh solver.
   - Panel metric cho thoi gian, so buoc, tinh hop le.
   - Khong lam roi khu vuc luoi choi.

---

## 6) Checklist nhanh de test UI Futoshiki

- [ ] Nhap mot so sai hang/cot -> o do sang mau conflict.
- [ ] Vi pham bat dang thuc -> mui ten/ky hieu lien quan doi mau conflict.
- [ ] Dropdown On click mo ra khong bi che.
- [ ] O clue khong the sua.
- [ ] Solver mode, Step-by-step, Save van chay dung.
- [ ] Khi doi kich thuoc cua so, cac ky hieu van thang hang va khong vo layout.

---

## 7) Ket luan

Futoshiki de hoc va de choi khi UI the hien dung 3 lop rang buoc:

1. Latin square (hang/cot),
2. Bat dang thuc,
3. Phan hoi conflict truc quan.

Neu 3 lop nay duoc render dung va ro, nguoi choi se giai nhanh hon, it nham hon, va de tin vao ket qua solver hon.
