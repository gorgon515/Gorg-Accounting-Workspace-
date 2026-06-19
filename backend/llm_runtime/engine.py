import sqlite3, uuid, time, json
from pathlib import Path
from typing import Optional

_DB = Path.home() / ".helios" / "llm_runtime.db"

_BUILTIN_MODELS = [
    {"name": "gpt-4o", "provider": "openai", "context_window": 128000, "cost_per_1k": 0.005,
     "capabilities": ["chat","reasoning","analysis","code","extraction"], "local": False, "gpu_required": False},
    {"name": "gpt-4o-mini", "provider": "openai", "context_window": 128000, "cost_per_1k": 0.00015,
     "capabilities": ["chat","summarization","classification"], "local": False, "gpu_required": False},
    {"name": "claude-opus-4-8", "provider": "anthropic", "context_window": 200000, "cost_per_1k": 0.015,
     "capabilities": ["chat","reasoning","analysis","code"], "local": False, "gpu_required": False},
    {"name": "claude-sonnet-4-6", "provider": "anthropic", "context_window": 200000, "cost_per_1k": 0.003,
     "capabilities": ["chat","analysis","extraction"], "local": False, "gpu_required": False},
    {"name": "llama3-8b-local", "provider": "ollama", "context_window": 8192, "cost_per_1k": 0.0,
     "capabilities": ["chat","summarization"], "local": True, "gpu_required": False},
    {"name": "mistral-7b-local", "provider": "ollama", "context_window": 32768, "cost_per_1k": 0.0,
     "capabilities": ["chat","reasoning","code"], "local": True, "gpu_required": True},
]


class LLMRuntime:
    _instance = None

    def __init__(self):
        self._db = str(_DB)
        _DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_models()

    def _init_db(self):
        with sqlite3.connect(self._db) as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS model (
                id TEXT PRIMARY KEY, name TEXT UNIQUE, provider TEXT,
                context_window INTEGER, cost_per_1k REAL,
                capabilities_json TEXT, local INTEGER, gpu_required INTEGER,
                registered_at REAL, enabled INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS inference_log (
                id TEXT PRIMARY KEY, model TEXT, prompt_tokens INTEGER,
                completion_tokens INTEGER, latency_ms REAL, task_type TEXT, ts REAL
            );
            CREATE TABLE IF NOT EXISTS response_cache (
                id TEXT PRIMARY KEY, prompt_hash TEXT UNIQUE, response TEXT,
                model TEXT, tokens INTEGER, created_at REAL, accessed_at REAL
            );
            """)

    def _seed_models(self):
        with sqlite3.connect(self._db) as c:
            for m in _BUILTIN_MODELS:
                exists = c.execute("SELECT 1 FROM model WHERE name=?", (m["name"],)).fetchone()
                if not exists:
                    c.execute(
                        "INSERT INTO model VALUES (?,?,?,?,?,?,?,?,?,1)",
                        (str(uuid.uuid4()), m["name"], m["provider"], m["context_window"],
                         m["cost_per_1k"], json.dumps(m["capabilities"]),
                         int(m["local"]), int(m["gpu_required"]), time.time())
                    )

    def _row_to_model(self, row) -> dict:
        cols = ["id","name","provider","context_window","cost_per_1k",
                "capabilities_json","local","gpu_required","registered_at","enabled"]
        d = dict(zip(cols, row))
        d["capabilities"] = json.loads(d.pop("capabilities_json"))
        d["local"] = bool(d["local"])
        d["gpu_required"] = bool(d["gpu_required"])
        d["enabled"] = bool(d["enabled"])
        return d

    def register_model(self, name: str, provider: str, context_window: int = 4096,
                       cost_per_1k: float = 0.0, capabilities: Optional[list] = None,
                       local: bool = False, gpu_required: bool = False) -> dict:
        mid = str(uuid.uuid4())
        now = time.time()
        caps = capabilities or ["chat"]
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT OR REPLACE INTO model VALUES (?,?,?,?,?,?,?,?,?,1)",
                (mid, name, provider, context_window, cost_per_1k,
                 json.dumps(caps), int(local), int(gpu_required), now)
            )
        return self.get_model(name)

    def list_models(self, local_only: bool = False, capability: str = "") -> list:
        with sqlite3.connect(self._db) as c:
            if local_only:
                rows = c.execute("SELECT * FROM model WHERE enabled=1 AND local=1").fetchall()
            else:
                rows = c.execute("SELECT * FROM model WHERE enabled=1").fetchall()
        models = [self._row_to_model(r) for r in rows]
        if capability:
            models = [m for m in models if capability in m["capabilities"]]
        return models

    def get_model(self, name: str) -> Optional[dict]:
        with sqlite3.connect(self._db) as c:
            row = c.execute("SELECT * FROM model WHERE name=?", (name,)).fetchone()
        return self._row_to_model(row) if row else None

    def route_task(self, task_type: str, context_length: int = 0,
                   requires_local: bool = False) -> dict:
        models = self.list_models(local_only=requires_local)
        if task_type == "embedding":
            local_pref = [m for m in models if m["local"] and task_type in m["capabilities"]]
            if local_pref:
                return {"model": local_pref[0]["name"], "reason": "local embedding model preferred"}
        capable = [m for m in models if task_type in m["capabilities"]]
        if not capable:
            capable = models
        if task_type == "reasoning":
            capable.sort(key=lambda m: m["context_window"], reverse=True)
        else:
            capable.sort(key=lambda m: m["cost_per_1k"])
        if capable:
            chosen = capable[0]
            return {"model": chosen["name"], "provider": chosen["provider"],
                    "context_window": chosen["context_window"], "reason": f"best for {task_type}"}
        return {"model": "gpt-4o-mini", "reason": "fallback default"}

    def budget_context(self, messages: list, max_tokens: int = 4000) -> list:
        result = []
        token_est = 0
        for msg in reversed(messages):
            content = msg.get("content", "")
            est = len(content) // 4 + 4
            if token_est + est > max_tokens:
                break
            result.insert(0, msg)
            token_est += est
        return result

    def optimize_prompt(self, prompt: str, task_type: str = "chat") -> str:
        prompt = prompt.strip()
        prefixes = {
            "summarization": "Please provide a concise summary:\n\n",
            "classification": "Classify the following:\n\n",
            "extraction": "Extract the requested information:\n\n",
            "code": "You are an expert programmer. ",
            "analysis": "Provide a thorough analysis:\n\n",
        }
        if task_type in prefixes and not prompt.startswith(prefixes[task_type]):
            prompt = prefixes[task_type] + prompt
        return " ".join(prompt.split())

    def cache_response(self, prompt_hash: str, response: str,
                       model: str, tokens: int = 0) -> dict:
        cid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT OR REPLACE INTO response_cache VALUES (?,?,?,?,?,?,?)",
                (cid, prompt_hash, response, model, tokens, now, now)
            )
        return {"id": cid, "prompt_hash": prompt_hash, "model": model,
                "tokens": tokens, "created_at": now}

    def get_cached(self, prompt_hash: str, ttl_sec: float = 3600) -> Optional[dict]:
        cutoff = time.time() - ttl_sec
        with sqlite3.connect(self._db) as c:
            row = c.execute(
                "SELECT * FROM response_cache WHERE prompt_hash=? AND created_at > ?",
                (prompt_hash, cutoff)
            ).fetchone()
        if not row:
            return None
        cols = ["id","prompt_hash","response","model","tokens","created_at","accessed_at"]
        d = dict(zip(cols, row))
        with sqlite3.connect(self._db) as c:
            c.execute("UPDATE response_cache SET accessed_at=? WHERE id=?", (time.time(), d["id"]))
        return d

    def record_inference(self, model: str, prompt_tokens: int, completion_tokens: int,
                         latency_ms: float, task_type: str = "chat") -> dict:
        lid = str(uuid.uuid4())
        now = time.time()
        with sqlite3.connect(self._db) as c:
            c.execute(
                "INSERT INTO inference_log VALUES (?,?,?,?,?,?,?)",
                (lid, model, prompt_tokens, completion_tokens, latency_ms, task_type, now)
            )
        return {"id": lid, "model": model, "latency_ms": latency_ms, "ts": now}

    def inference_metrics(self, model: str = "", hours: float = 24.0) -> dict:
        cutoff = time.time() - hours * 3600
        with sqlite3.connect(self._db) as c:
            if model:
                rows = c.execute(
                    "SELECT latency_ms, prompt_tokens+completion_tokens FROM inference_log WHERE model=? AND ts>?",
                    (model, cutoff)
                ).fetchall()
                total_calls = c.execute(
                    "SELECT COUNT(*) FROM inference_log WHERE model=? AND ts>?", (model, cutoff)
                ).fetchone()[0]
            else:
                rows = c.execute(
                    "SELECT latency_ms, prompt_tokens+completion_tokens FROM inference_log WHERE ts>?",
                    (cutoff,)
                ).fetchall()
                total_calls = c.execute(
                    "SELECT COUNT(*) FROM inference_log WHERE ts>?", (cutoff,)
                ).fetchone()[0]
        if not rows:
            return {"total_calls": 0, "avg_latency_ms": 0, "p95_latency_ms": 0,
                    "total_tokens": 0, "model": model or "all"}
        latencies = sorted([r[0] for r in rows])
        total_tokens = sum(r[1] for r in rows)
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0
        return {"total_calls": total_calls, "avg_latency_ms": round(avg_lat, 1),
                "p95_latency_ms": round(p95_lat, 1), "total_tokens": total_tokens,
                "model": model or "all"}

    def detect_gpu(self) -> dict:
        try:
            import torch
            available = torch.cuda.is_available()
            devices = []
            vram_gb = 0.0
            if available:
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    vram = props.total_memory / 1e9
                    devices.append({"index": i, "name": props.name, "vram_gb": round(vram, 2)})
                    vram_gb += vram
            return {"available": available, "devices": devices, "vram_gb": round(vram_gb, 2),
                    "backend": "cuda"}
        except ImportError:
            pass
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                devices = []
                vram_gb = 0.0
                for line in result.stdout.strip().splitlines():
                    parts = line.split(",")
                    name = parts[0].strip()
                    mem_mib = float(parts[1].strip().split()[0]) if len(parts) > 1 else 0
                    vram = mem_mib / 1024
                    devices.append({"name": name, "vram_gb": round(vram, 2)})
                    vram_gb += vram
                return {"available": True, "devices": devices, "vram_gb": round(vram_gb, 2), "backend": "nvidia-smi"}
        except Exception:
            pass
        return {"available": False, "devices": [], "vram_gb": 0.0, "backend": "none"}

    def benchmark_model(self, name: str, test_prompt: str = "Hello, how are you?") -> dict:
        model = self.get_model(name)
        if not model:
            return {"error": f"Model {name} not found"}
        start = time.time()
        tokens_est = len(test_prompt.split())
        time.sleep(0.05)
        elapsed_ms = (time.time() - start) * 1000
        tokens_per_sec = tokens_est / max(elapsed_ms / 1000, 0.001)
        return {"model": name, "latency_ms": round(elapsed_ms, 1),
                "tokens_per_sec": round(tokens_per_sec, 1),
                "test_prompt_tokens": tokens_est, "local": model["local"]}

    def performance_report(self) -> dict:
        models = self.list_models()
        gpu = self.detect_gpu()
        metrics_by_model = {}
        for m in models:
            metrics_by_model[m["name"]] = self.inference_metrics(m["name"])
        cache_count = 0
        with sqlite3.connect(self._db) as c:
            cache_count = c.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
        return {"models": len(models), "gpu": gpu, "cache_entries": cache_count,
                "metrics_by_model": metrics_by_model,
                "generated_at": time.time()}

    def stats(self) -> dict:
        with sqlite3.connect(self._db) as c:
            total_models = c.execute("SELECT COUNT(*) FROM model WHERE enabled=1").fetchone()[0]
            local_models = c.execute("SELECT COUNT(*) FROM model WHERE enabled=1 AND local=1").fetchone()[0]
            total_calls = c.execute("SELECT COUNT(*) FROM inference_log").fetchone()[0]
            cache_entries = c.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
        return {"total_models": total_models, "local_models": local_models,
                "total_inference_calls": total_calls, "cache_entries": cache_entries}


_instance: Optional[LLMRuntime] = None


def get_llm_runtime() -> LLMRuntime:
    global _instance
    if _instance is None:
        _instance = LLMRuntime()
    return _instance
