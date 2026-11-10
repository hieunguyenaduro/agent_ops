# Buổi 4 — Deploying an Agent to Cloud

> **Học xong buổi này, bạn có thể:** đưa image lên Cloud Run, cấu hình
> secret và quyền tối thiểu, đặt giới hạn scaling để kiểm soát chi phí,
> và rollback khi bản mới có vấn đề.

## 1. Một câu để nhớ

**Deploy không phải "ném code lên mây". Nó là ký một hợp đồng**: image nào,
quyền gì, bao nhiêu bản sao, ai trả tiền, và bằng cách nào quay lại bản cũ.

Nếu không trả lời được câu "rollback bằng lệnh nào?" thì chưa phải deploy,
mới chỉ là đẩy code đi.

## 2. Kiến trúc tối thiểu

```text
Người dùng
    │ HTTPS
    ▼
Cloud Run (support-agent)  ──► Secret Manager   (key, không nằm trong image)
    │        │
    │        ├──► Cloud Logging               (log của service)
    │        └──► Langfuse / OTel             (trace của agent)
    │
    └── image kéo từ Artifact Registry
```

Bốn thành phần, bốn loại sự cố khác nhau:

| Thành phần | Khi hỏng | Dấu hiệu |
|---|---|---|
| Image | Container không start | Revision mới fail health check |
| Secret | Gọi model 401 | Log có lỗi auth, health vẫn ok |
| Quyền (IAM) | Không đọc được secret/registry | Deploy fail hoặc 403 |
| Scaling | Hết instance, request xếp hàng | Latency tăng, 429/503 |

## 3. Cấu hình runtime

Ba biến quan trọng nhất:

```text
PORT            Cloud Run tự đặt (8080); app phải lắng nghe biến này
APP_VERSION     để /healthz trả về đúng bản đang chạy
OPENAI_MODEL    đổi model không cần build lại image
```

Dockerfile của lab đã đọc `PORT`:

```dockerfile
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} ..."]
```

Vì sao có `exec`? Để uvicorn là tiến trình chính, nhận được SIGTERM và tắt
một cách lịch sự — đúng bài học buổi 3.

## 4. Bí mật và danh tính

Hai câu hỏi khác nhau:

- **Bí mật**: giá trị là gì? → Secret Manager, inject lúc chạy.
- **Danh tính**: service được phép làm gì? → service account.

```bash
# Tạo secret (một lần)
printf '%s' "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-

# Cấp quyền đọc cho service account của Cloud Run
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:agent-runtime@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Nguyên tắc: **một service account riêng cho agent, chỉ có quyền nó cần.**
Đừng dùng tài khoản mặc định có quyền Editor cho mọi thứ.

> Nếu key lỡ nằm trong image, đổi key là chưa đủ — image cũ vẫn còn trong
> registry. Phải xoá image và coi như key đã bị lộ.

## 5. Scaling và chi phí

Cloud Run scale theo **số request đồng thời**, không theo CPU:

```text
containerConcurrency = 20   → mỗi instance phục vụ tối đa 20 request cùng lúc
min-instances = 0           → rảnh thì về 0 (rẻ, nhưng cold start)
max-instances = 5           → "phanh" chi phí quan trọng nhất
```

Chi phí xấu hổ nhất trong AgentOps không phải giá token — mà là **một vòng
lặp agent không có giới hạn**, chạy trên 50 instance, trong một buổi tối.

Ba phanh cần đặt ngay từ ngày đầu:

| Phanh | Ở đâu | Chặn điều gì |
|---|---|---|
| `max-instances` | Cloud Run | Số request đồng thời bùng nổ |
| `max_tokens` / timeout | Code agent | Một request chạy mãi |
| Rate limit theo user | API gateway / app | Một người dùng đốt hết quota |

`min-instances = 1` giảm cold start nhưng tính tiền 24/7. Chỉ bật khi đã
đo được cold start ảnh hưởng thật đến người dùng.

## 6. Deploy, revision và rollback

Mỗi lần deploy tạo một **revision bất biến**. Traffic có thể chia giữa các
revision — đây là cách làm blue/green đơn giản nhất:

```bash
# Đưa 10% traffic sang bản mới, quan sát
gcloud run services update-traffic support-agent \
  --region asia-southeast1 \
  --to-revisions support-agent-00005-new=10

# Mọi thứ ổn: chuyển 100%
gcloud run services update-traffic support-agent \
  --region asia-southeast1 \
  --to-revisions support-agent-00005-new=100

# Có sự cố: quay lại bản cũ
gcloud run services update-traffic support-agent \
  --region asia-southeast1 \
  --to-revisions support-agent-00004-old=100
```

Điều kiện để rollback dùng được:

1. Image cũ vẫn còn trong registry.
2. Database thay đổi **tương thích ngược** (không xoá cột ngay).
3. Biến môi trường/secret cũ vẫn còn.
4. Bạn biết revision nào là "tốt" — vì `/healthz` và tag release nói rõ.

## 7. Sau deploy: xác minh, đừng tin

Deploy thành công chỉ nghĩa là container start được. Phải kiểm tra thêm:

```bash
python -m labs.buoi_04.preflight --url https://... --strict
```

Script kiểm tra version, database, và gọi thử một request. Đây là **smoke
test sau deploy** — bước mà nhiều đội bỏ qua rồi phát hiện lỗi từ người dùng.

Ba thứ nên xem trong 5 phút đầu:

| Xem gì | Ở đâu | Ngưỡng gợi ý |
|---|---|---|
| Tỉ lệ lỗi 5xx | Cloud Logging / metrics | > 1% là bất thường |
| Latency p95 | Cloud Run metrics | So với baseline buổi 1 |
| Chi phí token | Langfuse | So với cùng kỳ |

## 8. Lab — 30 phút

Phần chạy được ngay:

```bash
python -m labs.buoi_04.preflight
```

Phần deploy (nếu có tài khoản GCP):

```bash
export PROJECT_ID=...
export APP_VERSION=0.4.0
bash labs/buoi_04/deploy.sh
python -m labs.buoi_04.preflight --url "$(gcloud run services describe support-agent \
  --region asia-southeast1 --format 'value(status.url)')" --strict
```

`service.yaml` là manifest tham khảo nếu muốn quản lý cấu hình bằng GitOps.

## 9. Bài tập

1. Deploy với `max-instances=1`, bắn 20 request đồng thời. Ghi lại p95 và
   số request bị chờ. Giải thích bằng `containerConcurrency`.
2. Đổi `APP_VERSION` nhưng giữ nguyên image tag. `/healthz` báo gì? Vì sao
   đây là lỗi phải chặn ở CI/CD?
3. Xoá một secret rồi restart service. Health check có phát hiện không?
   Nếu không, cần thêm check gì?
4. Chia 10% traffic sang revision mới rồi rollback. Ghi lại đúng hai lệnh.

## 10. Tự kiểm tra

1. Vì sao image phải bất biến và được tag bằng version/git sha?
2. `min-instances=0` tiết kiệm gì và đánh đổi gì?
3. Kể tên ba "phanh" chi phí và chỗ đặt chúng.

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Hỏi: "Deploy xong, làm sao biết nó đúng?" Ghi câu trả lời lên bảng. |
| 5–15 | Kiến trúc 4 thành phần + runtime config. Nhấn mạnh PORT và image tag. |
| 15–25 | Secret Manager + IAM. Kể một câu chuyện key bị bake vào image. |
| 25–35 | Scaling, chi phí, rollback bằng revision. |
| 35–55 | Lab: preflight local; nếu có GCP thì deploy thật, cả lớp cùng xem `/healthz`. |
| 55–60 | Chốt: "không có rollback thì chưa gọi là deploy". |

**Demo gây ấn tượng:** deploy hai revision, chia 50/50 traffic, rồi rollback
trong lúc cả lớp đang gọi API. Mọi người thấy traffic đổi ngay, không cần
build lại.
