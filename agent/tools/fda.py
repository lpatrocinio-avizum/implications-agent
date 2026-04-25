"""FDA and drug data tools using public APIs (RxNorm, openFDA)."""

import httpx

_TIMEOUT = 15


def resolve_drug(drug_name: str) -> dict:
    """Normalize a drug name to canonical identifiers via RxNorm."""
    # Step 1: Fuzzy match to get RxCUI candidates
    resp = httpx.get(
        "https://rxnav.nlm.nih.gov/REST/approximateTerm.json",
        params={"term": drug_name, "maxEntries": 5},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    candidates = resp.json().get("approximateGroup", {}).get("candidate", [])

    if not candidates:
        return {"error": f"No RxNorm match found for '{drug_name}'"}

    rxcui = candidates[0].get("rxcui")
    if not rxcui:
        return {"error": f"No RxCUI returned for '{drug_name}'"}

    # Step 2: Get all related names (brand, generic, ingredient, etc.)
    resp2 = httpx.get(
        f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json",
        timeout=_TIMEOUT,
    )
    resp2.raise_for_status()

    groups = resp2.json().get("allRelatedGroup", {}).get("conceptGroup", [])

    result = {
        "rxcui": rxcui,
        "query": drug_name,
        "brands": [],
        "generics": [],
        "ingredients": [],
    }

    tty_map = {
        "BN": "brands",       # Brand Name
        "SBD": "brands",      # Semantic Branded Drug
        "IN": "ingredients",   # Ingredient
        "MIN": "ingredients",  # Multiple Ingredients
        "SCD": "generics",    # Semantic Clinical Drug
        "SCDF": "generics",   # Semantic Clinical Drug Form
    }

    for group in groups:
        tty = group.get("tty", "")
        target = tty_map.get(tty)
        if target and "conceptProperties" in group:
            for prop in group["conceptProperties"]:
                name = prop.get("name", "")
                if name and name not in result[target]:
                    result[target].append(name)

    # Step 3: Get drug class if available
    resp3 = httpx.get(
        f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json",
        params={"rxcui": rxcui, "relaSource": "ATC"},
        timeout=_TIMEOUT,
    )
    if resp3.status_code == 200:
        classes = resp3.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
        result["drug_classes"] = list({
            c.get("rxclassMinConceptItem", {}).get("className", "")
            for c in classes
            if c.get("rxclassMinConceptItem", {}).get("className")
        })

    return result


def get_drug_label(drug_name: str) -> dict:
    """Get FDA-approved prescribing information from openFDA."""
    search = f'openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}"'
    resp = httpx.get(
        "https://api.fda.gov/drug/label.json",
        params={"search": search, "limit": 1},
        timeout=_TIMEOUT,
    )

    if resp.status_code == 404:
        return {"error": f"No FDA label found for '{drug_name}'"}
    resp.raise_for_status()

    results = resp.json().get("results", [])
    if not results:
        return {"error": f"No FDA label found for '{drug_name}'"}

    label = results[0]

    # Extract key fields, truncate long ones
    max_chars = 2000
    fields = [
        "indications_and_usage",
        "dosage_and_administration",
        "warnings_and_cautions",
        "warnings",
        "contraindications",
        "drug_interactions",
        "adverse_reactions",
        "clinical_studies",
        "use_in_specific_populations",
    ]

    extracted = {}
    for field in fields:
        value = label.get(field)
        if value:
            text = value[0] if isinstance(value, list) else str(value)
            if len(text) > max_chars:
                text = text[:max_chars] + "... [truncated]"
            extracted[field] = text

    # Add openFDA metadata if present
    openfda = label.get("openfda", {})
    if openfda:
        extracted["brand_name"] = openfda.get("brand_name", [])
        extracted["generic_name"] = openfda.get("generic_name", [])
        extracted["manufacturer"] = openfda.get("manufacturer_name", [])
        extracted["route"] = openfda.get("route", [])
        extracted["product_type"] = openfda.get("product_type", [])

    return extracted


def get_adverse_events(drug_name: str, limit: int = 10) -> dict:
    """Get top reported adverse events for a drug from FDA FAERS."""
    # FAERS indexes primarily by generic name; try multiple search strategies
    searches = [
        f'patient.drug.openfda.generic_name:"{drug_name}"',
        f'patient.drug.openfda.brand_name:"{drug_name}"',
        f'patient.drug.medicinalproduct:"{drug_name}"',
    ]

    data = None
    used_search = None
    for search in searches:
        resp = httpx.get(
            "https://api.fda.gov/drug/event.json",
            params={
                "search": search,
                "count": "patient.reaction.reactionmeddrapt.exact",
                "limit": limit,
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            used_search = search
            break

    if data is None:
        return {"error": f"No adverse event data found for '{drug_name}'"}

    reactions = data.get("results", [])

    # Also get total report count
    total_resp = httpx.get(
        "https://api.fda.gov/drug/event.json",
        params={"search": used_search, "limit": 1},
        timeout=_TIMEOUT,
    )
    total = 0
    if total_resp.status_code == 200:
        total = total_resp.json().get("meta", {}).get("results", {}).get("total", 0)

    return {
        "drug_name": drug_name,
        "total_reports": total,
        "top_adverse_reactions": [
            {"reaction": r.get("term", ""), "count": r.get("count", 0)}
            for r in reactions
        ],
    }


def get_drug_recalls(drug_name: str, limit: int = 5) -> dict:
    """Check for recent FDA recalls/enforcement actions on a drug."""
    search = f'openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}"'
    resp = httpx.get(
        "https://api.fda.gov/drug/enforcement.json",
        params={"search": search, "limit": limit, "sort": "report_date:desc"},
        timeout=_TIMEOUT,
    )

    if resp.status_code == 404:
        return {"drug_name": drug_name, "recalls": [], "message": "No recalls found"}
    resp.raise_for_status()

    results = resp.json().get("results", [])

    recalls = []
    for r in results:
        recalls.append({
            "classification": r.get("classification", ""),
            "reason": r.get("reason_for_recall", ""),
            "status": r.get("status", ""),
            "distribution": r.get("distribution_pattern", ""),
            "report_date": r.get("report_date", ""),
            "recall_initiation_date": r.get("recall_initiation_date", ""),
            "product_description": r.get("product_description", ""),
        })

    return {"drug_name": drug_name, "recalls": recalls}
