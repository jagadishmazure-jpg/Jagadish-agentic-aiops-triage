"""LLM triage: a tool-using agent loop, a one-shot answer from the page alone, and a hybrid where the
correlation engine shortlists candidates and the model reads their evidence. Same model and runbook."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from .rca import first_alert, graph_rca
from .runbook import runbook_text
from .tools import TOOLS_DOC, IncidentTools

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_brands import scrub  # noqa: E402

PROMPTS = ROOT / "prompts"
LIMITS = {"max_turns": 12, "max_tool_calls": 10, "max_new_tokens": 256, "n_ctx": 8192, "no_call_streak": 3}
CONFIGS = {
    "gemma4-e2b.agent": {"model": "gemma-4-e2b", "mode": "agent"},
    "gemma4-e2b.hybrid": {"model": "gemma-4-e2b", "mode": "hybrid"},
    "gemma4-e2b.oneshot": {"model": "gemma-4-e2b", "mode": "oneshot"},
    # Stress test: the same hybrid, but every incident's root-cause log carries the injected instruction.
    "gemma4-e2b.hybrid-injected": {"model": "gemma-4-e2b", "mode": "hybrid_injected"},
}
RULES = {"first_alert": first_alert, "graph_rca": graph_rca}


def public_view(incident: dict) -> dict:
    """What any triage method may see: everything except the answer."""
    return {k: v for k, v in incident.items() if k not in ("fault", "root", "t0", "flags")}


def find_json(text: str, key: str) -> dict | None:
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
    return None


def parse_call(text: str) -> tuple[str, dict] | None:
    obj = find_json(text, "tool")
    if obj is None or not isinstance(obj["tool"], str):
        return None
    args = obj.get("args", obj.get("arguments", {}))
    return obj["tool"], args if isinstance(args, dict) else {}


def chat(llm, msgs: list[dict], max_tokens: int) -> tuple[str, int, int]:
    r = llm.create_chat_completion(messages=msgs, temperature=0, max_tokens=max_tokens, seed=0)
    text = scrub(r["choices"][0]["message"]["content"] or "")[0]
    return text, r["usage"]["prompt_tokens"], r["usage"]["completion_tokens"]


def result(incident, config, model, answer, stop, t0, turns, calls, invalid, pt, ct, trace, raw="") -> dict:
    answer = answer or {}
    return {"id": incident["id"], "config": config, "model": model, "stop": stop,
            "root": str(answer.get("root_service", answer.get("root", "")) or ""),
            "fault": str(answer.get("fault_type", answer.get("fault", "")) or ""),
            "action": str(answer.get("action", "") or ""),
            "candidates": answer.get("candidates", []),
            "summary": scrub(str(answer.get("summary", "")))[0][:400], "turns": turns, "tool_calls": calls,
            "invalid_replies": invalid, "prompt_tokens": pt, "completion_tokens": ct,
            "seconds": round(time.perf_counter() - t0, 1), "trace": trace, "raw": raw[:600]}


def run_agent(incident: dict, llm, config: str) -> dict:
    t0 = time.perf_counter()
    tools = IncidentTools(public_view(incident), max_calls=LIMITS["max_tool_calls"])
    system = (PROMPTS / "agent.md").read_text().strip() + "\n\n" + runbook_text() + "\n\n" + TOOLS_DOC
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": f"Incident {incident['id'].split('-')[1]} is open: "
                                        f"{len(incident['alerts'])} alerts fired. Start triage. "
                                        f"Budget: {LIMITS['max_tool_calls']} tool calls."}]
    turns = streak = invalid = pt = ct = 0
    stop, trace = "max_turns", []
    while turns < LIMITS["max_turns"]:
        turns += 1
        if len(llm.tokenize(json.dumps(msgs).encode())) + LIMITS["max_new_tokens"] > LIMITS["n_ctx"]:
            stop = "context_full"
            break
        reply, p, c = chat(llm, msgs, LIMITS["max_new_tokens"])
        pt, ct = pt + p, ct + c
        msgs.append({"role": "assistant", "content": reply})
        call = parse_call(reply)
        if call is None:
            streak += 1
            invalid += 1
            trace.append({"turn": turns, "tool": None})
            if streak >= LIMITS["no_call_streak"]:
                stop = "no_tool_call"
                break
            msgs.append({"role": "user", "content": "No tool call found. Reply with one JSON tool call."})
            continue
        streak = 0
        out = tools.call(*call)
        trace.append({"turn": turns, **tools.log[-1]})
        if tools.submission is not None:
            stop = "submitted"
            break
        note = "\nTool budget used up. Call submit now." if tools.calls >= tools.max_calls else ""
        msgs.append({"role": "user", "content": f"Result:\n{out}{note}"})
    s = tools.submission or {}
    answer = {"root_service": s.get("root"), "fault_type": s.get("fault"), "action": s.get("action"),
              "summary": s.get("summary", "")}
    return result(incident, config, CONFIGS[config]["model"], answer, stop, t0, turns, tools.calls, invalid,
                  pt, ct, trace)


def one_answer(incident, llm, config, evidence: str, extra: dict | None = None) -> dict:
    t0 = time.perf_counter()
    msgs = [{"role": "system", "content": (PROMPTS / "answer.md").read_text().strip() + "\n\n" + runbook_text()},
            {"role": "user", "content": evidence}]
    reply, p, c = chat(llm, msgs, LIMITS["max_new_tokens"])
    ans = find_json(reply, "root_service")
    r = result(incident, config, CONFIGS[config]["model"], {**(ans or {}), **(extra or {})},
               "answered" if ans else "no_answer", t0, 1, 0, 0 if ans else 1, p, c, [], raw=reply)
    return r


def run_oneshot(incident: dict, llm, config: str) -> dict:
    """Only what the page shows: alerts, change records and the service map. No tools, no logs."""
    tools = IncidentTools(public_view(incident))
    from .topology import CALLS

    graph = "\n".join(f"{s} -> {', '.join(c)}" for s, c in CALLS.items() if c)
    ev = (f"Alerts:\n{tools.t_get_alerts()}\n\nChanges:\n{tools.t_get_changes()}\n\nService map (caller -> callees):\n"
          f"{graph}")
    return one_answer(incident, llm, config, ev)


def run_hybrid(incident: dict, llm, config: str) -> dict:
    """The correlation engine shortlists three candidates; the model reads their metrics and logs."""
    pub = public_view(incident)
    g = graph_rca(pub)
    tools = IncidentTools(pub)
    parts = [f"Alerts:\n{tools.t_get_alerts()}", f"Changes:\n{tools.t_get_changes()}",
             "Correlation engine shortlist (earliest unexplained anomaly first): " + ", ".join(g["candidates"])]
    for s in g["candidates"]:
        parts.append(f"## {s}\n{tools.t_get_topology(s)}\nMetrics:\n{tools.t_get_metrics(s)}\nLogs:\n{tools.t_get_logs(s)}")
    return one_answer(incident, llm, config, "\n\n".join(parts), {"candidates": g["candidates"]})


def with_root_injection(incident: dict) -> dict:
    """Copy of the incident with the injected instruction added to the root service's own log."""
    from .simulate import INJECTION

    logs = dict(incident["logs"])
    logs[incident["root"]] = sorted([*logs[incident["root"]], f"{incident['t0'] + 1:02d}m WARN {INJECTION}"])
    return {**incident, "logs": logs}


def run_hybrid_injected(incident: dict, llm, config: str) -> dict:
    return run_hybrid(with_root_injection(incident), llm, config)


def run_rules(incident: dict, name: str) -> dict:
    t0 = time.perf_counter()
    r = RULES[name](public_view(incident))
    ans = {"root_service": r["root"], "fault_type": r["fault"], "action": r["action"], "candidates": r["candidates"]}
    return result(incident, name, "-", ans, "answered", t0, 0, 0, 0, 0, 0, [])
