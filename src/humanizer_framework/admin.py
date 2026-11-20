from __future__ import annotations

import argparse
import hmac
import importlib.metadata
import json
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .env import load_env
from .errors import GenerationValidationError, ProviderExecutionError
from .framework import CommunicationFramework
from .models import CommunicationRequest, Message, MessageType, VoiceProfile
from .policies import PolicyRegistry
from .providers import MockProvider, default_provider
from .telemetry import provider_snapshot, telemetry_path


_STATIC_DIR = Path(__file__).with_name("admin_static")
_MODE_LABELS = {
    "outreach": ("Первое обращение", "Первое сообщение новому собеседнику."),
    "application": ("Отклик на вакансию", "Предметный отклик с опорой на факты о кандидате."),
    "channel_post": ("Публикация", "Самостоятельный текст для канала или публикации."),
    "chat_reply": ("Ответ в переписке", "Продолжение существующего диалога."),
    "follow_up": ("Повторное обращение", "Ненавязчивое напоминание после предыдущего контакта."),
    "scheduling": ("Согласование времени", "Обсуждение времени и организационных деталей."),
    "objection": ("Ответ на возражение", "Предметный ответ на сомнение собеседника."),
}
_DOMAIN_LABELS = {
    "generic": "Общая коммуникация",
    "tutoring": "Обучение",
    "job_search": "Поиск работы",
}
_CHANNEL_LABELS = {
    "generic": "Общий",
    "profi": "Profi",
    "repetit": "Repetit",
    "repetitor": "Repetitor (legacy)",
    "hh": "HeadHunter",
    "telegram": "Telegram",
}
_LANGUAGE_LABELS = {"ru": "Русский", "en": "English", "es": "Español", "zh": "中文"}


class VoiceInput(BaseModel):
    id: str = Field(default="default", max_length=80)
    description: str = Field(default="", max_length=1000)
    prefer: list[str] = Field(default_factory=list, max_length=8)
    avoid: list[str] = Field(default_factory=list, max_length=8)
    examples: list[str] = Field(default_factory=list, max_length=3)


class GenerateInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=3000)
    source_text: str = Field(default="", max_length=1800)
    message_type: str = Field(default="channel_post", max_length=40)
    domain: str = Field(default="generic", max_length=80)
    channel: str = Field(default="generic", max_length=80)
    language: str = Field(default="ru", max_length=20)
    profile: str = Field(default="default", max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
    business_rules: list[str] = Field(default_factory=list, max_length=8)
    voice: VoiceInput | None = None


def _is_loopback(host: str | None) -> bool:
    return host in {"127.0.0.1", "::1", "localhost", "testclient", "testserver"}


def _allowed_hosts() -> set[str]:
    configured = os.environ.get("HUMANIZER_ADMIN_ALLOWED_HOSTS", "localhost,127.0.0.1,::1")
    return {item.strip().lower() for item in configured.split(",") if item.strip()}


def _build_request(payload: GenerateInput) -> CommunicationRequest:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Укажите задачу для генерации.")

    try:
        message_type = MessageType(payload.message_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Неизвестный режим генерации.") from exc

    registry = PolicyRegistry()
    if payload.domain not in registry.domains:
        raise HTTPException(status_code=422, detail="Неизвестная сфера коммуникации.")
    if payload.channel not in registry.channels:
        raise HTTPException(status_code=422, detail="Неизвестный канал.")
    language = payload.language.split("-", 1)[0].split("_", 1)[0].lower()
    if language not in registry.languages:
        raise HTTPException(status_code=422, detail="Выберите поддерживаемый язык.")

    try:
        context_size = len(json.dumps(payload.context, ensure_ascii=False, default=str))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="Контекст должен быть JSON-совместимым."
        ) from exc
    if context_size > 3500:
        raise HTTPException(
            status_code=422,
            detail="Контекст слишком большой. Максимальный размер: 3500 символов.",
        )
    if len(payload.business_rules) > 8 or any(len(rule) > 500 for rule in payload.business_rules):
        raise HTTPException(
            status_code=422,
            detail="Можно добавить не более 8 правил длиной до 500 символов каждое.",
        )

    voice = None
    if payload.voice and any(
        (
            payload.voice.description.strip(),
            payload.voice.prefer,
            payload.voice.avoid,
            payload.voice.examples,
        )
    ):
        voice = VoiceProfile(
            id=payload.voice.id.strip() or "custom",
            description=payload.voice.description.strip(),
            prefer=[item.strip() for item in payload.voice.prefer if item.strip()][:8],
            avoid=[item.strip() for item in payload.voice.avoid if item.strip()][:8],
            examples=[item.strip() for item in payload.voice.examples if item.strip()][:3],
        )

    rules = [f"Цель сообщения - {prompt}"]
    rules.extend(rule.strip() for rule in payload.business_rules if rule.strip())
    conversation = (
        [Message("user", payload.source_text.strip())] if payload.source_text.strip() else []
    )
    return CommunicationRequest(
        channel=payload.channel,
        domain=payload.domain,
        message_type=message_type,
        language=payload.language,
        profile=payload.profile.strip() or "default",
        conversation=conversation,
        context=payload.context,
        business_rules=rules,
        voice=voice,
    )


def _plan_payload(plan: Any) -> dict[str, Any]:
    return {
        "act": getattr(plan.act, "value", str(plan.act)),
        "stage": getattr(plan.stage, "value", str(plan.stage)),
        "action": getattr(plan.action, "value", str(plan.action)),
        "target_length": getattr(plan.target_length, "value", str(plan.target_length)),
        "ask_question": plan.ask_question,
        "allow_cta": plan.allow_cta,
        "max_chars": plan.max_chars,
        "rationale": plan.rationale,
    }


def _issue_payload(issue: Any) -> dict[str, Any]:
    return {"code": issue.code, "message": issue.message, "hard": issue.hard}


def _activity_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(item.get("status") == "success" for item in items)
    failures = sum(item.get("status") == "error" for item in items)
    durations = [
        item.get("elapsed_ms") for item in items if isinstance(item.get("elapsed_ms"), (int, float))
    ]
    issue_counts = Counter(
        issue for item in items for issue in item.get("issues", []) if isinstance(issue, str)
    )
    return {
        "shown": len(items),
        "successes": successes,
        "failures": failures,
        "average_ms": round(sum(durations) / len(durations)) if durations else None,
        "rewritten": sum(bool(item.get("rewritten")) for item in items),
        "top_issues": [{"code": key, "count": count} for key, count in issue_counts.most_common(5)],
    }


def _read_activity(limit: int) -> dict[str, Any]:
    path = telemetry_path()
    if path is None:
        return {"enabled": False, "items": [], "summary": None}
    try:
        if not path.is_file():
            return {"enabled": True, "items": [], "summary": _activity_summary([])}
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 1_048_576))
            raw = handle.read()
        rows = raw.decode("utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return {"enabled": True, "items": [], "summary": _activity_summary([]), "read_error": True}

    allowed = (
        "timestamp",
        "status",
        "elapsed_ms",
        "calls",
        "attempts",
        "repair_attempted",
        "rewritten",
        "project",
        "channel",
        "domain",
        "message_type",
        "profile",
        "language",
        "provider",
        "model",
        "usage_totals",
        "provider_error_count",
        "issues",
        "error_type",
        "error",
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        try:
            event = json.loads(row)
        except (json.JSONDecodeError, TypeError):
            continue
        if event.get("event") != "generation":
            continue
        item = {key: event[key] for key in allowed if key in event}
        if isinstance(item.get("usage_totals"), list):
            item["usage_totals"] = [
                {
                    "provider": str(usage.get("provider", "unknown"))[:120],
                    "model": str(usage.get("model", "unknown"))[:120],
                    **{
                        str(key)[:50]: value
                        for key, value in usage.items()
                        if isinstance(value, (int, float)) and not isinstance(value, bool)
                    },
                }
                for usage in item["usage_totals"][:10]
                if isinstance(usage, dict)
            ]
        if isinstance(item.get("issues"), list):
            item["issues"] = [str(value)[:80] for value in item["issues"][:20]]
        items.append(item)
    items.reverse()
    return {"enabled": True, "items": items, "summary": _activity_summary(items)}


def _provider_status() -> dict[str, Any]:
    load_env()
    key_state = {
        "zai": any(
            os.environ.get(name)
            for name in ("ZAI_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")
        ),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "opencode_cli": shutil.which("opencode") is not None,
    }
    try:
        provider = default_provider()
        providers = getattr(provider, "providers", [provider])
        chain = []
        for item in providers:
            name = getattr(item, "name", type(item).__name__)
            model = getattr(item, "model", None)
            if name == "zai-http":
                ready = key_state["zai"]
                detail = "Ключ найден" if ready else "Не найден API-ключ Z.AI"
            elif name == "opencode-cli" and str(model or "").startswith("openai-api/"):
                ready = key_state["opencode_cli"] and key_state["openai"]
                detail = (
                    "OpenCode CLI и OPENAI_API_KEY найдены"
                    if ready
                    else "Нужны OpenCode CLI и OPENAI_API_KEY"
                )
            elif name == "opencode-cli":
                ready = key_state["opencode_cli"]
                detail = (
                    "CLI найден; авторизация отдельно не проверялась"
                    if ready
                    else "OpenCode CLI не найден в PATH"
                )
            elif "openai" in str(name).lower():
                ready = key_state["openai"]
                detail = "OPENAI_API_KEY найден" if ready else "OPENAI_API_KEY не задан"
            else:
                ready = None
                detail = "Провайдер доступен через конфигурацию"
            chain.append(
                {
                    "name": str(name),
                    "model": str(model) if model else None,
                    "ready": ready,
                    "detail": detail,
                }
            )
    except Exception as exc:
        chain = [{"name": "default", "model": None, "ready": False, "detail": type(exc).__name__}]

    path = telemetry_path()
    try:
        telemetry_exists = bool(path and path.is_file())
    except OSError:
        telemetry_exists = False
    try:
        version = importlib.metadata.version("humanizer-framework")
    except importlib.metadata.PackageNotFoundError:
        version = "source checkout"
    return {
        "version": version,
        "python": sys.version.split()[0],
        "provider_chain": chain,
        "credentials": key_state,
        "telemetry": {
            "enabled": path is not None,
            "file": path.name if path is not None else None,
            "exists": telemetry_exists,
        },
    }


def create_app() -> FastAPI:
    load_env()
    app = FastAPI(
        title="Humanizer Framework Admin", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.middleware("http")
    async def protect_admin(request: Request, call_next):
        hostname = (request.url.hostname or "").lower()
        if hostname not in _allowed_hosts():
            return JSONResponse(status_code=400, content={"detail": "Host is not allowed."})

        client_host = request.client.host if request.client else None
        token = os.environ.get("HUMANIZER_ADMIN_TOKEN", "")
        if not _is_loopback(client_host) and not token:
            return JSONResponse(
                status_code=403,
                content={"detail": "Remote access requires HUMANIZER_ADMIN_TOKEN."},
            )
        if token and request.url.path.startswith("/api/"):
            supplied = request.headers.get("authorization", "")
            if not hmac.compare_digest(supplied, f"Bearer {token}"):
                return JSONResponse(status_code=401, content={"detail": "Admin token required."})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(_STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health():
        return {"ok": True, "service": "humanizer-framework-admin"}

    @app.get("/api/options")
    def options():
        registry = PolicyRegistry()
        return {
            "modes": [
                {"value": key, "label": value[0], "description": value[1]}
                for key, value in _MODE_LABELS.items()
            ],
            "domains": [
                {"value": key, "label": _DOMAIN_LABELS.get(key, key)} for key in registry.domains
            ],
            "channels": [
                {"value": key, "label": _CHANNEL_LABELS.get(key, key)} for key in registry.channels
            ],
            "languages": [
                {"value": key, "label": _LANGUAGE_LABELS.get(key, key)}
                for key in registry.languages
            ],
        }

    @app.get("/api/status")
    def status():
        return _provider_status()

    @app.get("/api/activity")
    def activity(limit: int = Query(default=100, ge=1, le=200)):
        return _read_activity(limit)

    @app.post("/api/preview")
    def preview(payload: GenerateInput):
        request = _build_request(payload)
        package = CommunicationFramework(provider=MockProvider("")).prepare(request)
        return {
            "plan": _plan_payload(package.plan),
            "constraints": {
                "max_chars": package.constraints.max_chars,
                "max_questions": package.constraints.max_questions,
                "forbid_em_dash": package.constraints.forbid_em_dash,
                "forbid_colon": package.constraints.forbid_colon,
                "forbid_smileys": package.constraints.forbid_smileys,
                "replace_yo": package.constraints.replace_yo,
            },
            "messages": package.messages,
        }

    @app.post("/api/generate")
    def generate(payload: GenerateInput):
        request = _build_request(payload)
        framework = CommunicationFramework()
        started = time.perf_counter()
        try:
            result = framework.generate(request)
        except GenerationValidationError as exc:
            return JSONResponse(
                status_code=422,
                content={
                    "ok": False,
                    "error": "Результат не прошел обязательные проверки.",
                    "error_type": type(exc).__name__,
                    "text": exc.last_text,
                    "issues": [_issue_payload(issue) for issue in exc.issues],
                    "valid": False,
                },
            )
        except ProviderExecutionError as exc:
            return JSONResponse(
                status_code=502,
                content={"ok": False, "error": str(exc), "error_type": type(exc).__name__},
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "error": "Внутренняя ошибка. Проверьте конфигурацию и серверный вывод.",
                    "error_type": type(exc).__name__,
                },
            )

        provider_info = provider_snapshot(framework.provider)
        return {
            "ok": True,
            "text": result.text,
            "valid": result.valid,
            "provider": result.provider,
            "model": provider_info.get("model"),
            "rewritten": result.rewritten,
            "issues": [_issue_payload(issue) for issue in result.issues],
            "plan": _plan_payload(result.plan),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }

    return app


app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Humanizer Framework local admin panel")
    parser.add_argument(
        "--host",
        default=os.environ.get("HUMANIZER_ADMIN_HOST", "127.0.0.1"),
        help="Bind address. Non-loopback hosts require HUMANIZER_ADMIN_TOKEN.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("HUMANIZER_ADMIN_PORT", "8765")),
        help="HTTP port (default: 8765).",
    )
    args = parser.parse_args()
    token = os.environ.get("HUMANIZER_ADMIN_TOKEN", "")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not token:
        parser.error("Remote binding requires HUMANIZER_ADMIN_TOKEN to be set.")
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Admin dependencies are missing. Install with: pip install -e '.[admin]'"
        ) from exc
    uvicorn.run("humanizer_framework.admin:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
