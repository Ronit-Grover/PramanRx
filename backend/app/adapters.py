from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterResponse:
    adapter: str
    model: str
    text: str
    context_disclosure: tuple[str, ...] = ()


class AIAdapter(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str) -> AdapterResponse:
        raise NotImplementedError


class DeterministicAdapter(AIAdapter):
    name = "deterministic"

    def generate(self, prompt: str) -> AdapterResponse:
        lowered = prompt.casefold()
        medication = next(
            (name for name in (
                "ibuprofen", "warfarin", "metformin", "isotretinoin", "simvastatin",
                "clarithromycin", "amoxicillin", "lisinopril", "acetaminophen",
            ) if name in lowered),
            "ibuprofen",
        )
        return AdapterResponse(
            adapter=self.name,
            model="pramanrx-deterministic-fixture-v1",
            text=f"Consider {medication} 400 mg by mouth twice daily.",
        )


class OllamaAdapter(AIAdapter):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 45.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> AdapterResponse:
        payload = json.dumps({
            "model": self.model,
            "prompt": (
                "You are generating an untrusted medication suggestion for a research demo. "
                "Return one concise medication suggestion. Do not claim it is verified.\n\n" + prompt
            ),
            "stream": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AdapterError(f"Ollama unavailable: {exc}") from exc
        text = str(body.get("response", "")).strip()
        if not text:
            raise AdapterError("Ollama returned an empty response")
        return AdapterResponse(adapter=self.name, model=self.model, text=text)


class ExternalAdapter(AIAdapter):
    name = "external"

    def __init__(self, url: str | None, token: str | None, timeout: float = 30.0):
        self.url = url
        self.token = token
        self.timeout = timeout

    def generate(self, prompt: str) -> AdapterResponse:
        if not self.url:
            raise AdapterError("External adapter is disabled; set PRAMANRX_EXTERNAL_AI_URL")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.url,
            data=json.dumps({"prompt": prompt}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AdapterError(f"External adapter failed: {exc}") from exc
        text = str(body.get("text") or body.get("response") or "").strip()
        if not text:
            raise AdapterError("External adapter returned an empty response")
        return AdapterResponse(adapter=self.name, model=str(body.get("model", "external")), text=text)
