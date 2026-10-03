# PRODUCT_V0_2 — Footnote-first targeted citation tracing

Status: CONFIRMED by user on 2026-10-03.

This supersedes the broader post-MVP identity-resolution / whole-web finder direction for the active product workflow. D019's historical MVP milestone remains accepted; V0.2 is the current product simplification target.

## Product name

二流文科生的二手文献引用助手

## One-sentence definition

用户在阅读二手文献时，把想追溯的一段引用/转述以及对应脚注或尾注交给系统；系统先根据脚注定向识别被引一手作品及其中文出版物，再在可合法访问的资料源中寻找/接收对应 PDF，随后定位中文版正文，返回可复制原文、原页高亮截图、页码和可一键复制的中文引用格式。

## Core user story

真实场景不是“我想全网找某本书”。

真实场景是：

1. 我正在读一篇二手文献；
2. 我看到一处引用或转述，觉得值得用于自己的文章；
3. 我把这段文字复制/截图给系统；
4. 我把对应脚注/尾注也复制/截图给系统；
5. 脚注告诉系统作者、作品、篇名、页码、版本等定向线索；
6. 系统据此识别原作，并判断它在中文出版中对应哪本书/文集/版本；
7. 系统获取或要求用户上传对应中文版 PDF；
8. 系统在 PDF 中定位对应原文；
9. 用户得到：中文版原文 + 原页高亮截图 + 页码 + 一键复制引用。

## Product philosophy

- 核心是 **secondary citation -> footnote-guided primary evidence**。
- 脚注/尾注不是最终证据，但它是首要的“导航信息”，不是泛化的可有可无 hint。
- 不做漫无目的全网检索；联网动作应由脚注/尾注解析出的具体作者/作品/版本线索触发。
- 不要求用户先知道标准中文书名、译名或收录文集。
- 不把“被引篇目”与“中文承载出版物”混为一谈。
- 最终证据永远来自实际中文 PDF 原页，而不是书目 API、模型生成或搜索摘要。
- 找不到对应中文出版物或拿不到可核验 PDF，就明确告诉用户，没有就没有。

## Main inputs

### ① 二手文献中的引用 / 转述

支持：
- 直接粘贴文字；
- 上传/粘贴截图；
- 上传二手文献 PDF 页面。

### ② 对应脚注 / 尾注

这是主导航输入。

支持：
- 直接粘贴脚注/尾注文字；
- 上传/粘贴脚注截图；
- OCR 提取。

系统从中尽量提取：
- 作者；
- 篇名 / 书名；
- 原文标题或缩写；
- 年份；
- 页码；
- 译者；
- 版本 / 出版社；
- 可能的收录文集/卷册；
- DOI / ISBN 等标识符。

缺失或错误都允许；用户可以编辑确认。

### ③ 一手中文版来源

正常用户不应该先选“内置测试源”。

优先顺序：
A. 系统根据脚注定向识别出的中文出版物；
B. 用户已有 PDF -> 直接上传；
C. 用户没有 PDF -> 系统只针对已识别的作品/中文出版物做定向资料源查询；
D. 如果当前可合法访问来源没有 PDF -> 明确告诉用户应寻找/上传哪一版中文出版物。

内置 C04 / T005B 等只保留在开发/演示模式，不出现在普通用户主流程。

## Footnote-guided bibliographic resolution

系统应先回答：

- 二手作者究竟引用的是哪一个“一手作品/篇目”？
- 这个作品是否是整本书、文章、论文、章节或演讲？
- 在中文语境中它通常以什么译名出现？
- 它可能独立出版，也可能收录在哪个中文文集/选集/全集/大部头中？

数据模型至少区分：

- cited work / essay / chapter
- author
- title variants
- Chinese title variants
- containing Chinese publication
- translator
- publisher / year / edition
- cited page clue
- provenance of each bibliographic field

多个合理候选就展示多个，不强迫选唯一答案。

## Targeted network lookup

联网检索只发生在已经有脚注/尾注线索之后。

目标不是搜索“任何可能相关的 PDF”，而是验证：
1. 这个被引作品是否有中文出版；
2. 中文出版物叫什么、由谁翻译、收在哪一卷/哪本书；
3. 当前合法/开放/授权来源是否能提供对应 PDF。

Reuse existing metadata/source adapters where useful. Do not broaden provider coverage without real pilot need.

## PDF acquisition boundary

The product may automatically use lawful/open/authorized full-text PDFs.

It must not integrate automated downloading from unauthorized/pirated repositories or bypass paywalls/DRM/login/borrowing controls.

If a matching Chinese publication is identified but no lawful accessible PDF is available:
- show the exact publication/edition information found;
- ask the user to upload a legally obtained PDF;
- once uploaded, continue automatically.

## Evidence workflow

Once a PDF exists:

secondary quote/paraphrase
+ footnote clues
+ confirmed primary publication
→ text-layer or RapidOCR path
→ retrieval
→ original-page localization
→ highlight
→ evidence object

No new evidence stack.

## Result page

Default result should feel like a citation helper, not a debugging console.

Show:
- “找到的对应中文版原文”
- copyable Chinese original text
- original-page highlighted screenshot
- PDF page / printed page if confirmed
- bibliographic metadata
- one-click copy citation, similar in spirit to CNKI citation controls:
  - footnote/basic note
  - reference-list citation

If multiple candidate passages/editions exist, show compact expandable alternatives.

## Failure states

Distinguish:
1. footnote parsed + Chinese publication identified + passage found;
2. publication identified but several PDF/edition candidates exist;
3. publication identified but no lawful accessible PDF -> ask user upload;
4. bibliographic identity remains ambiguous -> ask user confirm/edit candidate;
5. PDF searchable but no reliable passage found;
6. network/provider unavailable -> retry later, do not say the work does not exist;
7. no Chinese publication found in checked bibliographic sources -> say “当前未找到对应中文出版信息”, not “不存在”.

## Normal UI — keep it simple

Ordinary user view should contain only:

### ① 引用 / 转述
[paste text or upload/screenshot]

### ② 脚注 / 尾注
[paste text or upload/screenshot]

### ③ 一手文献
- [开始识别并查找]
- or [我已有 PDF，直接上传]

Then:
[开始核验]

Move to advanced/developer-only:
- k
- OCR mode controls
- local file path
- metadata JSON path
- internal demo sources
- provider diagnostics
- raw status/debug information

## Explicit non-goals for this MVP

Do not make the normal product into:
- a general academic search engine;
- a general OA discovery portal;
- a bibliography manager;
- an all-provider metadata explorer;
- a knowledge base;
- a full paper-writing assistant.

All infrastructure exists only to serve the one citation-tracing workflow above.
