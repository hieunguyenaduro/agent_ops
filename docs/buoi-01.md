# Buổi 1 — AgentOps: Từ nguyên mẫu đến production

> **Học xong buổi này, bạn có thể:** giải thích AgentOps khác MLOps ở đâu,
> tổ chức lại một project agent cho gọn, và tạo một "baseline" đủ rõ để
> biết chính xác phiên bản nào đã tạo ra một câu trả lời.

## 1. Một câu để nhớ

Agent chạy trên laptop giống món ăn bạn nấu ở nhà. Ngon, nhưng chưa phải
nhà hàng: nhà hàng cần bếp đủ chuẩn, thực đơn cố định, kiểm kê nguyên liệu,
nhân viên trực ca, và người chịu trách nhiệm khi khách bị đau bụng.

**AgentOps là toàn bộ phần việc biến món ăn đó thành nhà hàng vận hành được
mỗi ngày** — không phải viết agent giỏi hơn, mà làm cho agent chạy được,
quan sát được, sửa được và tin được khi có nhiều người dùng.

## 2. Vòng đời 10 bước

```text
  ① Prepare ──► ② Serve ──► ③ Containerize ──► ④ Deploy
       ▲                                          │
       │                                          ▼
  ⑩ Operate ◄── ⑨ Run durably ◄── ⑧ Optimize ◄── ⑦ Evaluate ◄── ⑥ Observe
                                                      ▲
                                                      │
                                              ⑤ Automate (CI/CD)
```

Đừng học thuộc. Chỉ cần nhớ **ba câu hỏi** mà mỗi bước trả lời:

| Câu hỏi | Bước nào trả lời |
|---------|------------------|
| "Chạy ở đâu, ai gọi được?" | Serve, Containerize, Deploy |
| "Làm sao biết nó đang làm gì?" | Observe, Evaluate |
| "Làm sao sửa mà không làm hỏng thứ khác?" | Automate, Optimize, Run durably, Operate |

## 3. MLOps và AgentOps khác nhau ở đâu

| | MLOps | AgentOps |
|---|---|---|
| Thứ được triển khai | Một model | Một **hệ thống hành vi**: model + prompt + tool + vòng lặp |
| Output | Xác suất, nhãn, số | Câu trả lời, hành động, lời gọi tool |
| "Đúng" nghĩa là gì | Có nhãn, đo được bằng metric | Thường **không có một đáp án đúng duy nhất** |
| Lỗi đến từ đâu | Dữ liệu, model drift | Model, prompt, tool, retrieval, thời gian chờ, người dùng |
| Chi phí | Tương đối ổn định | **Biến đổi theo hành vi** — agent "nghĩ" càng lâu càng tốn |
| Debug | Xem log + feature | Phải xem **cả một chuỗi quyết định** (trace) |

Điểm cốt lõi: với agent, **cùng một input có thể ra hai output khác nhau**.
Vì vậy "chạy đúng một lần" không chứng minh được gì. Ta cần dữ liệu của
nhiều lần chạy, có nhãn phiên bản, mới so sánh và cải thiện được.

## 4. Chuẩn hóa project

Một cấu trúc đủ tốt cho cả 10 buổi:

```text
agent_ops/
├── docs/                 # bài giảng, quyết định thiết kế
├── labs/
│   ├── common/           # agent lõi, dùng chung
│   └── buoi_02/          # từng buổi một thư mục chạy được
├── requirements.txt      # thư viện, có pin phiên bản
├── .env.example          # mẫu cấu hình, KHÔNG chứa key thật
├── .gitignore            # chặn .env, .venv, dữ liệu sinh ra
└── README.md             # người mới mở repo biết chạy gì trước
```

Ba quy tắc nhỏ nhưng tiết kiệm rất nhiều thời gian:

1. **Một chỗ cho cấu hình.** Không rải `os.getenv` khắp nơi; gom vào
   `labs/common/config.py`.
2. **Một chỗ gọi model.** Mọi lời gọi đi qua `labs/common/llm.py` — đổi
   model, thêm trace, thêm retry chỉ sửa một nơi.
3. **Không commit bí mật.** `.env` nằm trong `.gitignore`; repo chỉ có
   `.env.example`.

### Ví dụ: sai rồi sửa

```python
# ❌ Sai: key nằm trong code, máy nào cũng giống nhau, đổi môi trường
#    phải sửa code và commit lại.
client = OpenAI(api_key="sk-proj-abc123...")
MODEL = "gpt-4.1-mini"
```

```python
# ✅ Đúng: code giống nhau ở mọi nơi, môi trường quyết định giá trị.
#    (Đây là tinh thần 12-factor.)
from labs.common.config import settings

client = OpenAI(api_key=settings.openai_api_key)
model = settings.openai_model
```

## 5. Git/GitHub: workflow tối thiểu

Không cần quy trình nặng. Chỉ cần bốn thứ:

- `main` luôn chạy được. Không push thẳng khi đã có người khác dùng.
- Mỗi thay đổi đi qua một PR nhỏ, có mô tả "đổi gì, vì sao".
- Mỗi lần release đánh tag: `v0.1.0`, `v0.2.0`.
- Commit message nói **hành vi**, không nói file:
  `feat: thêm tool tra cứu đơn hàng` tốt hơn `update agent.py`.

Quy ước version đơn giản:

| Thay đổi | Tăng số nào | Ví dụ |
|---|---|---|
| Sửa lỗi, không đổi hành vi | PATCH | 0.1.0 → 0.1.1 |
| Thêm tính năng tương thích | MINOR | 0.1.1 → 0.2.0 |
| Đổi contract API / phá vỡ | MAJOR | 0.2.0 → 1.0.0 |

## 6. Version cái gì?

Đây là phần dễ sai nhất. Agent có **bốn lớp** có thể thay đổi độc lập:

| Lớp | Ví dụ | Nếu không version |
|---|---|---|
| Code | `agent.py`, `app.py` | Không biết lỗi xuất hiện từ bản nào |
| Prompt | `SYSTEM_PROMPT` | Sửa một câu, chất lượng đổi mà không ai nhớ |
| Model | `gpt-4.1-mini` → model khác | Cost/latency nhảy mà không rõ nguyên nhân |
| Tool | schema, dữ liệu tool trả về | Agent "ngu đi" vì tool trả format mới |

Cách rẻ nhất để gộp cả bốn: một **release fingerprint** — hash ngắn của
model + prompt + danh sách tool. Lab hôm nay tính fingerprint này và ghi
vào `baseline.json`.

> Quy tắc thực dụng: nếu một thay đổi có thể làm câu trả lời khác đi,
> nó phải xuất hiện trong fingerprint hoặc trong tag release.

## 7. Lab — 15 phút

```bash
python -m labs.buoi_01.check_env
python -m labs.buoi_01.baseline_agent
```

`check_env` in ra phiên bản Python, thư viện, trạng thái key và ghi
`baseline.json`. `baseline_agent` chạy agent một lần, in trace URL (nếu
đã cấu hình Langfuse) và lưu lại các bước đã chạy.

Mở trace trên Langfuse, bạn sẽ thấy cây:

```text
agent.support                 (span gốc, 1.2s)
├── tool.lookup_order         (12ms)
└── llm.answer                (1.1s, có token usage + cost)
```

Đây là "bản chụp" để các buổi sau so sánh. Đừng xoá `baseline.json`.

## 8. Bài tập

1. Đổi `OPENAI_MODEL` trong `.env` sang một model khác, chạy lại
   `check_env`. Fingerprint có đổi không? Vì sao?
2. Sửa một câu trong `SYSTEM_PROMPT` ở `labs/common/agent.py`, chạy lại.
   Ghi lại fingerprint mới.
3. Chạy `git init`, commit baseline, rồi tag `v0.1.0`. Đây là mốc để buổi 5
   dựng CI/CD.

## 9. Tự kiểm tra

1. Vì sao "agent chạy đúng trên máy tôi" chưa đủ để deploy?
2. Nêu một thay đổi **không** làm đổi code nhưng vẫn làm chất lượng agent đổi.
3. Nếu chỉ được lưu một thứ để điều tra sự cố, bạn lưu gì? Vì sao?

## 11. Gợi ý lên lớp (45–60 phút)

| Phút | Việc làm |
|---|---|
| 0–5 | Câu hỏi mở: "Agent của bạn chạy tốt ở nhà. Điều gì hỏng đầu tiên khi có 100 người dùng?" |
| 5–15 | Vòng đời 10 bước + bảng MLOps/AgentOps. Không đọc hết bảng — chỉ hỏi khác biệt nào khiến vận hành khó hơn. |
| 15–25 | Cấu trúc project, 12-factor, ví dụ sai/đúng về hardcode key. |
| 25–30 | Version 4 lớp + release fingerprint. Đây là ý quan trọng nhất buổi. |
| 30–45 | Lab: chạy `check_env`, `baseline_agent`, mở trace. Đi từng bàn kiểm tra `.env`. |
| 45–55 | Chữa bài: cho một học viên đổi model, so sánh fingerprint. |
| 55–60 | Chốt: "mọi thay đổi có thể làm câu trả lời khác đi đều phải được ghi lại". |

**Câu hỏi để cả lớp tranh luận:** cùng một prompt, cùng một model, chạy hai
lần ra hai câu trả lời khác nhau. Vậy "test pass" nghĩa là gì?
