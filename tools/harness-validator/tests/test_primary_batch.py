import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from harness_validator.primary_batch import (  # noqa: E402
    load_primary_batch,
    main,
    validate_primary_batch,
    write_primary_batch_artifacts,
)
from harness_validator.project_file_application import canonical_hash_payload  # noqa: E402


class PrimaryBatchTests(unittest.TestCase):
    def _copy_source_fixture(self, source_root: Path, target_root: Path) -> Path:
        fixture = target_root / "source"
        for rel in (
            Path("_organized_harness_design")
            / "current"
            / "working-manifests"
            / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
            Path("_organized_harness_design")
            / "current"
            / "working-manifests"
            / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl",
        ):
            target = fixture / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_root / rel, target)
        shutil.copytree(
            source_root / "_organized_harness_design" / "active" / "current-stage" / "work-units",
            fixture / "_organized_harness_design" / "active" / "current-stage" / "work-units",
        )
        return fixture

    def _mutate_wave_003_to_drop_wu_004(self, source_fixture: Path) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["wave_id"] == "WAVE-003":
                row["work_unit_ids"] = ["WU-003"]
                row["work_unit_count"] = 1
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_wave_003_to_add_wu_005(self, source_fixture: Path) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["wave_id"] == "WAVE-003":
                row["work_unit_ids"] = ["WU-003", "WU-004", "WU-005"]
                row["work_unit_count"] = 3
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_batch_028_status_and_source_hash(self, source_fixture: Path) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["batch_id"] == "PAC10-BATCH-028":
                row["approval_status"] = "approved"
                row["gate_effect"] = "open"
                row["ready_to_start"] = True
                row["source_wave_hash"] = "0" * 64
                row["work_unit_identity_set_hash"] = "1" * 64
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_batch_028_identity_and_recalculate_set_hash(self, source_fixture: Path) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["batch_id"] == "PAC10-BATCH-028":
                row["work_unit_identities"][0]["canonical_content_hash"] = "0" * 64
                row["work_unit_identities"][0]["artifact_revision_identity"] = "1" * 64
                row["work_unit_identity_set_hash"] = self._canonical_rows_sha(row["work_unit_identities"])
                break
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _canonical_rows_sha(self, rows: list[dict]) -> str:
        import hashlib

        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _mutate_source_file_missing_or_malformed(self, source_fixture: Path, relative_path: Path, malformed: bool) -> None:
        path = source_fixture / relative_path
        if malformed:
            path.write_text("{not-jsonl", encoding="utf-8", newline="\n")
        else:
            path.unlink()

    def _mutate_source_file_wrong_shape(self, source_fixture: Path, relative_path: Path, payload: str) -> None:
        (source_fixture / relative_path).write_text(payload, encoding="utf-8", newline="\n")

    def _mutate_batch_028_field(self, source_fixture: Path, field: str, value) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["batch_id"] == "PAC10-BATCH-028":
                row[field] = value
                break
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_wave_003_field(self, source_fixture: Path, field: str, value) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "current"
            / "working-manifests"
            / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["wave_id"] == "WAVE-003":
                row[field] = value
                break
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_wu_003_definition_to_drop_consumed_contributions(self, source_fixture: Path) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "work-units"
            / "WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row["work_unit_id"] == "WU-003":
                row["consumed_contribution_row_ids"] = []
                break
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_source_to_remove_wu_653_definition(self, source_fixture: Path) -> None:
        self._mutate_source_to_remove_definition(source_fixture, "WU-653")

    def _mutate_source_to_remove_definition(self, source_fixture: Path, work_unit_id: str) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "work-units"
            / "WORK_UNIT_DEFINITION_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = [row for row in rows if row["work_unit_id"] != work_unit_id]
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _mutate_source_to_remove_test_target(self, source_fixture: Path, test_target_id: str) -> None:
        path = (
            source_fixture
            / "_organized_harness_design"
            / "active"
            / "current-stage"
            / "work-units"
            / "WORK_UNIT_TEST_TARGET_REGISTRY_V1_0.jsonl"
        )
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = [row for row in rows if row["test_target_id"] != test_target_id]
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def _seed_consumed_handoffs(self, root: Path, source_root: Path) -> None:
        batch = load_primary_batch(source_root, "PAC10-BATCH-028")
        for unit in batch["work_units"]:
            for row in unit["consumed_rows"]:
                handoff_path = (
                    Path(".harness")
                    / "evidence"
                    / "work-units"
                    / row["contributor_work_unit_id"]
                    / f"{row['handoff_evidence']}.json"
                )
                target = root / handoff_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((source_root / handoff_path).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        subprocess.run(["git", "add", ".harness"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Harness Test",
                "-c",
                "user.email=harness-test@example.invalid",
                "commit",
                "-m",
                "Seed consumed handoff evidence",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_writes_wave_003_primary_contracts_and_git_evidence(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)

            result = write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], True)
            self.assertEqual(result["work_unit_count"], 2)
            manifest = json.loads(
                (root / ".harness" / "manifests" / "PAC10_BATCH_028_IMPLEMENTATION_MANIFEST.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["work_unit_ids"], ["WU-003", "WU-004"])
            self.assertTrue((root / ".harness" / "evidence" / "git" / "pac10-batch-028-git-status.json").exists())
            self.assertTrue((root / ".harness" / "current" / "git-status" / "pac10-batch-028.json").exists())
            self.assertTrue((root / ".harness" / "current" / "checkpoints" / "pac10-batch-028.json").exists())
            status_text = (root / ".harness" / "current" / "status" / "STATUS_KO.md").read_text(encoding="utf-8")
            self.assertIn("PAC10-BATCH-028 primary foundation 후보 evidence 검증 상태: 통과", status_text)
            self.assertIn("대상 Work Unit 2개", status_text)

            for work_unit_id in ["WU-003", "WU-004"]:
                contract_path = root / ".harness" / "artifacts" / "work-units" / work_unit_id / "implementation-contract.json"
                evidence_path = root / ".harness" / "evidence" / "work-units" / work_unit_id / "completion-evidence.json"
                test_path = root / ".harness" / "evidence" / "work-units" / work_unit_id / "test-results.jsonl"
                self.assertTrue(contract_path.exists(), work_unit_id)
                self.assertTrue(evidence_path.exists(), work_unit_id)
                self.assertTrue(test_path.exists(), work_unit_id)
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                self.assertEqual(contract["work_unit_kind"], "primary_integration")
                self.assertRegex(contract["canonical_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_missing_consumed_handoff_evidence(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")

            handoff = root / ".harness" / "evidence" / "work-units" / "WU-653" / "handoff_bs_u02_ac1_de_to_wu_003.json"
            handoff.unlink()

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")
            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("consumed handoff evidence missing", " ".join(validation["content_errors"]))

    def test_fresh_primary_batch_rejects_missing_preexisting_handoffs(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)

            result = write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("consumed handoff evidence missing", " ".join(result["validation"]["content_errors"]))

    def test_rejects_stale_consumed_handoff_payload(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            handoff = root / ".harness" / "evidence" / "work-units" / "WU-653" / "handoff_bs_u02_ac1_de_to_wu_003.json"
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            payload["contribution_id"] = "CONTRIB-WU-CHANGED"
            handoff.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("consumed handoff evidence payload mismatch", " ".join(validation["content_errors"]))
            self.assertIn("consumed handoff evidence canonical_sha256 mismatch", " ".join(validation["content_errors"]))

    def test_secret_scan_includes_consumed_handoff_evidence(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            handoff = root / ".harness" / "evidence" / "work-units" / "WU-653" / "handoff_bs_u02_ac1_de_to_wu_003.json"
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            payload["api_key"] = "sk_test_secret_123456"
            payload["canonical_sha256"] = canonical_hash_payload(payload)
            handoff.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
                newline="\n",
            )
            subprocess.run(["git", "add", ".harness"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Harness Test",
                    "-c",
                    "user.email=harness-test@example.invalid",
                    "commit",
                    "-m",
                    "Record secret-bearing consumed handoff",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertGreaterEqual(validation["batch_local_blockers"]["batch_secret_scan_finding"], 1)
            self.assertTrue(
                any(item["path"].endswith("handoff_bs_u02_ac1_de_to_wu_003.json") for item in validation["secret_findings"])
            )

    def test_rejects_minimal_self_consistent_consumed_handoff_payload(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            handoff = root / ".harness" / "evidence" / "work-units" / "WU-653" / "handoff_bs_u02_ac1_de_to_wu_003.json"
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            kept_fields = {
                "acceptance_criterion_id",
                "architecture_owner_id",
                "consumed_interface",
                "contribution_id",
                "handoff_contract_verified",
                "handoff_evidence",
                "integration_acceptance",
                "owner_implementation_responsibility",
                "primary_integration_work_unit_id",
                "provided_interface",
                "required_dependency_edge_id",
                "verification_result",
                "work_unit_id",
                "work_unit_kind",
            }
            payload = {key: value for key, value in payload.items() if key in kept_fields}
            payload["canonical_sha256"] = canonical_hash_payload(payload)
            handoff.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
                newline="\n",
            )

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("consumed handoff evidence exact payload mismatch", " ".join(validation["content_errors"]))

    def test_rejects_source_wave_batch_mismatch(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_wave_003_to_drop_wu_004(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("batch source", " ".join(result["validation"]["content_errors"]))

    def test_rejects_source_wave_expansion_after_batch_binding(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_wave_003_to_add_wu_005(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_batch_status_and_source_hash_mutation(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_batch_028_status_and_source_hash(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            errors = " ".join(result["validation"]["content_errors"])
            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", errors)

    def test_rejects_batch_identity_mutation_even_when_identity_set_hash_is_recalculated(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_batch_028_identity_and_recalculate_set_hash(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_missing_or_malformed_batch_and_wave_manifest_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                False,
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                True,
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl",
                False,
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl",
                True,
            ),
        ]
        for relative_path, malformed in cases:
            with self.subTest(relative_path=relative_path.as_posix(), malformed=malformed):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp) / "root"
                    root.mkdir()
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    source_fixture = self._copy_source_fixture(source_root, Path(tmp))
                    self._mutate_source_file_missing_or_malformed(source_fixture, relative_path, malformed)

                    result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

                    self.assertEqual(result["validation"]["validation_passed"], False)
                    errors = " ".join(result["validation"]["content_errors"])
                    if relative_path.name.startswith("IMPLEMENTATION_APPROVAL_BATCH"):
                        self.assertIn("batch source load failure", errors)
                    else:
                        self.assertIn("source registry", errors)

    def test_rejects_wrong_shape_batch_and_wave_manifest_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                "[]\n",
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "IMPLEMENTATION_APPROVAL_BATCH_CANDIDATE_REGISTRY_V1_0.jsonl",
                '"x"\n',
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl",
                "[]\n",
            ),
            (
                Path("_organized_harness_design")
                / "current"
                / "working-manifests"
                / "WORK_UNIT_DEPENDENCY_WAVE_CANDIDATE_REGISTRY_V1_0.jsonl",
                '"x"\n',
            ),
        ]
        for relative_path, payload in cases:
            with self.subTest(relative_path=relative_path.as_posix(), payload=payload.strip()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp) / "root"
                    root.mkdir()
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    source_fixture = self._copy_source_fixture(source_root, Path(tmp))
                    self._mutate_source_file_wrong_shape(source_fixture, relative_path, payload)

                    result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

                    self.assertEqual(result["validation"]["validation_passed"], False)
                    errors = " ".join(result["validation"]["content_errors"])
                    if relative_path.name.startswith("IMPLEMENTATION_APPROVAL_BATCH"):
                        self.assertIn("batch source load failure", errors)
                    else:
                        self.assertIn("source registry hash mismatch", errors)

    def test_rejects_wrong_shape_batch_and_wave_fields_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            ("batch", "work_unit_identities", "x"),
            ("batch", "work_unit_count", "x"),
            ("wave", "work_unit_ids", None),
        ]
        for registry_kind, field, value in cases:
            with self.subTest(registry_kind=registry_kind, field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp) / "root"
                    root.mkdir()
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    source_fixture = self._copy_source_fixture(source_root, Path(tmp))
                    if registry_kind == "batch":
                        self._mutate_batch_028_field(source_fixture, field, value)
                    else:
                        self._mutate_wave_003_field(source_fixture, field, value)

                    result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

                    self.assertEqual(result["validation"]["validation_passed"], False)
                    self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_work_unit_definition_source_mutation(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_wu_003_definition_to_drop_consumed_contributions(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_missing_provider_definition_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_source_to_remove_wu_653_definition(source_fixture)

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            errors = " ".join(result["validation"]["content_errors"])
            self.assertIn("source registry hash mismatch", errors)

    def test_rejects_missing_primary_definition_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_source_to_remove_definition(source_fixture, "WU-003")

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_missing_bound_test_target_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            source_fixture = self._copy_source_fixture(source_root, Path(tmp))
            self._mutate_source_to_remove_test_target(source_fixture, "TT-WU-040")

            result = write_primary_batch_artifacts(root, source_fixture, "PAC10-BATCH-028")

            self.assertEqual(result["validation"]["validation_passed"], False)
            self.assertIn("source registry hash mismatch", " ".join(result["validation"]["content_errors"]))

    def test_rejects_mutated_authorization_payload(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            authorization = (
                root
                / ".harness"
                / "evidence"
                / "implementation-entry"
                / "PAC10_BATCH_028_GOAL_EXECUTION_AUTHORIZATION_RECORD.json"
            )
            payload = json.loads(authorization.read_text(encoding="utf-8"))
            payload["work_unit_count"] = 999
            authorization.write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n"
            )

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("authorization record: payload mismatch", " ".join(validation["content_errors"]))

    def test_rejects_mutated_checkpoint_payload(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            checkpoint = root / ".harness" / "current" / "checkpoints" / "pac10-batch-028.json"
            payload = json.loads(checkpoint.read_text(encoding="utf-8"))
            payload["head"] = "not-the-head"
            checkpoint.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8", newline="\n")

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("checkpoint: payload mismatch", " ".join(validation["content_errors"]))

    def test_rejects_missing_git_status_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            (root / ".harness" / "evidence" / "git" / "pac10-batch-028-git-status.json").unlink()

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("declared artifact missing", " ".join(validation["content_errors"]))

    def test_rejects_malformed_generated_json_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            (
                Path(".harness")
                / "evidence"
                / "implementation-entry"
                / "PAC10_BATCH_028_GOAL_EXECUTION_AUTHORIZATION_RECORD.json",
                "authorization record: invalid JSON",
            ),
            (
                Path(".harness") / "evidence" / "work-units" / "WU-003" / "completion-evidence.json",
                "WU-003: completion evidence: invalid JSON",
            ),
            (
                Path(".harness") / "evidence" / "work-units" / "WU-003" / "test-results.jsonl",
                "WU-003: test result row: invalid JSONL",
            ),
        ]
        for relative_path, expected_error in cases:
            with self.subTest(relative_path=relative_path.as_posix()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    self._seed_consumed_handoffs(root, source_root)
                    write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
                    (root / relative_path).write_text("{not json", encoding="utf-8", newline="\n")

                    validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

                    self.assertEqual(validation["validation_passed"], False)
                    self.assertIn(expected_error, " ".join(validation["content_errors"]))

    def test_rejects_wrong_shape_generated_json_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            (
                Path(".harness") / "evidence" / "git" / "pac10-batch-028-git-status.json",
                "[]",
                "git status evidence: invalid JSON object",
            ),
            (
                Path(".harness") / "evidence" / "work-units" / "WU-653" / "handoff_bs_u02_ac1_de_to_wu_003.json",
                "[]",
                "WU-003: consumed handoff evidence: invalid JSON object",
            ),
            (
                Path(".harness") / "evidence" / "work-units" / "WU-003" / "test-results.jsonl",
                '"x"\n',
                "WU-003: test result row: invalid JSONL object row",
            ),
        ]
        for relative_path, payload, expected_error in cases:
            with self.subTest(relative_path=relative_path.as_posix()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    self._seed_consumed_handoffs(root, source_root)
                    write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
                    (root / relative_path).write_text(payload, encoding="utf-8", newline="\n")

                    validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

                    self.assertEqual(validation["validation_passed"], False)
                    self.assertIn(expected_error, " ".join(validation["content_errors"]))

    def test_rejects_git_status_missing_required_keys_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            git_status = root / ".harness" / "evidence" / "git" / "pac10-batch-028-git-status.json"
            git_status.write_text("{}", encoding="utf-8", newline="\n")

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("git status evidence missing field: batch_id", " ".join(validation["content_errors"]))

    def test_rejects_invalid_utf8_status_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
            (root / ".harness" / "current" / "status" / "STATUS_KO.md").write_bytes(b"\xff\xfe\xff")

            validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

            self.assertEqual(validation["validation_passed"], False)
            self.assertIn("current status: invalid UTF-8", " ".join(validation["content_errors"]))

    def test_rejects_directory_artifact_paths_without_exception(self):
        source_root = Path(__file__).resolve().parents[3]
        cases = [
            (
                Path(".harness") / "manifests" / "PAC10_BATCH_028_IMPLEMENTATION_MANIFEST.json",
                "manifest: not a file",
            ),
            (Path(".harness") / "current" / "status" / "STATUS_KO.md", "current status: not a file"),
            (
                Path(".harness") / "evidence" / "work-units" / "WU-003" / "test-results.jsonl",
                "WU-003: test result row: not a file",
            ),
        ]
        for relative_path, expected_error in cases:
            with self.subTest(relative_path=relative_path.as_posix()):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
                    self._seed_consumed_handoffs(root, source_root)
                    write_primary_batch_artifacts(root, source_root, "PAC10-BATCH-028")
                    target = root / relative_path
                    target.unlink()
                    target.mkdir()

                    validation = validate_primary_batch(root, source_root, "PAC10-BATCH-028")

                    self.assertEqual(validation["validation_passed"], False)
                    self.assertIn(expected_error, " ".join(validation["content_errors"]))

    def test_primary_cli_accepts_batch_id(self):
        source_root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            self._seed_consumed_handoffs(root, source_root)
            exit_code = main(
                [
                    "--root",
                    str(root),
                    "--source-root",
                    str(source_root),
                    "--batch-id",
                    "PAC10-BATCH-028",
                ]
            )

            self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
