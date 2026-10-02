# 二流文科生的二手文献引用助手

**Secondary-source citation → Chinese primary-source evidence, with the page image to prove it.**

You paste a quotation or paraphrase from secondary literature (or upload the page),
add whatever half-remembered clues you have, and point it at a local primary source.
It returns candidate passages from the actual Chinese text, highlighted on the
original page image, with the PDF page and a copyable citation — and it says
"I can't verify this from your current sources" instead of inventing an answer.

Status: **MVP candidate** — runnable and tested, not yet an accepted MVP.
Final acceptance belongs to review plus the owner's milestone decision.

---

## Why it exists

追踪二手文献里的一句引用，通常意味着在几百页的扫描本里反复翻页、比对措辞、再回头确认页码。
这个工具把这段体力活压缩成一次检索，而且**只把能找到原件的那部分当成证据**：

- 二手文献里的引用、转述、脚注，以及你自己的记忆，都是**可能出错的线索**；
- 只有一手文献的**原页文本和原页图像**才算证据；
- 找不到就如实说找不到，绝不为了给出答案而编造匹配、页码或引文。

Weber 是评测集，不是产品白名单：产品与作者、学科无关，覆盖范围取决于当前可访问的资料源。

## What you get back

对每条候选段落：

- 可复制的**中文原文**；
- **原页截图 + 高亮**（坐标来自文本层或 OCR，不是猜的）；
- **PDF 顺序页**；印刷页码只有在真的确认时才显示；
- 已知的书目信息（只显示确认过的字段，缺什么就报缺什么）；
- 可复制的**脚注**与**参考文献**基础格式；
- 明确的未确认字段与警告。

结果状态从不合并成一个笼统的"未找到"：

| 状态 | 含义 |
| --- | --- |
| 可靠证据已找到 | 已定位到原页并生成高亮 |
| 有多个可能对应的段落 | 相关度接近，并列展示，不强制选唯一答案 |
| 未找到可靠的对应段落 | 来源可以检索，但没有能定位的段落 |
| 当前资料源不足以核验 | 例如扫描本既没有文本层也没有 OCR 缓存 |

## How it works

```
二手文献文本 / PDF / 照片  (+ 可选线索)
        ├── 粘贴文本 ─────────────┐
        ├── 二手 PDF → 文本层 ─────┼─→ 确认 / 编辑要检索的文本
        └── 图片 → RapidOCR ──────┘
                                     │
一手文献来源 ─→ 能不能检索？ ─→ 文本层路径（默认）/ RapidOCR 扫描路径
                                     │
   upstream chunker → 本地向量检索（0 次付费调用）→ 原页定位与高亮 → 结果与状态
```

复用的是成熟组件，而不是自建 RAG：PaperQA2 的分块与检索入口、`paper-qa-pypdf` 解析、
`pypdfium2` / `Pillow` 的原页几何与高亮，以及 RapidOCR（ONNX 推理，模型随 wheel 提供）。

## Setup

Windows / CPython 3.11（验证版本 3.11.9）：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- 精确环境导出（验证机的完整 `pip freeze`）：`requirements.freeze.txt`
- 可选 OCR 依赖（`rapidocr` / `onnxruntime`）已列在 `requirements.txt` 中；只处理文本层 PDF 时用不到。
- 本地嵌入模型 `BAAI/bge-small-zh-v1.5`：首次使用需要访问 Hugging Face；若本机已有缓存，
  程序默认以离线模式运行。要允许首次下载：

```powershell
$env:MVP_ALLOW_MODEL_DOWNLOAD = "1"
```

### One canonical launch command

```powershell
$env:PQA_HOME = $PWD
.\.venv\Scripts\python.exe tools\mvp_app.py
```

然后在浏览器打开 <http://127.0.0.1:8765>。只监听本机地址，没有账号体系，不上传任何内容。

无界面单次运行：

```powershell
$env:PQA_HOME = $PWD
.\.venv\Scripts\python.exe tools\mvp_app.py --run-once `
  --secondary-text "在《理想国》第十卷，苏格拉底竟扬言要将诗歌逐出城邦（605B、607B）。" `
  --hints "Stephanus 605B / 607B" `
  --source T005B-01
```

## Preparing your own primary source

一手文献全文不能进仓库（版权与隐私），所以它们放在被 Git 忽略的 `data/private/` 下，
`tools/mvp_sources.json` 只记录**路径与人工确认过的书目元数据**：

1. 把 PDF 放到一个稳定的本地路径（例如 `data/private/<你的书>/source.pdf`）；
2. 写一个元数据 JSON（字段见 `tools/mvp_sources.json` 的示例；`metadata_origin` 要说明来源）；
3. 在 `tools/mvp_sources.json` 的 `sources` 里加一条记录；
4. 重启应用，下拉框里就会出现这本书。

如果来源是**扫描本**（没有文本层），先跑一次 OCR 缓存（可选、显式的一步，不会自动发生）：

```powershell
.\.venv\Scripts\python.exe tools\t006_ocr_evidence.py `
  --pdf data/private/<你的书>/source.pdf `
  --cache-dir data/private/<你的书>/ocr/rapidocr --dpi 300
```

OCR 结果会被明确标注为"机器识别文本"，必须在结果页与页面图像核对；本产品不公布字符准确率。

也可以直接在网页表单里填写"本地 PDF 路径 + 元数据 JSON 路径"，不必修改注册表。

## Verification

```powershell
$env:PQA_HOME = $PWD
.\.venv\Scripts\python.exe tools\mvp_probes.py            # 产品入口探针（0 模型调用 / $0.00）
.\.venv\Scripts\python.exe tools\t003_regression_probes.py
.\.venv\Scripts\python.exe tools\t004_regression_probes.py
.\.venv\Scripts\python.exe tools\t006_ocr_probes.py
```

`tools/mvp_probes.py` 用**合成 PDF** 覆盖两条路径与诚实失败路径，因此不需要私有材料也能跑通：
文本层 PDF 能定位并生成高亮；纯图像 PDF 在没有 OCR 缓存时如实返回 `insufficient_source`。

## Repository map

| 路径 | 作用 |
| --- | --- |
| `tools/mvp_app.py` | 产品入口：本地网页界面 + 无界面单次运行 |
| `tools/mvp_pipeline.py` | 规范化后端流程：选路径 → 分块 → 检索 → 证据 → 状态 |
| `tools/mvp_sources.json` | 本地一手文献注册表（只有路径与元数据） |
| `tools/mvp_probes.py` | 零成本产品探针（含合成 PDF 端到端用例） |
| `tools/t003_evidence_localize.py` | 原页几何定位、高亮与状态机 |
| `tools/t004_backend_slice.py` | 证据对象与引用拼装（只用确认过的元数据） |
| `tools/t006_ocr_evidence.py` | RapidOCR 适配层 + 可续跑的分页 OCR 缓存 |
| `ops/` | 项目状态、决策、运行日志与报告（本仓库的状态总线） |

## Honest limits

- 不做万能文献获取：能核验什么取决于你能提供的资料源；缺来源是合法的失败状态。
- 不做长期解释性论述（是否曲解、夸大、漏掉限定语），需要时再按需展开。
- 扫描本的 OCR 文本不是出版社文本层；在人工认证转录之前，不给出准确率数字。
- 排序是检索判断，不是证据；相关度接近时并列展示，由你判断。
- 不写论文、不做文献综述、不做知识库。

## Data

代码与文档可以公开分享；`data/private/` 下的原文、页面图像与 OCR 文本都不进入仓库。
书目信息以各自来源为准。
