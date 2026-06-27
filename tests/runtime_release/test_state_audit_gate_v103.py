import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/harness-validator"))

from harness_validator.state_model import work_unit_identity_hash, write_work_unit_registry, write_work_unit_approval, write_batch_manifest, write_batch_approval, gate_open_eligible, write_gate_state, append_gate_event, write_implementation_source_manifest, mark_work_unit_stale


WU = {"work_unit_id":"WU-001","artifact_id":"work_unit.wu-001","version":"1.0.0","artifact_revision_identity":"a"*64,"canonical_content_hash":"b"*64,"dependency_snapshot_hash":"c"*64,"acceptance_hash":"d"*64,"direct_acceptance_criteria":["AC-001"],"contributor_acceptance_criteria":[],"test_target_ids":["TEST-001"],"ready_to_start":False,"approval_status":"approved","stale_status":"fresh"}


class StateAuditGateTests(unittest.TestCase):
    def test_state_files_and_gate_open_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_work_unit_registry(root, [WU])
            wu_approval = write_work_unit_approval(root, WU, "creator")
            batch = write_batch_manifest(root, "BATCH-001", ["WU-001"], {"WU-001": work_unit_identity_hash(WU)})
            batch_approval = write_batch_approval(root, batch, "creator")
            wu_payload = json.loads(wu_approval.read_text(encoding="utf-8"))
            for key in ("approval_record_id", "approval_type", "work_unit_id", "artifact_id", "version", "artifact_revision_identity", "canonical_content_hash", "dependency_snapshot_hash", "acceptance_hash", "registry_snapshot_hashes", "approved_by", "approved_at_utc", "approval_statement_hash", "approval_status", "revocation_reason", "supersedes_approval_record_id"):
                self.assertIn(key, wu_payload)
            batch_payload = json.loads(batch_approval.read_text(encoding="utf-8"))
            for key in ("approval_record_id", "approval_type", "batch_id", "batch_hash", "work_unit_ids", "work_unit_identity_hashes", "dependency_closure_hash", "bootstrap_prerequisite_status", "approved_by", "approved_at_utc", "approval_statement_hash", "approval_status", "revocation_reason", "supersedes_approval_record_id"):
                self.assertIn(key, batch_payload)
            for key in ("batch_id", "work_unit_ids", "dependency_closure_order", "parallelism_limit", "risk_level", "batch_hash", "approval_status", "stale_status"):
                self.assertIn(key, batch)
            result = gate_open_eligible(root, "BATCH-001")
            self.assertTrue(result["eligible"], result)

    def test_stale_work_unit_blocks_gate_and_resets_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = mark_work_unit_stale(dict(WU), "stale_due_to_artifact_change")
            write_work_unit_registry(root, [stale])
            batch = write_batch_manifest(root, "BATCH-001", ["WU-001"], {"WU-001": work_unit_identity_hash(stale)})
            write_batch_approval(root, batch, "creator")
            result = gate_open_eligible(root, "BATCH-001")
            self.assertFalse(result["eligible"])
            self.assertIn("bootstrap.work_unit_stale", result["blockers"])
            registry = json.loads((root / ".harness/current/work-units/WORK_UNITS_REGISTRY.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertFalse(registry["ready_to_start"])

    def test_gate_event_and_source_manifest_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_gate_state(root, "closed", None, [], [])
            append_gate_event(root, "gate_open_requested", "closed", "opening_requested", "BATCH-001", ["WU-001"], "creator", [])
            write_implementation_source_manifest(root, "BATCH-001", ["WU-001"], "0"*40, "1"*40, ["README.md"], [], [], [])
            gate_state = json.loads((root / ".harness/current/gate/GATE_STATE.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_state["gate_status"], "closed")
            self.assertIn("ready_to_start_counts", gate_state)
            self.assertTrue((root / ".harness/current/gate/GATE_EVENTS.jsonl").is_file())
            event = json.loads((root / ".harness/current/gate/GATE_EVENTS.jsonl").read_text(encoding="utf-8").splitlines()[0])
            for key in ("event_id", "event_type", "event_at_utc", "from_gate_status", "to_gate_status", "batch_id", "work_unit_ids", "actor", "reason", "state_hash_before", "state_hash_after", "evidence_paths"):
                self.assertIn(key, event)
            manifest = json.loads((root / ".harness/current/implementation/IMPLEMENTATION_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
            for key in ("batch_id", "work_unit_ids", "base_commit", "head_commit", "changed_files", "created_files", "modified_files", "deleted_files", "test_evidence_paths", "review_evidence_paths", "out_of_scope_files", "source_manifest_hash"):
                self.assertIn(key, manifest)
