# 大概是可以运行了，嗯对
# 至少我是这么想的

import base64
import binascii
import html as html_module
import json
import os
import random
import re
import string
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

BG        = "#16161f"
PANEL     = "#1e1e2b"
PANEL_HI  = "#2a2a3d"
FIELD     = "#101018"
BORDER    = "#32324a"
TEXT      = "#e8e8f2"
TEXT_DIM  = "#8b8ba7"
ACCENT    = "#7c5cff"
ACCENT_HI = "#9a80ff"
SUCCESS   = "#3ddc97"
ERROR     = "#ff6b81"
WARN      = "#ffb454"
INFO_BG   = "#14293a"
INFO_FG   = "#7fdcff"

FONT_TITLE = ("Microsoft YaHei UI", 19, "bold")
FONT_UI    = ("Microsoft YaHei UI", 10)
FONT_UI_B  = ("Microsoft YaHei UI", 10, "bold")
FONT_MONO  = ("Consolas", 10)


TYPE_NAMES = {
    "FillInTheBlank": "填空题",
    "MultipleChoice": "单项选择题",
    "TrueFalse":      "判断题",
    "Numeric":        "数字题",
    "ShortAnswer":    "简答题",
    "Essay":          "论述题",
    "Matching":       "匹配题",
    "Sequence":       "排序题",
    "ResultSlide":    "结果页",
    "IntroSlide":     "介绍页",
}


def strip_html(s):
    if not isinstance(s, str):
        return ""
    s = re.sub(r'<span id="qmFillInTheBlank\d+"></span>', '', s)
    s = re.sub(r'</p>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', '', s)
    s = html_module.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n\s*\n+', '\n', s)
    return s.strip()


def build_stem(q_data):
    d = q_data.get("d")
    if isinstance(d, list) and d:
        blank_map = {}
        parts = []
        for item in d:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "id" in item:
                bid = item["id"]
                if bid not in blank_map:
                    blank_map[bid] = len(blank_map) + 1
                parts.append(f"【空{blank_map[bid]}】")
        text = "".join(parts).strip()
        if text:
            return text
    return strip_html(q_data.get("a", "") or q_data.get("h", ""))


def _looks_like_container(o):
    return (isinstance(o, dict)
            and isinstance(o.get("g"), list) and o["g"]
            and isinstance(o["g"][0], dict) and "S" in o["g"][0])


def find_quiz_container(obj):
    if _looks_like_container(obj):
        return obj
    if isinstance(obj.get("d"), dict) and _looks_like_container(obj["d"]):
        return obj["d"]

    def search(o, depth=0):
        if depth > 5:
            return None
        if isinstance(o, dict):
            if _looks_like_container(o):
                return o
            for v in o.values():
                r = search(v, depth + 1)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = search(v, depth + 1)
                if r:
                    return r
        return None

    return search(obj)


def find_quiz_settings(obj, container):
    candidates = []
    if isinstance(obj.get("s"), dict):
        candidates.append(obj["s"])
    if isinstance(container, dict) and isinstance(container.get("s"), dict):
        candidates.append(container["s"])
    if isinstance(obj.get("d"), dict) and isinstance(obj["d"].get("s"), dict):
        candidates.append(obj["d"]["s"])
    for c in candidates:
        if "q" in c:
            return c
    return candidates[0] if candidates else {}


def _collect_fill_answers(*sources):
    ans_map = {}
    for src in sources:
        if not isinstance(src, list):
            continue
        for b in src:
            if not isinstance(b, dict):
                continue
            if b.get("type") != "qmFillInTheBlank":
                continue
            bid = b.get("id")
            v = (b.get("data") or {}).get("v") or []
            if bid and v:
                text = str(v[0]).replace("\r", "").replace("\n", "")
                ans_map[bid] = text
    return ans_map


def _order_answers_by_blank(arr, ans_map):
    answers = []
    if isinstance(arr, list):
        for piece in arr:
            if isinstance(piece, dict):
                pid = piece.get("id")
                if pid in ans_map:
                    answers.append(ans_map[pid])
    return answers


def parse_quiz_json(obj):
    container = find_quiz_container(obj)
    if not container:
        return [], {}

    title = container.get("T", "") or ""
    groups = container.get("g", []) or []

    questions = []
    total_points = 0
    passing_scores = []

    for group in groups:
        if not isinstance(group, dict):
            continue
        g_title = group.get("T", "")
        g_settings = group.get("s", {}) or {}
        ps = g_settings.get("ps", {}) or {}
        if ps:
            passing_scores.append((ps.get("u", ""), ps.get("v", 0)))

        for q in group.get("S", []) or []:
            if not isinstance(q, dict):
                continue
            q_type = q.get("tp", "")
            if q_type in ("ResultSlide", "IntroSlide"):
                continue

            q_data    = q.get("D", {}) or {}
            q_content = q.get("C", {}) or {}
            q_set     = q.get("s", {}) or {}
            pt = (q_set.get("e") or {}).get("pt", 0)
            total_points += pt

            if q_type == "FillInTheBlank":
                rt = q_content.get("rt") or {}
                src_for_stem = rt if rt else q_data
            else:
                src_for_stem = q_data

            stem = build_stem(src_for_stem)
            if not stem:
                continue

            item = {
                "group":   g_title,
                "type":    q_type,
                "type_cn": TYPE_NAMES.get(q_type, q_type),
                "stem":    stem,
                "points":  pt,
            }

            if q_type == "FillInTheBlank":
                ans_map = _collect_fill_answers(
                    src_for_stem.get("r"),
                    q_data.get("r"),
                    q_content.get("r"),
                )
                answers = _order_answers_by_blank(src_for_stem.get("d"), ans_map)
                if not answers:
                    answers = _order_answers_by_blank(q_data.get("d"), ans_map)
                if not answers:
                    answers = list(ans_map.values())
                item["answers"] = answers

            elif q_type in ("MultipleChoice", "TrueFalse"):
                opts = []
                for c in q_content.get("chs", []) or []:
                    if not isinstance(c, dict):
                        continue
                    t = c.get("t", {}) or {}
                    text = strip_html(t.get("a", "") or t.get("h", ""))
                    opts.append({
                        "text": text,
                        "correct": bool(c.get("c", False)),
                    })
                item["options"] = opts

            questions.append(item)

    passing_pct = None
    if passing_scores and len(set(passing_scores)) == 1:
        unit, val = passing_scores[0]
        if unit == "percents":
            passing_pct = val

    time_limit = None
    settings = find_quiz_settings(obj, container)
    q_section = settings.get("q", {}) if isinstance(settings, dict) else {}
    t_info = q_section.get("t", {}) if isinstance(q_section, dict) else {}
    if isinstance(t_info, dict) and t_info.get("e"):
        time_limit = t_info.get("v")

    group_names = []
    for g in groups:
        n = g.get("T", "") if isinstance(g, dict) else ""
        if n and n not in group_names:
            group_names.append(n)

    info = {
        "title":           title,
        "total_questions": len(questions),
        "total_points":    total_points,
        "passing_percent": passing_pct,
        "passing_points":  int(total_points * passing_pct / 100)
                           if passing_pct is not None else None,
        "time_limit":      time_limit,
        "groups":          group_names,
    }
    return questions, info


def format_questions(questions, info):
    out = []
    if info.get("title"):
        out.append(f"《{info['title']}》")
    meta = f"共 {info.get('total_questions', 0)} 题  |  " \
           f"总分 {info.get('total_points', 0)} 分"
    if info.get("passing_percent") is not None:
        meta += f"  |  及格线 {info['passing_percent']}%" \
                f"（{info['passing_points']} 分）"
    out.append(meta)
    out.append("")

    current_group = None
    n = 0
    for q in questions:
        if q["group"] != current_group:
            current_group = q["group"]
            out.append("")
            out.append(f"▼ {current_group}")
            out.append("─" * 60)
        n += 1
        out.append(f"【{n}】{q['stem']}")

        if q["type"] == "FillInTheBlank":
            answers = q.get("answers", [])
            if len(answers) == 1:
                out.append(f"      ✔ 参考答案：{answers[0]}")
            else:
                for i, a in enumerate(answers, 1):
                    out.append(f"      ✔ 空{i}答案：{a}")

        elif q["type"] in ("MultipleChoice", "TrueFalse"):
            opts = q.get("options", [])
            for i, opt in enumerate(opts):
                lab = chr(ord('A') + i)
                if opt["correct"]:
                    out.append(f"      ✔ {lab}. {opt['text']}")
                else:
                    out.append(f"        {lab}. {opt['text']}")
            correct = [chr(ord('A') + i)
                       for i, o in enumerate(opts) if o["correct"]]
            if correct:
                out.append(f"      ▶ 正确答案：{'、'.join(correct)}")

        out.append(f"      （{q['points']} 分）")
        out.append("")
    return "\n".join(out)


def _random_wrong_text(min_len=4, max_len=8):
    """生成随机错误答案文本（字母+数字）"""
    length = random.randint(min_len, max_len)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


# 这段Script将注入到备份的html文件中，不会变动源文件
# 光这个玩意就有五百多行了，还好我会vibe coding.

AUTOFILL_JS = r"""
<script>
(function () {
    "use strict";

    (function nuke() {
        try { localStorage.clear(); } catch (e) {}
        try { sessionStorage.clear(); } catch (e) {}
        try {
            var cs = document.cookie.split(";");
            for (var i = 0; i < cs.length; i++) {
                var c = cs[i].trim();
                var eq = c.indexOf("=");
                var n = eq > -1 ? c.substr(0, eq) : c;
                if (!n) continue;
                document.cookie = n + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
            }
        } catch (e) {}
        try { console.log("[AutoFill] storage cleared"); } catch (e) {}
    })();

    var QUESTIONS = __QUESTIONS_JSON__;

    function log()  { try { console.log.apply(console, ["[AutoFill]"].concat([].slice.call(arguments))); } catch (e) {} }
    function warn() { try { console.warn.apply(console, ["[AutoFill]"].concat([].slice.call(arguments))); } catch (e) {} }
    function norm(s) { return (s == null ? "" : String(s)).replace(/[\s\u200b\u200c\u200d\ufeff\u00a0]+/g, ""); }
    function makeKey(s) { return norm(s).replace(/【空\d+】/g, ""); }
    function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

    function getAllRoots() {
        var roots = [], seen = [];
        (function visit(root) {
            if (!root || seen.indexOf(root) !== -1) return;
            seen.push(root); roots.push(root);
            var ifs = [];
            try { ifs = root.querySelectorAll ? root.querySelectorAll("iframe") : []; } catch (e) {}
            for (var i = 0; i < ifs.length; i++) {
                try { if (ifs[i].contentDocument) visit(ifs[i].contentDocument); } catch (e) {}
            }
            var all = [];
            try { all = root.querySelectorAll ? root.querySelectorAll("*") : []; } catch (e) {}
            for (var j = 0; j < all.length; j++) {
                if (all[j].shadowRoot) visit(all[j].shadowRoot);
            }
        })(document);
        return roots;
    }
    function queryAllDeep(sel) {
        var out = [], roots = getAllRoots();
        for (var i = 0; i < roots.length; i++) {
            try {
                var ns = roots[i].querySelectorAll(sel);
                for (var j = 0; j < ns.length; j++) out.push(ns[j]);
            } catch (e) {}
        }
        return out;
    }
    function isVisible(el) {
        if (!el || el.nodeType !== 1) return false;
        var r;
        try { r = el.getBoundingClientRect(); } catch (e) { return false; }
        if (r.width < 2 || r.height < 2) return false;
        var cs;
        try { cs = window.getComputedStyle(el); } catch (e) { return true; }
        if (cs.display === "none" || cs.visibility === "hidden") return false;
        return true;
    }
    function isEnabled(el) {
        if (!el) return false;
        if (el.disabled) return false;
        if (el.getAttribute && el.getAttribute("aria-disabled") === "true") return false;
        return true;
    }

    function fireInput(el, value) {
        if (!el) return;
        try { el.focus(); } catch (e) {}
        try {
            if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
                var proto = el.tagName === "INPUT"
                    ? window.HTMLInputElement.prototype
                    : window.HTMLTextAreaElement.prototype;
                var desc = Object.getOwnPropertyDescriptor(proto, "value");
                if (desc && desc.set) desc.set.call(el, value);
                else el.value = value;
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
            } else if (el.isContentEditable) {
                el.textContent = value;
                try { el.dispatchEvent(new InputEvent("input", { bubbles: true, data: value })); }
                catch (e) { el.dispatchEvent(new Event("input", { bubbles: true })); }
            }
        } catch (e) {
            try { el.value = value; } catch (_) {}
        }
    }
    function fireClickStrong(el) {
        if (!el) return;
        try { el.scrollIntoView({ block: "center" }); } catch (_) {}
        try { el.focus(); } catch (_) {}
        var rect = null;
        try { rect = el.getBoundingClientRect(); } catch (_) {}
        var cx = rect ? rect.left + rect.width / 2 : 0;
        var cy = rect ? rect.top + rect.height / 2 : 0;
        var opts = { bubbles: true, cancelable: true, view: window,
                     clientX: cx, clientY: cy, button: 0, buttons: 1, detail: 1 };
        ["pointerover", "mouseover", "mousedown", "mouseup", "click"].forEach(function (name) {
            try { el.dispatchEvent(new MouseEvent(name, opts)); } catch (_) {}
        });
        try { el.click(); } catch (_) {}
    }

    function clickButton(texts) {
        var wantList = texts.map(norm);
        var btns = queryAllDeep(
            'button, [role="button"], a[role="button"], ' +
            'div[class*="button"], div[class*="Button"], ' +
            'span[class*="button"], span[class*="Button"]');
        var best = null, bestScore = 99, bestLen = Infinity;
        for (var i = 0; i < btns.length; i++) {
            var el = btns[i];
            if (!isVisible(el) || !isEnabled(el)) continue;
            var t = norm(el.textContent || "");
            if (!t || t.length > 24) continue;
            for (var k = 0; k < wantList.length; k++) {
                var want = wantList[k];
                if (!want) continue;
                var score = 99;
                if (t === want) score = 0;
                else if (t.indexOf(want) !== -1 && t.length <= want.length + 3) score = 1;
                else continue;
                if (score < bestScore || (score === bestScore && t.length < bestLen)) {
                    best = el; bestScore = score; bestLen = t.length;
                }
            }
        }
        if (best) { fireClickStrong(best); return true; }
        return false;
    }
    function tryClickStart() {
        return clickButton(["开始测试", "开始练习", "开始答题", "开始",
                            "Start Quiz", "Start", "Begin"]);
    }

    function findResumeNoButton() {
        var all = queryAllDeep(
            'button, [role="button"], a, ' +
            'div[class*="button"], div[class*="Button"], ' +
            'span[class*="button"], span[class*="Button"]');
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            if (!isVisible(el) || !isEnabled(el)) continue;
            var t = norm(el.textContent || "");
            if (!t || t.length > 14) continue;
            if (!/^(否|不|No|重新开始|重新|重启|Restart|Startover|从头开始|从头)$/i.test(t)) continue;
            var cur = el, ok = false;
            for (var d = 0; d < 8 && cur; d++) {
                var txt = cur.textContent || "";
                if (/从上次|上次离开|继续下去|继续上次|resume|continue\s*from/i.test(txt)) {
                    ok = true; break;
                }
                cur = cur.parentElement;
            }
            if (ok) return el;
        }
        return null;
    }
    async function handleResumeDialog() {
        var btn = findResumeNoButton();
        if (!btn) return false;
        log("处理继续弹窗");
        fireClickStrong(btn);
        await sleep(400);
        var btn2 = findResumeNoButton();
        if (btn2) { fireClickStrong(btn2); await sleep(300); }
        return true;
    }

    function findStemAnchor(stem) {
        var key = makeKey(stem).slice(0, 20);
        if (key.length < 6) return null;
        var roots = getAllRoots();
        var best = null, bestLen = Infinity;
        for (var r = 0; r < roots.length; r++) {
            var nodes;
            try { nodes = roots[r].querySelectorAll("*"); } catch (e) { continue; }
            for (var i = 0; i < nodes.length; i++) {
                var el = nodes[i];
                var tag = (el.tagName || "").toLowerCase();
                if (tag === "script" || tag === "style" || tag === "noscript"
                        || tag === "head" || tag === "title" || tag === "meta") continue;
                if (!isVisible(el)) continue;
                var t = makeKey(el.textContent || "");
                if (t.indexOf(key) !== -1) {
                    if (t.length < bestLen) { best = el; bestLen = t.length; }
                }
            }
        }
        return best;
    }

    function getClassSignature() {
        var all = queryAllDeep("*");
        var parts = [];
        var limit = Math.min(all.length, 5000);
        for (var i = 0; i < limit; i++) {
            var el = all[i];
            var c = el.className;
            if (!c || typeof c !== "string") continue;
            if (/selected|checked|active|current|picked|marked|on\b|chosen|answered/i.test(c)) {
                parts.push(c);
            }
        }
        return parts.join("#");
    }
    function getStateSignature() {
        var parts = [];
        try {
            var radios = queryAllDeep('input[type="radio"], input[type="checkbox"]');
            var str = "";
            for (var i = 0; i < radios.length; i++) str += radios[i].checked ? "1" : "0";
            parts.push("R:" + str);
        } catch (e) { parts.push("R:?"); }
        try {
            var aria = queryAllDeep('[aria-checked="true"],[aria-selected="true"]');
            parts.push("A:" + aria.length);
        } catch (e) { parts.push("A:?"); }
        try {
            parts.push("C:" + getClassSignature());
        } catch (e) { parts.push("C:?"); }
        return parts.join("|");
    }

    function deepestAtCenter(el) {
        try { el.scrollIntoView({ block: "center" }); } catch (e) {}
        var r;
        try { r = el.getBoundingClientRect(); } catch (e) { return el; }
        if (r.width < 2 || r.height < 2) return el;
        var cx = r.left + r.width / 2;
        var cy = r.top + r.height / 2;
        var t = null;
        try { t = document.elementFromPoint(cx, cy); } catch (e) {}
        if (!t) return el;
        if (t === el) return el;
        if (el.contains(t)) return t;
        return el;
    }
    function fireFullClick(el, cx, cy) {
        if (!el) return;
        var opts = {
            bubbles: true, cancelable: true, view: window,
            clientX: cx || 0, clientY: cy || 0,
            button: 0, buttons: 1, detail: 1
        };
        var names = ["pointerdown", "mousedown", "pointerup", "mouseup", "click"];
        for (var i = 0; i < names.length; i++) {
            var n = names[i];
            try {
                var Ctor = (n.indexOf("pointer") === 0 && window.PointerEvent)
                    ? window.PointerEvent : window.MouseEvent;
                el.dispatchEvent(new Ctor(n, opts));
            } catch (e) {}
        }
        try { el.click(); } catch (e) {}
    }
    async function attemptClickAll(target) {
        if (!target) return false;
        var sig0 = getStateSignature();

        try { target.click(); } catch (e) {}
        await sleep(60);
        if (getStateSignature() !== sig0) { log("      ✔ 策略A(原生click)"); return true; }

        var r = null;
        try { r = target.getBoundingClientRect(); } catch (e) {}
        var cx = r ? r.left + r.width / 2 : 0;
        var cy = r ? r.top + r.height / 2 : 0;
        fireFullClick(target, cx, cy);
        await sleep(60);
        if (getStateSignature() !== sig0) { log("      ✔ 策略B(鼠标序列)"); return true; }

        var deep = deepestAtCenter(target);
        if (deep && deep !== target) {
            fireFullClick(deep, cx, cy);
            await sleep(70);
            if (getStateSignature() !== sig0) { log("      ✔ 策略C(最深子元素)"); return true; }
            try { deep.click(); } catch (e) {}
            await sleep(50);
            if (getStateSignature() !== sig0) { log("      ✔ 策略C2(最深子原生click)"); return true; }
        }

        var radios = target.querySelectorAll
            ? target.querySelectorAll('input[type="radio"], input[type="checkbox"]')
            : [];
        for (var i = 0; i < radios.length; i++) {
            try { radios[i].click(); } catch (e) {}
            await sleep(50);
            if (getStateSignature() !== sig0) { log("      ✔ 策略D(radio.click)"); return true; }
        }

        var parent = target.parentElement;
        if (parent && parent !== document.body) {
            try { parent.click(); } catch (e) {}
            await sleep(50);
            if (getStateSignature() !== sig0) { log("      ✔ 策略E(父节点)"); return true; }
            fireFullClick(parent, cx, cy);
            await sleep(50);
            if (getStateSignature() !== sig0) { log("      ✔ 策略E2(父节点序列)"); return true; }
        }
        return false;
    }

    function collectStrictCandidates(correctTexts) {
        var roots = getAllRoots();
        var exact = [], tight = [];
        for (var r = 0; r < roots.length; r++) {
            var nodes;
            try { nodes = roots[r].querySelectorAll("*"); } catch (e) { continue; }
            for (var i = 0; i < nodes.length; i++) {
                var el = nodes[i];
                var tag = (el.tagName || "").toLowerCase();
                if (tag === "script" || tag === "style" || tag === "noscript"
                        || tag === "head" || tag === "title" || tag === "meta"
                        || tag === "html" || tag === "body") continue;
                if (!isVisible(el)) continue;
                var t = norm(el.textContent || "");
                if (!t || t.length < 2 || t.length > 300) continue;
                for (var k = 0; k < correctTexts.length; k++) {
                    var want = correctTexts[k];
                    if (!want || want.length < 2) continue;
                    if (t === want) {
                        exact.push({ el: el, len: t.length,
                                     isLeaf: (el.children && el.children.length > 0) ? 1 : 0 });
                        break;
                    }
                    if (t.indexOf(want) !== -1 && (t.length - want.length) <= 8) {
                        tight.push({ el: el, len: t.length,
                                     isLeaf: (el.children && el.children.length > 0) ? 1 : 0 });
                        break;
                    }
                }
            }
        }
        exact.sort(function (a, b) {
            if (a.isLeaf !== b.isLeaf) return a.isLeaf - b.isLeaf;
            return a.len - b.len;
        });
        tight.sort(function (a, b) {
            if (a.isLeaf !== b.isLeaf) return a.isLeaf - b.isLeaf;
            return a.len - b.len;
        });
        return exact.concat(tight);
    }

    async function tryPickChoice(correctTexts) {
        var cands = collectStrictCandidates(correctTexts);
        if (!cands.length) { log("  ⚠ 严格匹配不到答案文本"); return false; }
        log("  严格候选 " + cands.length + " 个");
        var limit = Math.min(cands.length, 8);
        for (var ci = 0; ci < limit; ci++) {
            var el = cands[ci].el;
            log("  尝试候选[" + ci + "]");
            try {
                if (await attemptClickAll(el)) {
                    log("  ✔ 候选[" + ci + "]成功");
                    return true;
                }
            } catch (e) {
                warn("    尝试候选[" + ci + "]异常：", e);
            }
        }
        log("  ✗ " + limit + " 个候选 × 5 策略均未生效");
        return false;
    }

    function getVisibleInputs() {
        var all = queryAllDeep(
            'input[type="text"], input:not([type]), input[type="search"], ' +
            'input[type="number"], input[type="email"], ' +
            'textarea, [contenteditable="true"]');
        var out = [];
        for (var i = 0; i < all.length; i++) {
            if (all[i].disabled || all[i].readOnly) continue;
            if (all[i].type === "radio" || all[i].type === "checkbox") continue;
            if (isVisible(all[i])) out.push(all[i]);
        }
        return out;
    }
    function findQuestionContainer(el) {
        if (!el) return null;
        var cur = el, fallback = null;
        for (var i = 0; i < 14 && cur && cur !== document.body; i++) {
            var len = (cur.textContent || "").length;
            if (len > 1500) break;
            if (len >= 8) {
                fallback = cur;
                var ins = cur.querySelectorAll
                    ? cur.querySelectorAll('input, textarea, [contenteditable="true"]')
                    : [];
                if (ins.length >= 1 && ins.length <= 6) return cur;
            }
            cur = cur.parentElement;
        }
        return fallback || (el.parentElement || el);
    }
    async function fillAnyFillInBlank(filledSet) {
        var inputs = getVisibleInputs();
        if (!inputs.length) return null;
        var container = findQuestionContainer(inputs[0]);
        if (!container) return null;
        var ct = makeKey(container.textContent || "");
        for (var qi = 0; qi < QUESTIONS.length; qi++) {
            if (filledSet[qi]) continue;
            var q = QUESTIONS[qi];
            if (q.type !== "FillInTheBlank") continue;
            var key = makeKey(q.stem);
            if (key.length < 6) continue;
            var probe = key.slice(0, 15);
            if (ct.indexOf(probe) === -1) continue;
            var group = [];
            for (var i = 0; i < inputs.length; i++) {
                if (container.contains(inputs[i])) group.push(inputs[i]);
            }
            if (!group.length) group = [inputs[0]];
            log("填空 #" + (qi + 1) + "：", q.stem.slice(0, 25),
                "→", (q.answers || []).join(" | "));
            for (var k = 0; k < q.answers.length && k < group.length; k++) {
                fireInput(group[k], q.answers[k]);
                await sleep(25);
            }
            filledSet[qi] = true;
            return "filled";
        }
        return null;
    }

    async function fillAnyChoice(filledSet) {
        for (var qi = 0; qi < QUESTIONS.length; qi++) {
            if (filledSet[qi]) continue;
            var q = QUESTIONS[qi];
            if (q.type !== "MultipleChoice" && q.type !== "TrueFalse") continue;
            var anchor = findStemAnchor(q.stem);
            if (!anchor) continue;
            log("定位选择题 #" + (qi + 1) + "：", q.stem.slice(0, 25));
            var correctTexts = (q.options || [])
                .filter(function (o) { return o.correct; })
                .map(function (o) { return norm(o.text); })
                .filter(function (t) { return t && t.length >= 2; });
            if (!correctTexts.length) { log("  No Such Thing Found"); continue; }
            log("  正确答案：", correctTexts.map(function (t) { return t.slice(0, 22); }));
            if (await tryPickChoice(correctTexts)) {
                filledSet[qi] = true;
                return "filled";
            }
        }
        return null;
    }

    async function fillCurrentPage(filledSet) {
        var r = await fillAnyFillInBlank(filledSet);
        if (r) return r;
        return await fillAnyChoice(filledSet);
    }

    /* 在结束页面停 */

    function isResultsPage() {
        try {
            var btns = queryAllDeep(
                'button, [role="button"], ' +
                'div[class*="button"], div[class*="Button"], ' +
                'span[class*="button"], span[class*="Button"]');
            for (var i = 0; i < btns.length; i++) {
                if (!isVisible(btns[i])) continue;
                var t = norm(btns[i].textContent || "");
                if (/^回看测试$|^回看练习$|^详细报告$/.test(t)) return true;
            }
            var bodyText = document.body ? (document.body.textContent || "") : "";
            if (/你的成绩|合格标准|恭喜.{0,4}合格|遗憾.{0,4}不合格/i.test(bodyText)) {
                return true;
            }
        } catch (e) {}
        return false;
    }

    async function finalize() {
        log("=== 收尾：提交所有 → 查看成绩 ===");

        for (var i = 0; i < 3; i++) {
            if (clickButton(["提交所有", "完成测试", "完成", "结束",
                             "Finish", "Submit All", "End Quiz"])) {
                log("  → 点击「提交所有 / 完成」");
                await sleep(900);
                break;
            }
            await sleep(250);
        }

        var reached = false;
        for (var attempt = 0; attempt < 15; attempt++) {
            if (isResultsPage()) {
                log("  ✔ Done");
                reached = true;
                break;
            }

            if (clickButton(["查看成绩", "查看测试成绩", "查看结果", "查看报告",
                             "View Results", "View Report", "Show Results"])) {
                log("  → 点击「查看成绩」");
                await sleep(900);
                if (isResultsPage()) {
                    log("  ✔ 已到达成绩页");
                    reached = true;
                    break;
                }
                continue;
            }

            if (clickButton(["是", "好", "确定", "OK", "Yes"])) {
                log("  → 确认弹窗");
                await sleep(700);
                if (isResultsPage()) {
                    log("  ✔ Done");
                    reached = true;
                    break;
                }
                continue;
            }

            await sleep(400);
            if (isResultsPage()) {
                log("  ✔ Done");
                reached = true;
                break;
            }
        }

        if (!reached && !isResultsPage()) {
            await sleep(800);
            if (clickButton(["查看成绩", "查看测试成绩", "查看结果",
                             "View Results", "View Report"])) {
                log("  ✔ Click Down");
                await sleep(900);
                if (isResultsPage()) {
                    log("  Done");
                    reached = true;
                }
            }
        }

        if (reached) log("=== Successful ===");
        else log("=== Failed ===");
    }

    /* ============ 主流程 ============ */
    async function run() {
        log("Start. Questions:", QUESTIONS.length);
        await sleep(500);

        if (await handleResumeDialog()) await sleep(500);

        for (var s = 0; s < 3; s++) {
            if (tryClickStart()) {
                log("点击开始");
                await sleep(700);
                if (await handleResumeDialog()) await sleep(500);
            } else break;
        }
        await sleep(400);

        var filledSet = {};
        var okCount = 0, idle = 0;
        var maxSteps = QUESTIONS.length * 6 + 40;
        var postponeUsed = 0;

        for (var step = 0; step < maxSteps; step++) {
            if (await handleResumeDialog()) { await sleep(600); continue; }

            var result = null;
            try { result = await fillCurrentPage(filledSet); }
            catch (e) { warn("异常：", e); }

            if (result === "filled") {
                okCount++;
                idle = 0;
                await sleep(350);
                var submitted = false;
                for (var si = 0; si < 5; si++) {
                    if (clickButton(["提交答案", "提交", "执行", "确定", "Submit"])) {
                        submitted = true;
                        log("  ✔ 提交已点击");
                        break;
                    }
                    await sleep(200);
                }
                if (!submitted) log("  ⚠ 未找到提交按钮");
                await sleep(450);
            } else {
                idle++;
                if (idle === 3 && postponeUsed < 3) {
                    if (clickButton(["推迟", "跳过", "Postpone", "Skip"])) {
                        log("  → 推迟/跳过");
                        postponeUsed++;
                        await sleep(500);
                        idle = 0;
                        continue;
                    }
                }
            }

            var advanced = clickButton(
                ["下一项", "下一题", "下一页", "Next", "继续", "Continue"]);
            if (advanced) {
                await sleep(500);
                if (okCount >= QUESTIONS.length) break;
                continue;
            }

            clickButton(["提交所有", "完成", "结束", "Finish", "关闭", "Close"]);
            if (idle >= 6) { log("连续 " + idle + " 步无进展，退出"); break; }
            if (okCount >= QUESTIONS.length) { log("已完成全部"); break; }
            await sleep(160);
        }

        var summary = "自动填写完成：成功 " + okCount + " / " + QUESTIONS.length;
        if (okCount < QUESTIONS.length) summary += "，未填 " + (QUESTIONS.length - okCount) + " 题";

        await sleep(500);
        await finalize();

        log("Done. OK:", okCount, "Total:", QUESTIONS.length);
        log(summary);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run);
    } else {
        run();
    }
})();
</script>
"""

# 主程序部分

class Base64DecoderApp:
    DATA_RE = re.compile(r'var\s+data\s*=\s*(["\'])([^"\']*)\1')
    MAX_DISPLAY = 500_000
    HUGE_THRESHOLD = 5_000_000

    def __init__(self, root):
        self.root = root
        self.path_var = tk.StringVar()
        self.wrong_ratio_var = tk.DoubleVar(value=10.0)
        self._full_result = ""
        self._questions = []
        self._quiz_info = {}
        self._raw_stats = {"bytes": 0, "b64": 0, "path": ""}
        self._view = "raw"

        self._setup_window()
        self._build_ui()
        self._bind_keys()

    def _setup_window(self):
        self.root.title("神秘课后练习自动完成")
        self.root.geometry("1160x840")
        self.root.minsize(900, 680)
        self.root.configure(bg=BG)

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BG, padx=26, pady=20)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="神秘课后练习自动完成工具，看完能绷住的把自己加进去",
                 bg=BG, fg=TEXT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(outer,
                 text='请先点击按钮选择一个.html文件',
                 bg=BG, fg=TEXT_DIM, font=FONT_UI).pack(anchor="w", pady=(6, 0))
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x", pady=18)

        card = tk.Frame(outer, bg=PANEL, highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=PANEL, padx=18, pady=16)
        inner.pack(fill="x")

        # ---- 文件选择 ----
        tk.Label(inner, text="完整文件路径", bg=PANEL, fg=TEXT_DIM,
                 font=FONT_UI_B).pack(anchor="w")

        row = tk.Frame(inner, bg=PANEL)
        row.pack(fill="x", pady=(8, 0))

        holder = tk.Frame(row, bg=BORDER)
        holder.pack(side="left", fill="x", expand=True)
        self.entry = tk.Entry(holder, textvariable=self.path_var,
                              bg=FIELD, fg=TEXT, insertbackground=ACCENT,
                              relief="flat", bd=0, font=FONT_MONO,
                              highlightthickness=0,
                              selectbackground=ACCENT, selectforeground="#ffffff")
        self.entry.pack(fill="x", padx=1, pady=1, ipady=9)

        self._button(row, "浏览文件…", self.browse_file, "secondary")\
            .pack(side="left", padx=(10, 0))

        slider_row = tk.Frame(inner, bg=PANEL)
        slider_row.pack(fill="x", pady=(14, 0))

        tk.Label(slider_row, text="错题比例", bg=PANEL, fg=TEXT_DIM,
                 font=FONT_UI_B).pack(side="left", padx=(0, 12))

        self.wrong_scale = tk.Scale(
            slider_row, from_=0, to=100, orient="horizontal",
            variable=self.wrong_ratio_var, showvalue=False, resolution=1,
            bg=PANEL, fg=TEXT, troughcolor=FIELD,
            activebackground=ACCENT_HI,
            highlightthickness=0, bd=0, sliderrelief="flat",
            sliderlength=22, width=14,
            command=self._on_slider_change)
        self.wrong_scale.pack(side="left", fill="x", expand=True, ipady=2)

        self.wrong_label = tk.Label(slider_row, text="10%",
                                     bg=PANEL, fg=ACCENT_HI,
                                     font=FONT_UI_B, width=5, anchor="e")
        self.wrong_label.pack(side="left", padx=(12, 0))

        hint_row = tk.Frame(inner, bg=PANEL)
        hint_row.pack(fill="x", pady=(4, 0))
        tk.Label(hint_row,
                 text="0% = 全部答对；100% = 全部答错（默认10%，你自己也不相信你一分钟能把这玩意做全对吧...）",
                 bg=PANEL, fg=TEXT_DIM, font=("Microsoft YaHei UI", 9)).pack(anchor="w")

        # ---- 按钮栏 ----
        actions = tk.Frame(inner, bg=PANEL)
        actions.pack(fill="x", pady=(14, 0))
        self._button(actions, "解码并解析", self.decode, "primary").pack(side="left")
        self._button(actions, "⚡ 自动填写答案", self.auto_fill, "auto")\
            .pack(side="left", padx=(10, 0))
        self._button(actions, "查看原始文本", self.show_raw, "ghost")\
            .pack(side="left", padx=(10, 0))
        self._button(actions, "复制结果", self.copy_result, "ghost")\
            .pack(side="left", padx=(10, 0))
        self._button(actions, "另存为…", self.save_result, "ghost")\
            .pack(side="left", padx=(10, 0))
        self._button(actions, "清空", self.clear_output, "ghost")\
            .pack(side="left", padx=(10, 0))

        out_card = tk.Frame(outer, bg=PANEL, highlightbackground=BORDER,
                            highlightthickness=1)
        out_card.pack(fill="both", expand=True, pady=(18, 0))

        head = tk.Frame(out_card, bg=PANEL)
        head.pack(fill="x", padx=18, pady=(14, 0))
        self.view_label = tk.Label(head, text="解码结果", bg=PANEL, fg=TEXT,
                                   font=FONT_UI_B)
        self.view_label.pack(side="left")
        self.count_label = tk.Label(head, text="等待操作…", bg=PANEL,
                                    fg=TEXT_DIM, font=FONT_UI)
        self.count_label.pack(side="right")

        wrap = tk.Frame(out_card, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=18, pady=(10, 16))

        vbar = tk.Scrollbar(wrap, bg=PANEL, troughcolor=PANEL,
                            activebackground=ACCENT, relief="flat",
                            bd=0, highlightthickness=0, width=12)
        vbar.pack(side="right", fill="y")
        hbar = tk.Scrollbar(wrap, bg=PANEL, troughcolor=PANEL,
                            activebackground=ACCENT, relief="flat",
                            bd=0, highlightthickness=0, orient="horizontal")
        hbar.pack(side="bottom", fill="x")

        self.output = tk.Text(wrap, bg=FIELD, fg=TEXT, relief="flat",
                              bd=0, wrap="none", font=FONT_MONO,
                              padx=14, pady=12, highlightthickness=0,
                              selectbackground=ACCENT, selectforeground="#ffffff",
                              yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        vbar.configure(command=self.output.yview)
        hbar.configure(command=self.output.xview)

        self.output.tag_configure("meta",     foreground=TEXT_DIM)
        self.output.tag_configure("sep",      foreground=BORDER)
        self.output.tag_configure("body",     foreground=TEXT)
        self.output.tag_configure("warn",     foreground=WARN)
        self.output.tag_configure("cut",      foreground=ERROR)
        self.output.tag_configure("qtitle",   foreground=ACCENT_HI,
                                   font=("Microsoft YaHei UI", 12, "bold"))
        self.output.tag_configure("qgroup",   foreground=INFO_FG,
                                   font=("Microsoft YaHei UI", 11, "bold"))
        self.output.tag_configure("qnum",     foreground="#ffd479",
                                   font=("Microsoft YaHei UI", 10, "bold"))
        self.output.tag_configure("qanswer",  foreground=SUCCESS,
                                   font=("Microsoft YaHei UI", 10, "bold"))
        self.output.tag_configure("qmeta",    foreground=TEXT_DIM,
                                   font=("Consolas", 9))
        self.output.tag_configure("qoptions", foreground=TEXT)
        self.output.configure(state="disabled")

        self.info_frame = tk.Frame(outer, bg=INFO_BG,
                                    highlightbackground=BORDER,
                                    highlightthickness=1)
        self.info_frame.pack(fill="x", pady=(12, 0))
        self.info_label = tk.Label(self.info_frame,
                                    text="提示：解码后将在此显示测验信息（题目数、总分、及格分…）",
                                    bg=INFO_BG, fg=TEXT_DIM,
                                    font=FONT_UI, anchor="w",
                                    padx=14, pady=10, justify="left")
        self.info_label.pack(fill="x")

        self.status = tk.Label(outer, text="请选择一个 .html 文件",
                               bg=BG, fg=TEXT_DIM, font=FONT_UI, anchor="w")
        self.status.pack(fill="x", pady=(8, 0))

    def _button(self, parent, text, command, kind="ghost"):
        palette = {
            "primary":   (ACCENT,   ACCENT_HI),
            "secondary": (PANEL_HI, "#3a3a55"),
            "ghost":     (PANEL,    "#2c2c42"),
            "auto":      ("#b45309", "#d97706"),
        }[kind]
        bg, hover = palette
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=TEXT, activebackground=hover,
                        activeforeground=TEXT, relief="flat", bd=0,
                        highlightthickness=0, cursor="hand2",
                        font=FONT_UI_B if kind in ("primary", "auto") else FONT_UI,
                        padx=16, pady=8)
        btn.bind("<Enter>", lambda _e: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
        return btn

    def _bind_keys(self):
        self.root.bind("<Control-o>", lambda _e: self.browse_file())
        self.root.bind("<Control-d>", lambda _e: self.decode())
        self.root.bind("<Control-s>", lambda _e: self.save_result())
        self.root.bind("<Control-l>", lambda _e: self.clear_output())
        self.root.bind("<Control-f>", lambda _e: self.auto_fill())
        self.entry.bind("<Return>", lambda _e: self.decode())

    def _on_slider_change(self, value):
        try:
            v = int(float(value))
        except Exception:
            v = 0
        self.wrong_label.configure(text=f"{v}%")

    def set_status(self, message, color=TEXT_DIM):
        self.status.configure(text=message, fg=color)

    def _render_text_view(self, meta_lines, body, warn_lines=(), cut_note=""):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        for line in meta_lines:
            self.output.insert("end", line + "\n", "meta")
        for line in warn_lines:
            self.output.insert("end", line + "\n", "warn")
        if meta_lines or warn_lines:
            self.output.insert("end", "─" * 72 + "\n", "sep")
        self.output.insert("end", body, "body")
        if cut_note:
            self.output.insert("end", cut_note, "cut")
        self.output.configure(state="disabled")
        self.output.yview_moveto(0.0)
        self.output.xview_moveto(0.0)

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self._full_result = ""
        self._questions = []
        self._quiz_info = {}
        self._raw_stats = {"bytes": 0, "b64": 0, "path": ""}
        self._view = "raw"
        self.count_label.configure(text="Waiting for input…")
        self.view_label.configure(text="处理结果")
        self.info_label.configure(
            text="将在此显示测验信息",
            fg=TEXT_DIM)
        self.set_status("已清空", TEXT_DIM)

    def _update_info_bar(self, info):
        if not info or not info.get("total_questions"):
            self.info_label.configure(
                text="将在此显示测验信息",
                fg=TEXT_DIM)
            return
        parts = []
        if info.get("title"):
            parts.append(f"📖 {info['title']}")
        parts.append(f"题目 {info['total_questions']} 道")
        parts.append(f"总分 {info['total_points']} 分")
        if info.get("passing_percent") is not None:
            parts.append(f"及格 {info['passing_points']} 分"
                         f"（{info['passing_percent']}%）")
        if info.get("time_limit"):
            m, s = divmod(int(info["time_limit"]), 60)
            parts.append(f"限时 {m} 分 {s} 秒" if s else f"限时 {m} 分钟")
        if info.get("groups"):
            parts.append("分组：" + " / ".join(info["groups"]))
        self.info_label.configure(text="　|　".join(parts), fg=INFO_FG)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="选择 HTML 文件",
            filetypes=[("HTML 文件", "*.html *.htm"),
                       ("文本文件", "*.txt"),
                       ("所有文件", "*.*")])
        if path:
            self.path_var.set(path)
            self.set_status(f"已选择：{path}", TEXT_DIM)

    def _extract_data(self, path):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        m = self.DATA_RE.search(html)
        if not m:
            raise ValueError('未找到 `var data = "..."` 结构')

        cleaned = re.sub(r"\s+", "", m.group(2))
        if not cleaned:
            raise ValueError("var data 内容为空")

        padded = cleaned + "=" * (-len(cleaned) % 4)
        try:
            data = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            try:
                data = base64.urlsafe_b64decode(padded)
            except Exception as exc:
                raise ValueError(f"Base64 解码失败：{exc}")

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")

        return text, len(data), len(cleaned)

    def decode(self):
        path = self.path_var.get().strip().strip('"').strip("'")
        if not path:
            messagebox.showwarning("提示", "请先选择一个 .html 文件。")
            self.set_status("未选择文件", ERROR)
            return
        if not os.path.isfile(path):
            messagebox.showerror("错误", f"文件不存在：\n{path}")
            self.set_status("文件不存在", ERROR)
            return

        self.set_status("正在执行…")
        self.root.update_idletasks()

        try:
            text, n_bytes, n_b64 = self._extract_data(path)
        except Exception as exc:
            messagebox.showerror("失败", str(exc))
            self.set_status(str(exc), ERROR)
            return

        self._full_result = text
        self._raw_stats = {"bytes": n_bytes, "b64": n_b64, "path": path}

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None

        if obj is not None:
            try:
                questions, info = parse_quiz_json(obj)
            except Exception as exc:
                questions, info = [], {}
                self.set_status(f"JSON 解析异常：{exc}", WARN)

            if questions:
                self._questions = questions
                self._quiz_info = info
                self._show_questions_view()
                self._update_info_bar(info)
                self.count_label.configure(
                    text=f"{len(questions)} 题 · {info.get('total_points', 0)} 分")
                self.view_label.configure(text="解析结果")
                self.set_status(
                    f"✔ 解码成功，已解析 {len(questions)} 道题目",
                    SUCCESS)
                return

        self._questions = []
        self._quiz_info = {}
        self._show_raw_view(path, text, n_bytes, n_b64)
        self._update_info_bar({})
        if obj is None:
            self.set_status("✔ 解码成功，但这可能并不是JSON内容", WARN)
        else:
            self.set_status("✔ 解码成功，但未找到题目数据", WARN)

    def _show_raw_view(self, path, text, n_bytes, n_b64, warn_lines=()):
        total = len(text)
        if total > self.MAX_DISPLAY:
            preview = text[: self.MAX_DISPLAY]
            cut = (f"\n\n…（已省略剩余 {total - self.MAX_DISPLAY:,} 个字符，否则会卡死，别问我怎么知道的。"
                   f"完整内容需要导出或复制）")
        else:
            preview = text
            cut = ""
        meta = [
            f"文件     : {os.path.basename(path)}",
            f"完整路径 : {path}",
            f"Base64   : {n_b64:,} 字符",
            f"解码结果 : {n_bytes:,} 字节",
            f"文本长度 : {total:,} 字符"
            + (f"（仅预览前 {self.MAX_DISPLAY:,}）" if cut else ""),
        ]
        self._view = "raw"
        self.view_label.configure(text="解码结果（原始）")
        self._render_text_view(meta, preview, warn_lines, cut)

    def show_raw(self):
        if not self._full_result:
            self.set_status("尚未解码任何内容", ERROR)
            return
        self._show_raw_view(
            self._raw_stats.get("path", self.path_var.get()),
            self._full_result,
            self._raw_stats.get("bytes", 0),
            self._raw_stats.get("b64", 0))
        self.set_status("已切换到原始文本视图", TEXT_DIM)

    def _show_questions_view(self):
        self._view = "questions"
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")

        info = self._quiz_info
        if info.get("title"):
            self.output.insert("end", f"《{info['title']}》\n", "qtitle")

        head = (f"共 {info.get('total_questions', 0)} 题    "
                f"总分 {info.get('total_points', 0)} 分")
        if info.get("passing_percent") is not None:
            head += f"    及格线 {info['passing_percent']}% "\
                    f"（{info['passing_points']} 分）"
        if info.get("time_limit"):
            m, s = divmod(int(info["time_limit"]), 60)
            head += f"    限时 {m} 分 {s} 秒"
        self.output.insert("end", head + "\n\n", "qmeta")

        current_group = None
        n = 0
        for q in self._questions:
            if q["group"] != current_group:
                current_group = q["group"]
                self.output.insert("end", "\n")
                self.output.insert("end", f"▼ {current_group}\n", "qgroup")
                self.output.insert("end", "─" * 72 + "\n", "sep")
                self.output.insert("end", "\n")

            n += 1
            self.output.insert("end", f"【{n}】", "qnum")
            self.output.insert("end", q["stem"] + "\n", "body")

            if q["type"] == "FillInTheBlank":
                answers = q.get("answers", [])
                if not answers:
                    self.output.insert("end", "      ⚠ 未找到答案\n", "warn")
                elif len(answers) == 1:
                    self.output.insert(
                        "end", f"      ✔ 参考答案：{answers[0]}\n", "qanswer")
                else:
                    for i, a in enumerate(answers, 1):
                        self.output.insert(
                            "end", f"      ✔ 空{i}答案：{a}\n", "qanswer")

            elif q["type"] in ("MultipleChoice", "TrueFalse"):
                opts = q.get("options", [])
                correct = []
                for i, opt in enumerate(opts):
                    lab = chr(ord('A') + i)
                    if opt["correct"]:
                        correct.append(lab)
                        self.output.insert(
                            "end", f"      ✔ {lab}. {opt['text']}\n", "qanswer")
                    else:
                        self.output.insert(
                            "end", f"        {lab}. {opt['text']}\n", "qoptions")
                if correct:
                    self.output.insert(
                        "end",
                        f"      ▶ 正确答案：{'、'.join(correct)}\n",
                        "qanswer")

            self.output.insert("end", f"      （{q['points']} 分）\n\n", "qmeta")

        self.output.configure(state="disabled")
        self.output.yview_moveto(0.0)

    # ------------------------------------------------------------------
    # ★ 根据错题比例生成 payload
    # ------------------------------------------------------------------
    def _make_payload(self, wrong_ratio):
        """根据错题比例生成注入数据，返回 (payload, n_wrong)"""
        n = len(self._questions)
        if n == 0:
            return [], 0

        if wrong_ratio <= 0:
            n_wrong = 0
        elif wrong_ratio >= 100:
            n_wrong = n
        else:
            n_wrong = max(1, round(n * wrong_ratio / 100.0))
            n_wrong = min(n_wrong, n)

        if n_wrong <= 0:
            wrong_indices = set()
        elif n_wrong >= n:
            wrong_indices = set(range(n))
        else:
            wrong_indices = set(random.sample(range(n), n_wrong))

        payload = []
        for idx, q in enumerate(self._questions):
            is_wrong = idx in wrong_indices
            item = {"type": q["type"], "stem": q["stem"]}

            if q["type"] == "FillInTheBlank":
                answers = list(q.get("answers", []))
                if is_wrong:
                    answers = [_random_wrong_text() for _ in answers] or \
                              [_random_wrong_text()]
                item["answers"] = answers

            elif q["type"] in ("MultipleChoice", "TrueFalse"):
                options = q.get("options", [])
                if is_wrong:
                    wrong_idxs = [i for i, o in enumerate(options)
                                  if not o["correct"]]
                    if wrong_idxs:
                        chosen = random.choice(wrong_idxs)
                        item["options"] = [
                            {"text": o["text"], "correct": (i == chosen)}
                            for i, o in enumerate(options)
                        ]
                    else:
                        # 万一没有错误选项，保持原样
                        item["options"] = [
                            {"text": o["text"], "correct": bool(o["correct"])}
                            for i, o in enumerate(options)
                        ]
                else:
                    item["options"] = [
                        {"text": o["text"], "correct": bool(o["correct"])}
                        for i, o in enumerate(options)
                    ]

            payload.append(item)

        return payload, n_wrong

    # ------------------------------------------------------------------
    def auto_fill(self):
        if not self._questions:
            messagebox.showwarning(
                "提示",
                "还没有解析出题目。\n\n请先点击「解码并解析」，确认题目列表已生成。")
            self.set_status("尚未解析题目，无法自动填写", ERROR)
            return

        path = self._raw_stats.get("path") or self.path_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("错误", "原 HTML 文件路径无效。")
            self.set_status("原 HTML 文件路径无效", ERROR)
            return

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
        except OSError as exc:
            messagebox.showerror("读取失败", str(exc))
            return

        # 读取滑块值
        try:
            wrong_ratio = float(self.wrong_ratio_var.get())
        except Exception:
            wrong_ratio = 10.0

        payload, n_wrong = self._make_payload(wrong_ratio)

        js_data = json.dumps(payload, ensure_ascii=False)
        js_data = js_data.replace("</", "<\\/")

        script = AUTOFILL_JS.replace("__QUESTIONS_JSON__", js_data)

        lowered = html.lower()
        idx = lowered.rfind("</head>")
        if idx == -1:
            idx = lowered.rfind("</body>")
        if idx == -1:
            idx = lowered.rfind("</html>")
        if idx != -1:
            new_html = html[:idx] + "\n" + script + "\n" + html[idx:]
        else:
            new_html = html + "\n" + script

        folder, name = os.path.split(path)
        stem, ext = os.path.splitext(name)
        out_path = os.path.join(folder, f"{stem}_autofill{ext or '.html'}")

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(new_html)
        except OSError as exc:
            messagebox.showerror("写入失败", str(exc))
            self.set_status(f"写入失败：{exc}", ERROR)
            return

        total = len(self._questions)
        self.set_status(
            f"✔ 已生成自动填写版：故意答错 {n_wrong} / {total} 题 "
            f"（比例 {wrong_ratio:.0f}%）→ {out_path}",
            SUCCESS)

        try:
            webbrowser.open("file:///" + out_path.replace("\\", "/"))
        except Exception as exc:
            messagebox.showwarning(
                "打开浏览器失败",
                f"文件已保存到：\n{out_path}\n\n请手动用浏览器打开。\n\n错误：{exc}")
            return

        messagebox.showinfo(
            "自动填写已启动",
            "已生成自动填写版本并在浏览器中打开：\n\n"
            f"{out_path}\n\n"
            f"本次配置：故意答错 {n_wrong} / {total} 题（比例 {wrong_ratio:.0f}%）\n\n")

    # ------------------------------------------------------------------
    def copy_result(self):
        if not self._full_result:
            self.set_status("没有可复制的内容", ERROR)
            return
        if self._view == "questions" and self._questions:
            text = format_questions(self._questions, self._quiz_info)
        else:
            text = self._full_result

        if len(text) > self.HUGE_THRESHOLD:
            if not messagebox.askyesno(
                    "确认复制",
                    f"内容约 {len(text):,} 个字符，"
                    "复制到剪贴板可能需要几秒，是否继续？"):
                return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.set_status(f"✔ 已复制（{len(text):,} 字符）", SUCCESS)

    def save_result(self):
        if not self._full_result:
            self.set_status("没有可保存的内容", ERROR)
            return

        if self._view == "questions" and self._questions:
            default_name = "quiz_questions.txt"
            text = format_questions(self._questions, self._quiz_info)
        else:
            default_name = "decoded.txt"
            text = self._full_result

        path = filedialog.asksaveasfilename(
            title="保存结果",
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            self.set_status(f"保存失败：{exc}", ERROR)
            return
        self.set_status(f"✔ 已保存到：{path}", SUCCESS)


# ----------------------------------------------------------------------
def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    Base64DecoderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()