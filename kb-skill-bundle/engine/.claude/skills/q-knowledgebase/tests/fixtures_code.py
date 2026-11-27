"""Test fixture for Q-KnowledgeBase C1 + E: code parsers, KB -> code links, issue / ID links.

Every name is invented (no real project data).
Usage in a test:  from fixtures_code import populate_code;  populate_code(tmp_root)
"""
import json
import sys
from pathlib import Path

# repository-relative path -> text (C++ / Qt sample app, one C file, one TS file, one Python file)
CODE = {
    "src/app/main.cpp": r"""#include <QApplication>
#include "ui/mainwindow.h"
#include "core/engine.h"
#include "missing.h"

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    MainWindow w;
    w.show();
    return app.exec();
}
""",
    "src/app/core/engine.h": r"""#pragma once
#include <QObject>
#include "util.h"

namespace app {

enum class State { Idle, Running, Failed };

struct Config {
    int retries;
    State initial;
};

template <typename T>
class Buffer {
public:
    void push(const T &value);
};

class Engine : public QObject
{
    Q_OBJECT
public:
    explicit Engine(QObject *parent = nullptr);
    void start(const Config &config);
    State state() const;
};

int computeScore(int a,
                 int b);

} // namespace app
""",
    "src/app/core/engine.cpp": r"""#include "engine.h"
#include <QDebug>
// #include "commented_line.h"
/* #include "commented_block.h" */
#if 0
#include "disabled.h"
#endif

namespace app {

Engine::Engine(QObject *parent) : QObject(parent) {}

void Engine::start(const Config &config)
{
    qDebug() << config.retries;
}

State Engine::state() const { return State::Idle; }

int computeScore(int a,
                 int b)
{
    return a + b;
}

} // namespace app
""",
    "src/app/core/util.h": r"""#pragma once

namespace app {

inline int clampValue(int v, int lo, int hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

#define MAKE_ADDER(name, n) int name(int x) { return x + n; }
MAKE_ADDER(addTwo, 2)

} // namespace app
""",
    "src/app/ui/mainwindow.h": r"""#pragma once
#include <QWidget>

class MainWindow : public QWidget
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
signals:
    void closed();
};
""",
    "src/app/ui/mainwindow.cpp": r"""#include "mainwindow.h"
#include "core/engine.h"
#include "../inventory/stock.h"

MainWindow::MainWindow(QWidget *parent) : QWidget(parent)
{
    app::Engine engine;
    inventory::Stock stock;
    stock.setCount(10);
}
""",
    "src/app/inventory/stock.h": r"""#pragma once
#include "util.h"

namespace inventory {

class Stock
{
public:
    Stock();
    void setCount(int count);
    int count() const;

private:
    int m_count;
};

} // namespace inventory
""",
    "src/app/inventory/stock.cpp": r"""#include "stock.h"
#include "../core/util.h"

namespace inventory {

Stock::Stock() : m_count(0) {}

void Stock::setCount(int count)
{
    m_count = app::clampValue(count, 0, 1000);
    (void)toCents(1.0);
}

int Stock::count() const { return m_count; }

} // namespace inventory
""",
    "src/app/inventory/util.h": r"""#pragma once

namespace inventory {

inline int toCents(double amount) { return static_cast<int>(amount * 100.0); }

} // namespace inventory
""",
    "src/app/legacy/old.c": r"""#include <stdio.h>

struct legacy_item {
    int id;
};

int legacy_sum(int a, int b)
{
    return a + b;
}
""",
    "src/app/web/app.ts": r"""import { helper } from "./helper";

export function greet(name: string): string {
    return `hello ${name}`;
}

export class Greeter {
    run(): string { return greet("x"); }
}
""",
    "src/app/tool.py": r'''"""Small helper tool."""


def parse(text):
    return text.split()


class Runner:
    def run(self):
        return parse("a b")
''',
}

# repository-relative path -> Markdown text (4 pages, one project folder "demo")
KB = {
    "kb/demo/design-en.md": r"""---
title: Demo design (EN)
---
# Demo design

## Overview
The start logic is in `engine.cpp:5-12` and the header is `core/engine.h`.

## Stock and window
The stock count is set in `stock.cpp:3-4, 10-12`. The window code is in `ui/mainwindow.cpp:999`.

## Helpers
Shared helpers are declared in `util.h`. The missing part is `nothing.cpp:1`.

## Aliases
`IV/` = `inventory/`
`eng.cpp` = `core/engine.cpp`

## Alias use
The stock header is `IV/stock.h:1-3`. The engine start is `eng.cpp:7`.

## Notes
See C-01 before changing the retry limit. Test T-100 covers it.
""",
    "kb/demo/thiet-ke-vi.md": r"""---
title: Thiết kế demo (VI)
---
# Thiết kế demo

## Tổng quan
Logic khởi động nằm ở `engine.cpp:13-16`, xem thêm `core/engine.h`.
Số tồn kho được đặt trong `stock.cpp:8-12`. Cửa sổ chính ở `ui/mainwindow.cpp:5-10`.

## Hàm tiện ích
Hàm dùng chung nằm ở `inventory/util.h:5` và `util.h:1-3`. File không tồn tại: `missing_file.cpp:3`.

## Mục còn mở
- **OP-001** · Trạng thái: mở · Ảnh hưởng: `src/app/core/engine.cpp`, `kb/demo/design-en.md` · Nguồn: REQ-010
- **OP-002** · Trạng thái: đã đóng · Ảnh hưởng: `src/app/inventory/stock.cpp`

## Ghi chú
Xem C-01 trước khi đổi giới hạn thử lại.
""",
    "kb/demo/sekkei-ja.md": r"""---
title: 設計デモ (JA)
---
# 設計デモ

## 概要
エンジンの開始処理は「`engine.cpp:13-16` を参照」。
在庫数の設定は「`stock.cpp:3-4` を参照」。

## 未解決事項
OP-001 は未解決である。OP-099 については定義がまだない。テスト T-100 で確認する。

## OP-003 起動時の確認
起動時に `engine.cpp:5` を確認する。
""",
    "kb/demo/open-points.md": r"""---
title: Open points
---
# Open points demo

## Open points
- C-01 Confirm the retry limit with the owner.
- C-02 Review the startup order (`engine.cpp:5`).

## Requirements
- REQ-010 Requirement text
""",
}

# extra .qkb/config.json keys for this fixture (adapted to the engine's key names at the merge)
CONFIG = {
    "knowledge_paths": ["kb"],
    "source_paths": ["src/app"],
    # The code tree is outside every project root (project None), so bare code names
    # may resolve to it; code of ANOTHER project never resolves without code_aliases (test_c_engine CrossProjectTests).
    "project_roots": ["kb"],
    "issue_id_patterns": [r"OP-\d{3}", r"C-\d{2,3}"],
    "id_patterns": {"requirement": [r"REQ-\d{3}"], "test": [r"T-\d{3}"]},
    "cpp_include_paths": ["src/app"],
}


def _defaults():
    try:
        from core import DEFAULTS
    except ImportError:  # tests/ sits beside scripts/ in the skill folder
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from core import DEFAULTS
    return DEFAULTS


def populate_code(root):
    """Write CODE + KB under root and create .qkb/config.json = core.DEFAULTS + CONFIG (UTF-8, LF, no BOM)."""
    root = Path(root)
    for table in (CODE, KB):
        for rel, text in table.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(text.encode("utf-8"))
    (root / ".qkb").mkdir(exist_ok=True)
    cfg = dict(_defaults())
    cfg.update(CONFIG)
    (root / ".qkb/config.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
