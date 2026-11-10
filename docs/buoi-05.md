# Buổi 5 — CI/CD with GitHub Actions

> **Học xong buổi này, bạn có thể:** viết pipeline tự động kiểm tra code,
> đóng gói image và deploy khi có tag; hiểu vì sao test của agent khác test
> thường; và biết rollback bằng một tag cũ.

## 1. Một câu để nhớ

**CI là người gác cổng. CD là băng chuyền.**

Người gác cổng kiểm tra hàng trước khi cho vào. Băng chuyền đưa hàng đã
đạt chuẩn ra cửa hàng — tự động, lặp lại được, không phụ thuộc việc ai đó
nhớ đúng câu lệnh.

Nếu chỉ có một trong hai:

- Có CI, không có CD: kiểm tra tốt nhưng vẫn deploy bằng tay lúc 11 giờ đêm.
- Có CD, không có CI: đưa hàng lỗi ra cửa hàng nhanh hơn.

## 2. Pipeline tối thiểu

```text
push / PR
   │
   ▼
[1] Compile + lint ──► [2] Unit test ──► [3] Contract test API
                                              │
                                              ▼
                                        [4] Build image
                                              │
                              tag v* ────────► [5] Deploy
                                              │
                                              ▼
                                        [6] Smoke test
                                              │
                                        fail ─┴─► dừng + báo
```

Mỗi bước trả lời một câu hỏi khác nhau:

| Bước | Câu hỏi | Nếu bỏ qua |
|---|---|---|
| Compile | Code có chạy được không? | Lỗi cú pháp lên tới production |
| Unit test | Logic có đúng không? | Sửa chỗ này hỏng chỗ kia |
| Contract test | API có giữ đúng hình dạng? | Frontend vỡ khi backend đổi field |
| Build | Image có đóng gói được? | Deploy fail sau 3 phút chờ |
| Smoke test | Bản vừa deploy có sống? | Người dùng phát hiện hộ bạn |

## 3. Test cho agent khác test thường ở đâu

Agent không deterministic. Cùng câu hỏi có thể ra hai câu trả lời. Vì vậy
đừng test bằng cách so khớp nguyên văn.

Bốn mức test, tăng dần độ tốn kém:

| Mức | Test cái gì | Có gọi model? | Chạy khi nào |
|---|---|---|---|
| Unit | Tách mã đơn, chọn tool, format prompt | Không | Mỗi commit |
| Contract | `/healthz`, schema request/response, thứ tự SSE | Không | Mỗi commit |
| Integration | Agent + tool + LLM thật | Có | Trước release |
| Evaluation | Chất lượng câu trả lời trên dataset | Có | Trước release (buổi 7) |

Trong lab, agent có **chế độ offline**: khi thiếu `OPENAI_API_KEY`, tool
vẫn chạy thật nhưng câu trả lời lấy từ mẫu. Nhờ vậy unit test và contract
test chạy được trong CI mà không cần bí mật, không tốn tiền, và không bị
model "trả lời khác hôm qua".

> Quy tắc: **test phần deterministic, đánh giá phần không deterministic.**
> Đừng trộn hai thứ vào một chỗ.

## 4. GitHub Actions trong 5 khái niệm

```text
workflow (1 file yaml)
└── job (chạy trên 1 máy ảo)
    └── step (1 lệnh hoặc 1 action)
```

| Khái niệm | Trong lab |
|---|---|
| `on:` | CI chạy khi push/PR; deploy chạy khi tag `v*` |
| `jobs:` | `test` và `deploy`; deploy `needs: test` |
| `env:` | Biến môi trường, không phải secret |
| `secrets:` | Key, token — GitHub che trong log |
| `environment:` | `production`, có thể bật người duyệt |

Ba thói quen tốt:

1. **Cache dependency** (`cache: pip`) để CI không cài lại từ đầu mỗi lần.
2. **Quyền tối thiểu** (`permissions: contents: read`), chỉ mở `id-token`
   khi cần OIDC.
3. **Không dùng service account key dài hạn.** Dùng Workload Identity
   Federation để GitHub lấy token tạm thời.

## 5. Version và tag: chỗ dễ sai nhất

Image phải **bất biến**. Một tag như `latest` bị ghi đè, nên "bản đang
chạy" không còn xác định được.

```text
✅ support-agent:0.5.0          (semver, do tag git tạo ra)
✅ support-agent:sha-7f3c9a1    (truy vết được commit)
❌ support-agent:latest         (không biết là bản nào)
```

Trong lab, tag git là nguồn duy nhất:

```bash
git tag v0.5.0
git push origin v0.5.0        # deploy.yml chạy
```

Và `APP_VERSION` trong container cũng lấy từ tag. Nhờ vậy:

```text
git tag  →  image tag  →  APP_VERSION  →  /healthz
```

Tất cả khớp nhau. Khi `/healthz` báo `0.5.0`, bạn biết chính xác commit nào
đang chạy.

## 6. Môi trường và phê duyệt

Pipeline trưởng thành có ít nhất hai môi trường:

```text
main ──► staging (deploy tự động, test thoải mái)
              │
              └──► production (cần tag + người duyệt)
```

Đừng để staging và production dùng chung secret hay chung database. Một
lần test sai ở staging không được phép làm bẩn dữ liệu thật.

Với GitHub, `environment: production` có thể bật **required reviewers**:
pipeline dừng lại chờ một người bấm duyệt. Đây là "release approval" của
buổi 10, nhưng ở mức đơn giản nhất.

## 7. Rollback trong CD

Rollback không phải viết code mới. Có ba cách, chọn theo tốc độ:

| Cách | Tốc độ | Khi nào dùng |
|---|---|---|
| Chuyển traffic về revision cũ | Giây | Cloud Run, sự cố đang diễn ra |
| Deploy lại image/tag cũ | 1–3 phút | Cần đúng image cũ trên mọi môi trường |
| Revert commit rồi pipeline chạy lại | 5–10 phút | Sự cố đã ổn, cần sửa gốc |

Điều kiện: image cũ còn trong registry, database tương thích ngược, và
bạn biết tag nào là "tốt". Đây là lý do phải giữ tag release.

## 8. Lab — 30 phút

Chạy đúng bộ kiểm tra CI ngay trên máy:

```bash
bash scripts/ci_local.sh
```

Sau đó:

1. Cố tình làm một test đỏ, chạy lại, xem CI sẽ chặn ở đâu.
2. Đọc `.github/workflows/ci.yml` — chỉ ra bước nào chạy trước, vì sao.
3. Đọc `.github/workflows/deploy.yml` — tìm ba chỗ dùng biến môi trường
   thay vì hardcode.
4. Nếu có repo GitHub: bật branch protection, yêu cầu job `test` phải xanh.

## 9. Bài tập

1. Thêm bước `ruff check .` vào CI. Nếu muốn giữ đơn giản, giải thích vì
   sao `compileall` chưa đủ để bắt lỗi style.
2. Viết một test mới cho trường hợp câu hỏi có mã đơn viết thường (`a1003`).
3. Sửa `deploy.yml` để **không** deploy nếu tag không khớp `APP_VERSION`
   trong `.env.example`. Đây là chốt chặn "deploy nhầm bản".
4. Smoke test sau deploy thất bại. Bạn chọn tự động rollback hay dừng lại
   chờ người quyết định? Viết lý do trong 3 câu.

## 10. Tự kiểm tra

1. Vì sao test agent không nên so khớp nguyên văn câu trả lời?
2. Sự khác nhau giữa `latest` và `0.5.0` khi có sự cố?
3. Kể ba điều kiện để rollback bằng revision cũ hoạt động được.

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Lần cuối bạn deploy bằng tay, bạn quên bước nào?" |
| 5–15 | CI vs CD + pipeline 6 bước. Vẽ lên bảng, đừng chiếu slide. |
| 15–25 | Test cho agent: 4 mức, offline mode, "test deterministic / eval non-deterministic". |
| 25–35 | GitHub Actions: workflow/job/step; tag → image → APP_VERSION. |
| 35–55 | Lab: chạy `ci_local.sh`, làm đỏ một test, sửa lại. |
| 55–60 | Chốt: "nếu rollback không làm được trong 2 phút, pipeline chưa xong". |

**Demo nên làm:** sửa một test cho đỏ, push lên nhánh, mở tab Actions,
cho cả lớp xem job fail và nút merge bị chặn.
