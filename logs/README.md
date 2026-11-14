# logs/

Toàn bộ log thô của nhóm. **Không sửa tay** – mọi bảng trong `analysis/output/` và dashboard đều tính lại được từ đây.
Thư mục này được mount vào hai container tại `/app/logs`.

```
logs/
├── mac/                              ← chạy trên Mac (Docker, PostgreSQL 12.5, shared_buffers 4 GB)
│   ├── postgres/                     PostgreSQL mặc định, 113 câu × 3 lần
│   │   ├── test__postgres__job__fair_*.txt          baseline đo công bằng (cùng phiên với Bao), Thí nghiệm 1
│   │   ├── test__postgres__job__<cấu hình>__interleaved_*.txt   ablation 8.4/8.5 chạy xen kẽ
│   │   └── test__postgres__job__imdb50_*.txt        ablation 8.3 trên IMDB 50%
│   ├── bao/                          Bao, 9 split
│   │   ├── train__bao__job__<split>__*.txt          log train
│   │   ├── test__bao__job__<split>__*.txt           log test (retest_fair = đo lại cùng phiên với PostgreSQL)
│   │   ├── model__bao__job__<split>__*/             model đã train
│   │   └── bao_training_times.csv                   thời gian train từng split
│   ├── exp2/                         Thí nghiệm 2
│   │   ├── exp2_hintsets_job.jsonl                  113 câu × 6 phương án × 3 lần, kèm plan
│   │   └── exp2_explain_job.jsonl                   plan mặc định từ EXPLAIN → 34 đặc trưng
│   └── demo_83/                      2 model Bao (IMDB đầy đủ / IMDB 50%) cho scripts/demo/demo_83.sh
│
└── kaggle/                           ← chạy trên Kaggle (CPU, shared_buffers 8 GB)
    ├── bao/<split>/                  Bao đợt đầu: bao_logs/ (test PostgreSQL + Bao cùng notebook, model, train)
    ├── hybridqo/<split>/             HybridQO đợt đầu (10 epoch): hqo_logs/*query_log.csv, run_mcts__*.out
    ├── hybridqo/wandb_export/        9 split HybridQO đổi sang đúng định dạng log của tác giả
    └── ablation/
        ├── 8_3/lan_dau/, lap1–lap4/  Dữ liệu thay đổi: Bao train trên IMDB đầy đủ và IMDB 50%, test trên cả hai
        ├── 8_4_8_5/lan_dau/          Tắt GEQO, tắt bitmap + TID scan (1 lượt)
        ├── 8_4_8_5/lap_8_luot/       Như trên, 8 lượt xen kẽ (dùng cho dashboard)
        └── 8_6/                      Số lần chạy k (hiệu ứng cache)
```

`<split>` là một trong 9 split của bài báo: `leave_one_out_split_1..3`, `random_split_1..3`, `base_query_split_1..3`.

`logs/bao_server.log` (không đưa lên git) là log lúc chạy của Bao server; các script chỉ đọc vài dòng mới ở cuối để
biết model đã nạp xong, nên file cần có trên máy nhưng nội dung cũ không dùng tới.
