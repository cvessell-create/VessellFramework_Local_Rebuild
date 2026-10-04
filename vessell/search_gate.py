# Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
"""Offline, deterministic checks of operator-supplied search and licence records."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Literal


class ClaimType(str, Enum):
    REPO_IDENTITY = "repo/identity"
    LICENSE_IP = "licence/IP"
    LIVE_FACT = "live/current"
    CODE_EXISTENCE = "code/safety-check"
    PERSONAL_MEMORY = "personal-memory/external-account"
    VERSION_DEPENDENCY = "version/dependency"
    PEOPLE_ORGANISATIONS = "people/organisations"


class EvidenceStatus(str, Enum):
    WORKING_HYPOTHESIS = "WORKING HYPOTHESIS"
    SOURCE_ESTABLISHED = "SOURCE-ESTABLISHED"
    UNVERIFIED = "UNVERIFIED"


class GateStatus(str, Enum):
    CLEARED = "CLEARED"
    HYPOTHESIS_ONLY = "HYPOTHESIS ONLY"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"


class LicenseClass(str, Enum):
    PERMISSIVE = "PERMISSIVE"
    ATTRIBUTION = "ATTRIBUTION"
    SHARE_ALIKE = "SHARE-ALIKE"
    COPYLEFT_CODE = "COPYLEFT-CODE"
    PROPRIETARY = "PROPRIETARY"


@dataclass(frozen=True)
class SearchRecord:
    query: str
    tool: str
    scope: str
    result_count: int
    limit_hit: bool
    primary_source_opened: bool
    status: EvidenceStatus
    what_was_not_checked: str
    primary_source: str = ""
    corrected_name: str = ""

    def __post_init__(self) -> None:
        for name in (
            "query",
            "tool",
            "scope",
            "what_was_not_checked",
            "primary_source",
            "corrected_name",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
        if not all(value.strip() for value in (self.query, self.tool, self.scope)):
            raise ValueError("query, tool and scope must be nonempty.")
        if type(self.result_count) is not int or self.result_count < 0:
            raise ValueError("result_count must be a nonnegative integer.")
        if type(self.limit_hit) is not bool or type(self.primary_source_opened) is not bool:
            raise ValueError("limit_hit and primary_source_opened must be booleans.")
        object.__setattr__(self, "status", EvidenceStatus(self.status))


@dataclass(frozen=True)
class SearchGateResult:
    status: GateStatus
    reasons: tuple[str, ...]


def evaluate_claim(claim_type: ClaimType, records: list[SearchRecord]) -> SearchGateResult:
    """Evaluate records for one claim; clearance is not independent corroboration."""
    claim_type = ClaimType(claim_type)
    if not records:
        return SearchGateResult(GateStatus.BLOCKED, ("No search, no claim: no records supplied.",))
    reasons: list[str] = []
    established = False
    hypothesis = False
    for record in records:
        if record.limit_hit:
            reasons.append(
                f"Search limit hit: {record.result_count} results in scope {record.scope}; "
                "coverage is incomplete."
            )
        reasons.append(
            f"Scope: {record.scope}. NOT checked: {record.what_was_not_checked or 'none declared'}."
        )
        if record.corrected_name and claim_type is ClaimType.REPO_IDENTITY:
            reasons.append(
                f"Corrected repository name: {record.corrected_name}; state before writes."
            )
        if record.result_count == 0:
            reasons.append(
                f"NOT FOUND IN SCOPE: {record.scope}; absence is not proof of nonexistence."
            )
        elif (
            record.status is EvidenceStatus.SOURCE_ESTABLISHED
            and record.primary_source_opened
            and record.primary_source.strip()
        ):
            established = True
            reasons.append(f"Primary source opened: {record.primary_source}.")
        elif record.status is not EvidenceStatus.UNVERIFIED:
            hypothesis = True
            reasons.append("Summary or unconfirmed primary source remains a WORKING HYPOTHESIS.")
        else:
            reasons.append("Inaccessible or unverified content must not be invented.")
    if established:
        status = GateStatus.CLEARED
        reasons.append(
            "Search prerequisite cleared only for the supplied claim and scope; "
            "Evidence Assurance and the Harm Gate still apply. Derivative copies are not independent."
        )
        if claim_type is ClaimType.LIVE_FACT:
            reasons.append(
                "An opened snapshot establishes only that snapshot, not a final outcome."
            )
        if claim_type is ClaimType.LICENSE_IP:
            reasons.append(
                "Confirm the applicable COPYING/LICENSE and pass check_import before import."
            )
    elif hypothesis:
        status = GateStatus.HYPOTHESIS_ONLY
    else:
        status = GateStatus.UNVERIFIED
        if claim_type is ClaimType.PERSONAL_MEMORY:
            reasons.append(
                "Account or memory inaccessible/unverified; ask the user to paste material."
            )
    return SearchGateResult(status, tuple(reasons))


def _normalize_license(value: str) -> str:
    return value.strip().lower()


_GPL2_ONLY = {"gpl-2.0", "gpl-2.0-only", "gplv2"}
_GPL2_LATER = {"gpl-2.0+", "gpl-2.0(+)", "gpl-2.0-or-later", "gplv2+"}
_GPL3 = {"gpl-3.0", "gpl-3.0-only", "gpl-3.0+", "gpl-3.0-or-later", "gplv3", "gplv3+"}
_AGPL3 = {"agpl", "agpl-3.0", "agpl-3.0-only", "agpl-3.0+", "agpl-3.0-or-later"}


def classify_license(spdx_or_name: str) -> LicenseClass:
    value = _normalize_license(spdx_or_name)
    if value in {
        "mit",
        "mit license",
        "apache-2.0",
        "apache license 2.0",
        "bsd",
        "bsd-2-clause",
        "bsd-3-clause",
        "bsd-0-clause",
    }:
        return LicenseClass.PERMISSIVE
    if value in {"cc-by-4.0", "cc by 4.0", "creative commons attribution 4.0"}:
        return LicenseClass.ATTRIBUTION
    if value in {"cc-by-sa-4.0", "cc by-sa 4.0", "creative commons attribution-sharealike 4.0"}:
        return LicenseClass.SHARE_ALIKE
    if value in _GPL2_ONLY | _GPL2_LATER | _GPL3 | _AGPL3:
        return LicenseClass.COPYLEFT_CODE
    return LicenseClass.PROPRIETARY


def check_import(
    asset_kind: Literal["code", "art", "audio", "data"], license: str, project_license: str
) -> SearchGateResult:
    """Conservative import policy, not a substitute for reading the primary licence."""
    if asset_kind not in {"code", "art", "audio", "data"}:
        return SearchGateResult(GateStatus.BLOCKED, ("Unknown asset kind.",))
    classification = classify_license(license)
    source = _normalize_license(license)
    project = _normalize_license(project_license)
    if classification is LicenseClass.PROPRIETARY:
        return SearchGateResult(
            GateStatus.BLOCKED, ("Proprietary, unknown or unsupported licence: never import.",)
        )
    if classification is LicenseClass.COPYLEFT_CODE:
        compatible = (
            (source in _GPL2_ONLY and project in _GPL2_ONLY | _GPL2_LATER)
            or (source in _GPL2_LATER and project in _GPL2_ONLY | _GPL2_LATER | _GPL3 | _AGPL3)
            or (source in _GPL3 and project in _GPL3 | _AGPL3)
            or (source in _AGPL3 and project in _AGPL3)
        )
        if not compatible:
            return SearchGateResult(
                GateStatus.BLOCKED,
                (
                    (
                        "Copyleft material requires a compatible project licence; record any "
                        "owner-approved relicensing decision before import."
                    ),
                ),
            )
        return SearchGateResult(
            GateStatus.CLEARED,
            (
                (
                    "Compatible copyleft project; record the licensing decision and selected compatible "
                    "version, preserve notices, and meet source/distribution obligations."
                ),
            ),
        )
    if classification is LicenseClass.SHARE_ALIKE:
        if asset_kind == "code":
            return SearchGateResult(
                GateStatus.BLOCKED, ("Share-alike asset licence is not cleared for code imports.",)
            )
        return SearchGateResult(
            GateStatus.CLEARED,
            (
                (
                    "Attribution required; keep assets separate under CC-BY-SA-4.0, including adaptations. "
                    "Record source, licence and modifications in the attribution file."
                ),
            ),
        )
    if classification is LicenseClass.ATTRIBUTION:
        return SearchGateResult(
            GateStatus.CLEARED,
            ("Attribution required; record source, CC-BY-4.0 licence and modifications.",),
        )
    if source in {"apache-2.0", "apache license 2.0"} and asset_kind == "code":
        if project in _GPL2_ONLY:
            return SearchGateResult(
                GateStatus.BLOCKED,
                ("Apache-2.0 code is not cleared for a GPL-2.0-only project.",),
            )
        if project in _GPL2_LATER:
            return SearchGateResult(
                GateStatus.CLEARED,
                (
                    (
                        "Select and record GPL-3.0 or later for the combined work; preserve Apache "
                        "licence, attribution and applicable notices."
                    ),
                ),
            )
    return SearchGateResult(
        GateStatus.CLEARED, ("Preserve licence, attribution and applicable notices.",)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    commands = parser.add_subparsers(dest="command", required=True)
    license_parser = commands.add_parser("check-license")
    license_parser.add_argument("license")
    import_parser = commands.add_parser("check-import")
    import_parser.add_argument("asset_kind", choices=["code", "art", "audio", "data"])
    import_parser.add_argument("license")
    import_parser.add_argument("project_license")
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("claim_type", choices=[kind.value for kind in ClaimType])
    evaluate_parser.add_argument("records", type=Path, help="JSON array of SearchRecord objects")
    for command in (license_parser, import_parser, evaluate_parser):
        command.add_argument(
            "--json", action="store_true", dest="json_output", default=argparse.SUPPRESS
        )
    args = parser.parse_args(argv)
    try:
        output: dict[str, object]
        if args.command == "check-license":
            classification = classify_license(args.license)
            output = {
                "license_class": classification.value,
                "status": (
                    GateStatus.BLOCKED
                    if classification is LicenseClass.PROPRIETARY
                    else GateStatus.CLEARED
                ).value,
                "reasons": [
                    (
                        "Classification only; verify COPYING/LICENSE and check_import "
                        "before importing."
                    )
                ],
            }
        elif args.command == "check-import":
            output = asdict(check_import(args.asset_kind, args.license, args.project_license))
        else:
            payload = json.loads(args.records.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
                raise ValueError("Records file must contain a JSON array of objects.")
            records = [SearchRecord(**item) for item in payload]
            output = asdict(evaluate_claim(ClaimType(args.claim_type), records))
    except (OSError, ValueError, TypeError) as error:
        output = {"status": GateStatus.BLOCKED.value, "reasons": [f"Invalid input: {error}"]}
        exit_code = 2
    else:
        exit_code = 0 if output["status"] == GateStatus.CLEARED.value else 1
    if args.json_output:
        print(json.dumps(output, sort_keys=True))
    else:
        print(" / ".join(f"{key}: {value}" for key, value in output.items()))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
