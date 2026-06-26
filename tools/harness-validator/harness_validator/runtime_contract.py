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

FORBIDDEN_PREFIXES = (
    "_organized" + "_harness_design/",
    "tests/",
    "tools/harness-validator/" + "tests/",
    ".harness/archive/",
    ".harness/artifacts/",
    ".harness/reviews/",
    ".harness/approvals/",
)

FORBIDDEN_NAME_MARKERS = (
    "GPT" + "_PRO",
    "HARNESS" + "_1_0_RUNTIME_SIMULATION_AUDIT",
)

READ_SET_MAX_BYTES = 20 * 1024
AGENTS_MAX_BYTES = 3 * 1024

SOURCE_IDENTITY_REQUIRED = (
    "source_repository",
    "release_url",
    "release_tag",
    "installer_sha256",
    "runtime_asset_sha256",
    "install_mode",
    "install_result",
)
