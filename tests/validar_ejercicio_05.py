"""Validación local del ejercicio 5, sin conexiones remotas ni credenciales.

Extracts only E5 imports/definitions/literal constants; never executes the
notebook's connection, credentials, DVC, Git, or production invocation cells.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import importlib.util
import io
import json
import math
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from math import isfinite
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Time
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
)

REPO = Path(__file__).resolve().parents[1]
TABLES = ("Buque", "Radar", "Movimiento", "Evidencia")
RETURN_KEYS = ("buques", "radares", "movimientos", "evidencias")


def load_helper(repo: Path):
    spec = importlib.util.spec_from_file_location(
        "portlog_e06_tests_for_e05", repo / "tests/validar_ejercicio_06.py"
    )
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    spec.loader.exec_module(helper)
    return helper


def safe_definitions(source: str):
    tree = ast.parse(source)
    safe = []
    for node in tree.body:
        if isinstance(
            node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
        ):
            safe.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            names = {
                part.id
                for target in targets
                for part in ast.walk(target)
                if isinstance(part, ast.Name)
            }
            if any(
                "PASSWORD" in name or "URL" in name or "KEY" in name
                for name in names
            ):
                continue
            safe.append(node)
    return ast.Module(body=safe, type_ignores=[])


def load_e05(repo: Path, helper, loader_source: Path | None = None):
    notebook = helper.read_notebook(repo)
    ns = helper.load_original_models(notebook)
    ns.update(
        {
            key: value
            for key, value in globals().items()
            if key
            not in {
                "__name__",
                "__file__",
                "__package__",
                "__loader__",
                "__spec__",
            }
        }
    )
    selected = []
    within = False
    for index, cell in enumerate(notebook["cells"]):
        source = "".join(cell.get("source", []))
        if cell["cell_type"] == "markdown" and "# Ejercicio 05" in source:
            within = True
        elif cell["cell_type"] == "markdown" and "# Ejercicio 06" in source:
            within = False
        if not within or cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        safe = safe_definitions(source)
        if safe.body and loader_source is None:
            exec(compile(safe, f"e05_definitions_cell_{index}", "exec"), ns)
            selected.append(index)
    if loader_source is not None:
        safe = safe_definitions(loader_source.read_text(encoding="utf-8"))
        exec(compile(safe, str(loader_source), "exec"), ns)
        selected.append(str(loader_source))
    if not callable(ns.get("cargar_transito_portuario")):
        raise RuntimeError(
            "E5 API cargar_transito_portuario is not available yet"
        )
    helper.E06_CELLS = tuple(
        index
        for index, cell in enumerate(notebook["cells"])
        if cell["cell_type"] == "code"
        and any(
            f"def {name}(" in "".join(cell.get("source", []))
            for name in helper.QUERY_NAMES
        )
    )
    assert len(helper.E06_CELLS) == 6, helper.E06_CELLS
    return notebook, ns, selected


def memory_engine():
    engine = create_engine("sqlite:///:memory:")
    statements = []

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    @event.listens_for(engine, "before_cursor_execute")
    def reject_destructive(
        _connection, _cursor, statement, _parameters, _context, _many
    ):
        normalized = " ".join(statement.upper().split())
        statements.append(normalized)
        assert not normalized.startswith(
            ("DROP ", "ALTER ", "DELETE ", "TRUNCATE ", "CREATE DATABASE ")
        ), normalized

    return engine, statements


def snapshot(engine, ns):
    existing = set(inspect(engine).get_table_names())
    result = {}
    with engine.connect() as connection:
        for name in TABLES:
            if name in existing:
                table = ns[name].__table__
                result[name] = sorted(
                    [tuple(row) for row in connection.execute(select(table))],
                    key=repr,
                )
        if "UnrelatedAuditMarker" in existing:
            result["UnrelatedAuditMarker"] = list(
                connection.execute(
                    text('SELECT * FROM "UnrelatedAuditMarker"')
                )
            )
    return result


def counts(engine, ns):
    with Session(engine) as session:
        return {
            key: session.scalar(select(func.count()).select_from(ns[name]))
            for key, name in zip(RETURN_KEYS, TABLES)
        }


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def load_raw(repo):
    with (repo / "port_log/data/processed/port_movements_image.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        return rows, reader.fieldnames


def invoke(loader, engine, path):
    with contextlib.redirect_stdout(io.StringIO()):
        result = loader(engine, path)
    assert isinstance(result, dict), result
    assert set(result) == {"insertados", "totales"}, result
    for section in ("insertados", "totales"):
        assert set(result[section]) == set(RETURN_KEYS), result
        assert all(
            isinstance(result[section][key], int) for key in RETURN_KEYS
        ), result
    return result


def expect_rollback(loader, engine, path, ns):
    before = snapshot(engine, ns)
    try:
        invoke(loader, engine, path)
    except (ValueError, TypeError) as error:
        assert snapshot(engine, ns) == before, (
            "Validation error left partial database mutations"
        )
        return type(error).__name__
    raise AssertionError("Expected an explicit validation/conflict exception")


def seed_unrelated(engine, ns, helper):
    ns["Base"].metadata.create_all(engine)
    row = helper.example_row(
        "FOREIGN-MOV",
        matricula="FOREIGN-VESSEL",
        radar="FOREIGN-RADAR",
        muelle="FOREIGN-DOCK",
        imagen="foreign.jpg",
    )
    with Session(engine) as session:
        session.add(ns["procesar_fila_csv"](row))
        session.commit()
    with engine.begin() as connection:
        connection.execute(
            text(
                'CREATE TABLE "UnrelatedAuditMarker" (id INTEGER PRIMARY KEY, marker TEXT)'
            )
        )
        connection.execute(
            text('INSERT INTO "UnrelatedAuditMarker" VALUES (1, :marker)'),
            {"marker": "preserve-me"},
        )


def run_suite(repo: Path, loader_source: Path | None = None):
    helper = load_helper(repo)
    notebook, ns, selected = load_e05(repo, helper, loader_source)
    loader = ns["cargar_transito_portuario"]
    original_csv = repo / "port_log/data/processed/port_movements_image.csv"
    raw, fieldnames = load_raw(repo)
    expected = {
        "buques": len({row["matricula"] for row in raw}),
        "radares": len({row["radar_id"] for row in raw if row["radar_id"]}),
        "movimientos": len(raw),
        "evidencias": sum(bool(row["imagen"].strip()) for row in raw),
    }
    assert expected == dict(
        buques=31, radares=8, movimientos=447, evidencias=431
    ), expected
    results = []

    def passed(name, detail=""):
        results.append({"case": name, "status": "PASS", "detail": detail})
        print("PASS", name, detail)

    with tempfile.TemporaryDirectory(prefix="port-log-e05-cases-") as case_dir:
        cases = Path(case_dir)
        engine, _ = memory_engine()
        try:
            result = invoke(loader, engine, original_csv)
            assert counts(engine, ns) == expected, (
                counts(engine, ns),
                expected,
            )
            assert result["totales"] == expected, (result, expected)
            assert result["insertados"] == expected, (result, expected)
            with Session(engine) as session:
                Movement = ns["Movimiento"]
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(Movement)
                        .where(Movement.radar_id.is_(None))
                    )
                    == 21
                )
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(Movement)
                        .where(~Movement.evidencia.has())
                    )
                    == 16
                )
                assert all(
                    isinstance(value, bool)
                    for value in session.scalars(
                        select(Movement.hora_ingreso_imputada)
                    )
                )
                identifiers = defaultdict(set)
                for row in raw:
                    if row.get("buque_id"):
                        identifiers[row["matricula"]].add(row["buque_id"])
                expected_ids = {
                    key: next(iter(values)) if len(values) == 1 else None
                    for key, values in identifiers.items()
                }
                actual_ids = dict(
                    session.execute(
                        select(ns["Buque"].matricula, ns["Buque"].buque_id)
                    ).all()
                )
                assert actual_ids == expected_ids, (actual_ids, expected_ids)
            passed("full_csv_counts_relations_types", str(expected))
            before = snapshot(engine, ns)
            repeated = invoke(loader, engine, original_csv)
            assert repeated["totales"] == expected
            assert repeated["insertados"] == dict.fromkeys(RETURN_KEYS, 0), (
                repeated
            )
            assert snapshot(engine, ns) == before, (
                "Re-run changed persisted data"
            )
            passed("idempotent_rerun_no_mutation")
            fixture = helper.Fixture(
                engine=engine,
                namespace=ns | {"engine": engine},
                rows=helper.read_csv_rows(repo),
            )
            query_checks, _output = helper.check_queries(
                fixture, notebook, label="e05_loaded_db"
            )
            passed(
                "e06_against_actual_e05_load",
                f"{query_checks} independent checks",
            )
            with Session(engine) as session:
                movement = session.get(
                    ns["Movimiento"], raw[0]["movimiento_id"]
                )
                movement.tonelaje_declarado += 1.0
                session.commit()
            expect_rollback(loader, engine, original_csv, ns)
            passed("existing_movement_conflict_explicit_rollback")
        finally:
            engine.dispose()

        engine, _ = memory_engine()
        try:
            seed_unrelated(engine, ns, helper)
            foreign_before = snapshot(engine, ns)
            result = invoke(loader, engine, original_csv)
            actual = counts(engine, ns)
            assert actual == {
                key: value + 1 for key, value in expected.items()
            }, actual
            assert (
                result["totales"] == actual
                and result["insertados"] == expected
            ), result
            after = snapshot(engine, ns)
            for table, rows in foreign_before.items():
                assert all(row in after[table] for row in rows), (
                    f"Changed foreign data in {table}"
                )
            before = after
            repeated = invoke(loader, engine, original_csv)
            assert repeated["insertados"] == dict.fromkeys(RETURN_KEYS, 0), (
                repeated
            )
            assert snapshot(engine, ns) == before
            passed("preserves_foreign_entities_tables_and_rerun", str(result))
        finally:
            engine.dispose()

        engine, statements = memory_engine()
        try:
            invoke(loader, engine, original_csv)
            with Session(engine) as session:
                movement = session.get(
                    ns["Movimiento"], raw[0]["movimiento_id"]
                )
                for field in ("exceso_velocidad_real", "exceso_velocidad"):
                    original = getattr(movement, field)
                    rounded = float(format(original, ".15g"))
                    assert rounded != original, (field, original, rounded)
                    setattr(movement, field, rounded)
                session.commit()
            before = snapshot(engine, ns)
            statement_start = len(statements)
            result = invoke(loader, engine, original_csv)
            assert result["totales"] == expected
            assert result["insertados"] == dict.fromkeys(RETURN_KEYS, 0)
            assert snapshot(engine, ns) == before, (
                "Float roundtrip caused persisted data changes"
            )
            assert not any(
                statement.startswith("UPDATE ")
                for statement in statements[statement_start:]
            ), "Idempotent float roundtrip emitted UPDATE statements"
            passed("postgres_float_roundtrip_idempotent_no_updates")
            with Session(engine) as session:
                movement = session.get(
                    ns["Movimiento"], raw[0]["movimiento_id"]
                )
                movement.exceso_velocidad += 0.01
                session.commit()
            expect_rollback(loader, engine, original_csv, ns)
            passed("significant_float_delta_001_still_conflicts")
        finally:
            engine.dispose()

        exact_variants = {
            "boolean": ("hora_ingreso_imputada", True),
            "nullable_none_vs_zero": ("duracion_horas", 0.0),
            "text": ("estado_despacho", "DIFFERENT-STATE"),
        }
        for label, (field, changed_value) in exact_variants.items():
            engine, _ = memory_engine()
            try:
                invoke(loader, engine, original_csv)
                with Session(engine) as session:
                    movement = session.get(
                        ns["Movimiento"], raw[0]["movimiento_id"]
                    )
                    assert getattr(movement, field) != changed_value
                    setattr(movement, field, changed_value)
                    session.commit()
                expect_rollback(loader, engine, original_csv, ns)
                passed(f"exact_{label}_comparison_preserved")
            finally:
                engine.dispose()

        engine, _ = memory_engine()
        try:
            partial = write_csv(cases / "partial.csv", raw[:7], fieldnames)
            invoke(loader, engine, partial)
            partial_counts = counts(engine, ns)
            completed = invoke(loader, engine, original_csv)
            assert counts(engine, ns) == expected
            assert completed["insertados"] == {
                key: expected[key] - partial_counts[key] for key in RETURN_KEYS
            }
            passed("partial_then_complete_load")
        finally:
            engine.dispose()

        engine, _ = memory_engine()
        try:
            ns["Base"].metadata.create_all(engine)
            with Session(engine) as session:
                session.add(
                    ns["Buque"](
                        matricula=raw[0]["matricula"],
                        buque_id="PRESERVE-LEGACY",
                    )
                )
                session.commit()
            result = invoke(loader, engine, original_csv)
            with Session(engine) as session:
                existing = session.get(ns["Buque"], raw[0]["matricula"])
                assert existing.buque_id == "PRESERVE-LEGACY"
            assert counts(engine, ns) == expected
            assert result["insertados"]["buques"] == expected["buques"] - 1
            passed("preserves_existing_informational_buque_id")
        finally:
            engine.dispose()

        engine, _ = memory_engine()
        try:
            invoke(loader, engine, original_csv)
            with Session(engine) as session:
                evidence = session.scalar(
                    select(ns["Evidencia"]).where(
                        ns["Evidencia"].movimiento_id
                        == raw[0]["movimiento_id"]
                    )
                )
                evidence.archivo_imagen = "conflicting-existing.jpg"
                session.commit()
            expect_rollback(loader, engine, original_csv, ns)
            passed("existing_evidence_conflict_explicit_rollback")
        finally:
            engine.dispose()

        invalid_variants = {
            "invalid_last_date": {"fecha_ingreso": "2024-99-99"},
            "invalid_last_boolean": {"hora_ingreso_imputada": "maybe"},
            "invalid_last_critical_number": {
                "tonelaje_declarado": "not-a-number"
            },
            "nonfinite_critical_number": {"tonelaje_declarado": "inf"},
            "missing_last_registration": {"matricula": ""},
        }
        for label, modifications in invalid_variants.items():
            engine, _ = memory_engine()
            try:
                seed_unrelated(engine, ns, helper)
                changed = [dict(row) for row in raw]
                changed[-1].update(modifications)
                path = write_csv(cases / f"{label}.csv", changed, fieldnames)
                rejected = expect_rollback(loader, engine, path, ns)
                passed(label + "_full_rollback", rejected)
            finally:
                engine.dispose()

        engine, _ = memory_engine()
        try:
            changed = [dict(row) for row in raw]
            changed[-1]["fecha_ingreso"] = "not-a-date"
            path = write_csv(
                cases / "invalid_before_ddl.csv", changed, fieldnames
            )
            expect_rollback(loader, engine, path, ns)
            assert inspect(engine).get_table_names() == [], (
                "Invalid CSV created tables before validation"
            )
            passed("invalid_csv_rejected_before_ddl")
        finally:
            engine.dispose()

        engine, _ = memory_engine()
        try:
            seed_unrelated(engine, ns, helper)
            duplicate = [dict(row) for row in raw[:3]]
            duplicate.append(dict(duplicate[0], origen="CONFLICTING-ORIGIN"))
            path = write_csv(
                cases / "duplicate_conflict.csv", duplicate, fieldnames
            )
            expect_rollback(loader, engine, path, ns)
            passed("duplicate_csv_id_conflict_explicit_rollback")
        finally:
            engine.dispose()

        engine, _ = memory_engine()
        try:
            seed_unrelated(engine, ns, helper)
            path = write_csv(
                cases / "missing_required_header.csv",
                raw[:2],
                [name for name in fieldnames if name != "matricula"],
            )
            expect_rollback(loader, engine, path, ns)
            passed("missing_required_header_rollback")
        finally:
            engine.dispose()

    print(
        "ALL_PASS",
        len(results),
        "E05 integration scenarios",
        "E05 definition cells",
        selected,
    )
    report = Path(tempfile.gettempdir()) / "port-log-e05-test-results.json"
    report.write_text(
        json.dumps(
            {"expected_counts": expected, "cases": results},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return results


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--source", type=Path)
    arguments = parser.parse_args()
    run_suite(arguments.repo, arguments.source)
