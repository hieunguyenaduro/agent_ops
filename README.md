# AgentOps — Từ nguyên mẫu đến production

Bài giảng và lab thực hành cho khóa **AgentOps 10 buổi**.
Mỗi buổi có hai phần:

- `docs/buoi-XX.md` — bài giảng ngắn, tiếng Việt, đọc trước hoặc đọc lại sau buổi học.
- `labs/buoi_XX/` — code chạy được ngay, có README riêng và bài tập.

> Bản đầy đủ: **10 buổi**, từ prototype đến vận hành production.
> Buổi 1–3 dùng chung agent đồ chơi; các buổi sau bọc thêm hạ tầng
> quanh đúng lõi đó — không viết lại agent.

## Bản đồ nội dung

| Buổi | Chủ đề | Bài giảng | Lab |
|------|--------|-----------|-----|
| 1 | AgentOps: từ prototype đến production | [docs/buoi-01.md](docs/buoi-01.md) | [labs/buoi_01](labs/buoi_01) |
| 2 | Serving an Agent with FastAPI | [docs/buoi-02.md](docs/buoi-02.md) | [labs/buoi_02](labs/buoi_02) |
| 3 | Containerizing Agents with Docker | [docs/buoi-03.md](docs/buoi-03.md) | [labs/buoi_03](labs/buoi_03) |
| 4 | Deploy lên Cloud Run | [docs/buoi-04.md](docs/buoi-04.md) | [labs/buoi_04](labs/buoi_04) |
| 5 | CI/CD với GitHub Actions | [docs/buoi-05.md](docs/buoi-05.md) | [labs/buoi_05](labs/buoi_05) |
| 6 | Observability cho agent | [docs/buoi-06.md](docs/buoi-06.md) | [labs/buoi_06](labs/buoi_06) |
| 7 | Continuous Evaluation | [docs/buoi-07.md](docs/buoi-07.md) | [labs/buoi_07](labs/buoi_07) |
| 8 | Cost & Latency Optimization | [docs/buoi-08.md](docs/buoi-08.md) | [labs/buoi_08](labs/buoi_08) |
| 9 | Durable Execution | [docs/buoi-09.md](docs/buoi-09.md) | [labs/buoi_09](labs/buoi_09) |
| 10 | Game Day & Production Readiness | [docs/buoi-10.md](docs/buoi-10.md) | [labs/buoi_10](labs/buoi_10) |

Phụ lục: [Cài Langfuse trong 5 phút](docs/phu-luc-langfuse.md)

## Cài đặt một lần

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # rồi mở .env điền key
```

`.env` cần tối thiểu:

```dotenv
OPENAI_API_KEY=sk-...
```

Muốn thấy trace trên giao diện Langfuse thì điền thêm 3 dòng `LANGFUSE_*`
(xem [phụ lục](docs/phu-luc-langfuse.md)).

## Chạy thử

```bash
# Buổi 1 — kiểm tra môi trường và tạo baseline
python -m labs.buoi_01.check_env
python -m labs.buoi_01.baseline_agent

# Buổi 2 — API + SSE (mở 2 terminal)
uvicorn labs.buoi_02.app:app --reload
python -m labs.buoi_02.client_demo

# Buổi 3 — Docker (cần Docker Desktop đang chạy)
docker compose -f labs/buoi_03/docker-compose.yml up --build
python -m labs.buoi_03.smoke_test

# Buổi 4 — kiểm tra sẵn sàng deploy (không cần GCP)
python -m labs.buoi_04.preflight

# Buổi 5 — chạy đúng những gì CI chạy
bash scripts/ci_local.sh

# Buổi 6 — trace thủ công và truy vết log
python -m labs.buoi_06.trace_manual
python -m labs.buoi_06.correlate_logs

# Buổi 7 — so sánh prompt và quality gate
python -m labs.buoi_07.run_eval
python -m labs.buoi_07.run_eval --gate

# Buổi 8 — đo cost/latency, cache, gọi tool song song
python -m labs.buoi_08.measure
python -m labs.buoi_08.cache_demo
python -m labs.buoi_08.parallel_tools

# Buổi 9 — hàng đợi bền vững: crash, lease, retry
python -m labs.buoi_09.demo

# Buổi 10 — game day: scorecard và diễn tập sự cố
python -m labs.buoi_10.game_day
python -m labs.buoi_10.game_day --drill all
```

Nhớ chạy lệnh từ **thư mục gốc của repo** — các lab được đóng gói thành
package Python, nên dùng `python -m ...` thay vì gọi trực tiếp file `.py`.

## Không có OpenAI key?

Vẫn chạy được. Agent tự chuyển sang chế độ offline: tool tra cứu đơn hàng
vẫn chạy thật, câu trả lời được ghép từ dữ liệu mẫu, trace vẫn được tạo nếu
có key Langfuse. Cách này đủ để học luồng SSE, Docker, eval, hàng đợi và
game day — tất cả lab đều chạy không cần key.

## Kiểm tra toàn bộ

```bash
bash scripts/ci_local.sh        # compile + test + preflight
pytest -q                       # riêng bộ test
```

## Cấu trúc repo

```text
.
├── docs/                  # bài giảng buổi 1–10 + phụ lục Langfuse
├── labs/
│   ├── common/            # agent đồ chơi dùng chung cho mọi buổi
│   ├── buoi_01/           # baseline & versioning
│   ├── buoi_02/           # FastAPI + SSE
│   ├── buoi_03/           # Docker + Docker Compose
│   ├── buoi_04/           # Cloud Run: preflight, manifest, deploy
│   ├── buoi_05/           # CI/CD (workflow ở .github/workflows/)
│   ├── buoi_06/           # observability: trace và log
│   ├── buoi_07/           # evaluation: dataset và quality gate
│   ├── buoi_08/           # cost & latency
│   ├── buoi_09/           # hàng đợi bền vững: store, worker, demo
│   └── buoi_10/           # game day, checklist, runbook
├── tests/                 # test offline cho agent, API, queue
├── scripts/               # ci_local.sh
├── .github/workflows/     # ci.yml, deploy.yml, eval.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Một quy ước nhỏ

- Tên thư mục code dùng dấu gạch dưới (`buoi_02`) để import được bằng Python.
- Tên file bài giảng dùng dấu gạch ngang (`buoi-02.md`) cho dễ đọc.

Cùng một buổi, hai cách đặt tên — không phải lỗi đánh máy.
