from harness_validator.stage_assets import STAGES


HARNESS_RUNTIME_VERSION = "1.0.4"
STAGE_SET_VERSION = "harness-stage-set-v1.0.3"
CURRENT_READ_SET_SCHEMA_VERSION = "1.0"
DOCTOR_MODES = ("release-payload", "installed-project")
READ_SET_MAX_BYTES = 20 * 1024
AGENTS_MAX_BYTES = 3 * 1024

REQUIRED_FILES = (
    "AGENTS.md",
    "install-harness.ps1",
    ".harness/current/status/STATUS_KO.md",
    ".harness/current/navigation/START_HERE.md",
    ".harness/current/source_identity/SOURCE_IDENTITY.json",
    ".harness/manifests/CURRENT_READ_SET.json",
    ".harness/runtime/START_WORKFLOW_KO.md",
    ".harness/runtime/WORKFLOW_RULES_KO.md",
    ".harness/runtime/COMMANDS_KO.md",
    ".harness/runtime/READ_SET_POLICY_KO.md",
)

RELEASE_PAYLOAD_FORBIDDEN_PREFIXES = (
    "_organized" + "_harness_design/",
    "docs/",
    "tests/",
    ".harness/archive/",
    ".harness/artifacts/",
    ".harness/reviews/",
    ".harness/approvals/",
)

INSTALLED_PROJECT_FORBIDDEN_PREFIXES = (
    "_organized" + "_harness_design/",
    "tools/harness-validator/" + "tests/",
    ".harness/archive/",
)

READ_SET_FORBIDDEN_PREFIXES = (
    "tools/",
    "_organized" + "_harness_design/",
    ".harness/archive/",
)

FORBIDDEN_PREFIXES = INSTALLED_PROJECT_FORBIDDEN_PREFIXES

FORBIDDEN_NAME_MARKERS = (
    "GPT" + "_PRO",
    "HARNESS" + "_1_0_RUNTIME_SIMULATION_AUDIT",
)

SOURCE_IDENTITY_REQUIRED = (
    "artifact_id",
    "artifact_version",
    "source_repository",
    "release_url",
    "release_tag",
    "source_commit_status",
    "installer_sha256",
    "runtime_asset_sha256",
    "install_mode",
    "install_result",
    "installed_at_utc",
    "previous_identity",
)

PLANNING_STAGE_FILES = {stage["stage_id"]: stage["artifact_path"] for stage in STAGES}
PLANNING_STAGE_ORDER = tuple(PLANNING_STAGE_FILES)
