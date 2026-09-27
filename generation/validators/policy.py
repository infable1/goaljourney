"""Product capabilities (POL-A) and evidence confidence semantics (POL-B).

Both policies are data: configs/product_capabilities.yaml and configs/evidence_policy.yaml. This
module turns them into the questions the linter asks:

* is a verification method / an evidence source / a promise backed by an *available* capability?
* what is the highest confidence a protocol's required methods (or a result's evidence) can support?
"""
import re
from functools import lru_cache

from gjcore.config import load_config

# Confidence ranks. `low` exists only on verification results (insufficient evidence).
RANK = {"low": 0, "limited": 1, "medium": 2, "high": 3}
LOW_CLASSES = {"self_report", "user_entered_data"}


@lru_cache(maxsize=None)
def capabilities():
    return load_config("product_capabilities")


@lru_cache(maxsize=None)
def evidence_policy():
    return load_config("evidence_policy")


def capability_status(cap_id):
    return (capabilities()["capabilities"].get(cap_id) or {}).get("status", "unknown")


def method_capability(method):
    return capabilities()["methods"].get(method)


def unavailable_method(method):
    """(capability, status) if `method` needs a capability that is not available, else None."""
    cap = method_capability(method)
    if cap and capability_status(cap) != "available":
        return cap, capability_status(cap)
    return None


def unavailable_evidence(item):
    """(capability, status) if an input evidence item could not have reached the model, else None."""
    cfg = capabilities()
    caps = []
    if item.get("type") in cfg.get("evidence_types", {}):
        caps.append(cfg["evidence_types"][item["type"]])
    src = item.get("description_source")
    if src in cfg.get("evidence_description_sources", {}):
        caps.append(cfg["evidence_description_sources"][src])
    for cap in caps:
        if capability_status(cap) != "available":
            return cap, capability_status(cap)
    return None


@lru_cache(maxsize=None)
def _promise_res():
    out = []
    for cap, patterns in (capabilities().get("promise_patterns") or {}).items():
        for p in patterns:
            out.append((cap, re.compile(p, re.IGNORECASE)))
    return out


def capability_promises(text):
    """Yield (capability, status, match) for promises/requests that need a non-available capability."""
    for cap, rx in _promise_res():
        if capability_status(cap) == "available":
            continue
        m = rx.search(text or "")
        if m:
            yield cap, capability_status(cap), m


# ----------------------------------------------------------------------------- evidence classes

def class_ceiling(cls):
    return (evidence_policy()["classes"].get(cls) or {}).get("ceiling", "limited")


def method_class(method_spec):
    return method_spec.get("evidence_class") or evidence_policy()["method_class"].get(method_spec.get("method"), "self_report")


def _max_level(levels):
    return max(levels, key=lambda lv: RANK[lv]) if levels else "limited"


def protocol_support(protocol):
    """Highest confidence the protocol's *required* methods can support, and their classes.

    * each class has a ceiling (self_report / user_entered_data / image_description: limited;
      inspectable_artifact / externally_verifiable: high);
    * user-entered data reaches medium when every row carries a checkable reference
      (references_required) and the protocol spot-checks references with url_review;
    * an image description reaches medium together with another required non-image method;
    * several methods: the highest class present (two self-reports are still limited).
    """
    methods = protocol.get("methods") or []
    required = [m for m in methods if m.get("role") == "required"]
    has_url_check = any(m.get("method") == "url_review" for m in methods)
    classes = [method_class(m) for m in required]
    levels = []
    for m, cls in zip(required, classes):
        lv = class_ceiling(cls)
        if cls == "user_entered_data" and m.get("references_required") and has_url_check:
            lv = _max_level([lv, "medium"])
        if cls == "image_description" and any(c != "image_description" for c in classes):
            lv = _max_level([lv, "medium"])
        levels.append(lv)
    return _max_level(levels), classes


def protocol_is_users_word(protocol):
    """True if every required method is the user's own word (self-report or unreferenced user data)."""
    support, classes = protocol_support(protocol)
    return bool(classes) and set(classes) <= LOW_CLASSES and support == "limited"


def evidence_item_class(item):
    t = item.get("type")
    if t == "answers":
        return "inspectable_artifact" if item.get("responds_to") in {"knowledge_test", "practical_test"} else "self_report"
    if t == "url":
        return "externally_verifiable" if item.get("description_source") == "system_fetch" else "user_entered_data"
    return evidence_policy()["evidence_class"].get(t, "self_report")


def evidence_support(items):
    """Highest confidence the submitted evidence items can support, and their classes."""
    classes = [evidence_item_class(i) for i in items]
    levels = []
    for cls in classes:
        lv = class_ceiling(cls)
        if cls == "image_description" and any(c != "image_description" for c in classes):
            lv = _max_level([lv, "medium"])
        levels.append(lv)
    return _max_level(levels), classes
