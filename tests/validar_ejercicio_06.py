"""Valida el ejercicio 06 localmente, sin Git, DVC ni conexiones a Supabase.

Preparación y ejecución desde la raíz del repositorio:
    python -m pip install -r requirements-test.txt
    python tests/validar_ejercicio_06.py

Carga en SQLite los modelos originales y los datos del CSV, deduplicando las
entidades y omitiendo relaciones ausentes únicamente en la fixture de prueba.
Ejecuta las seis celdas E06 y compara con cálculos independientes de CSV/Python.
No implementa el ejercicio 05 ni modifica el notebook o los datos del grupo.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import sys
import types
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from itertools import count
from pathlib import Path

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Time
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

DEFAULT_REPO = Path(__file__).resolve().parents[1]
MODEL_CELLS = (39, 40, 41, 42, 43)
E06_CELL_IDS = (
    "l-rWbjG8M-uv",
    "vbybe9caNDoA",
    "F-k8mOpbNAon",
    "0AA7dr5lNAW3",
    "0LhC1RyrNAAn",
    "eQ3CshKQM_bn",
)
QUERY_NAMES = (
    "consulta01_top_buques",
    "consulta02_sin_evidencia",
    "consulta03_radares",
    "consulta04_reincidentes",
    "consulta05_exceso_por_muelle",
    "consulta06_cobertura",
)
_module_ids = count(1)


def read_notebook(repo: Path = DEFAULT_REPO) -> dict:
    return json.loads(
        (repo / "03_Port_Log_Grupo_16.ipynb").read_text(encoding="utf-8")
    )


def load_original_models(notebook: dict) -> dict:
    """Executes precisely E4 classes and mapper, with safe imports supplied."""
    module_name = f"portlog_original_models_{next(_module_ids)}"
    module = types.ModuleType(module_name)
    module.__dict__.update(
        {
            name: globals()[name]
            for name in (
                "Boolean",
                "Date",
                "Float",
                "ForeignKey",
                "String",
                "Time",
                "DeclarativeBase",
                "Mapped",
                "mapped_column",
                "relationship",
                "date",
                "time",
            )
        }
    )
    sys.modules[module_name] = module
    for index in MODEL_CELLS:
        source = "".join(notebook["cells"][index]["source"])
        exec(
            compile(source, f"original_e4_cell_{index}", "exec"),
            module.__dict__,
        )
    return module.__dict__


def read_csv_rows(repo: Path = DEFAULT_REPO) -> list[dict]:
    path = repo / "port_log/data/processed/port_movements_image.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        raw = list(csv.DictReader(stream))
    rows = []
    numeric = (
        "tonelaje_declarado",
        "velocidad_ingreso",
        "velocidad_maxima_muelle",
        "duracion_horas",
        "exceso_velocidad_real",
        "exceso_velocidad",
        "ratio",
    )
    for original in raw:
        row = {
            key: (value if value != "" else None)
            for key, value in original.items()
        }
        for key in numeric:
            row[key] = float(row[key]) if row.get(key) is not None else None
        for key in ("hora_ingreso_imputada", "hora_egreso_imputada"):
            if row.get(key) not in ("True", "False", True, False):
                raise ValueError(f"Unexpected boolean {key}: {row.get(key)!r}")
            row[key] = row[key] in ("True", True)
        rows.append(row)
    return rows


@dataclass
class Fixture:
    engine: object
    namespace: dict
    rows: list[dict]

    def close(self) -> None:
        self.engine.dispose()


def build_fixture(
    rows: list[dict] | None = None,
    *,
    repo: Path = DEFAULT_REPO,
    notebook: dict | None = None,
) -> Fixture:
    """Deduplicates identities only in this test fixture; never edits E4/E5."""
    notebook = notebook if notebook is not None else read_notebook(repo)
    ns = load_original_models(notebook)
    rows = read_csv_rows(repo) if rows is None else rows
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_fk(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    ns["Base"].metadata.create_all(engine)
    buques = {}
    radares = {}
    with Session(engine) as session:
        movements = []
        for source in rows:
            movement = ns["procesar_fila_csv"](dict(source))
            registration = source["matricula"]
            if registration in buques:
                movement.buque = buques[registration]
            else:
                buques[registration] = movement.buque
            radar_id = source.get("radar_id")
            if radar_id is None:
                movement.radar = None
            elif radar_id in radares:
                movement.radar = radares[radar_id]
            else:
                radares[radar_id] = movement.radar
            if not source.get("imagen") and not source.get(
                "_persist_evidence"
            ):
                movement.evidencia = None
            movements.append(movement)
        session.add_all(movements)
        session.commit()
        expected_counts = {
            "Buque": len({row["matricula"] for row in rows}),
            "Radar": len(
                {
                    row["radar_id"]
                    for row in rows
                    if row.get("radar_id") is not None
                }
            ),
            "Movimiento": len(rows),
            "Evidencia": sum(
                bool(row.get("imagen")) or bool(row.get("_persist_evidence"))
                for row in rows
            ),
        }
        actual_counts = {
            name: session.scalar(select(func.count()).select_from(ns[name]))
            for name in expected_counts
        }
        assert actual_counts == expected_counts, (
            actual_counts,
            expected_counts,
        )
    ns.update(
        engine=engine,
        Session=Session,
        select=select,
        func=func,
        date=date,
        datetime=datetime,
    )
    return Fixture(engine=engine, namespace=ns, rows=rows)


def expected_from_csv(
    rows: list[dict], since: date, until: date, limit: int = 10
) -> dict:
    """Independent Python/CSV oracle: no SQLAlchemy query expressions."""
    if since > until:
        raise ValueError("Invalid date range")
    infringements = [
        row
        for row in rows
        if row.get("exceso_velocidad") is not None
        and row["exceso_velocidad"] > 0
    ]
    vessel_counts = Counter(row["matricula"] for row in infringements)
    top = sorted(vessel_counts.items(), key=lambda item: (-item[1], item[0]))[
        :limit
    ]
    no_evidence = [row for row in infringements if not has_image(row)]
    no_evidence.sort(
        key=lambda row: (
            -date.fromisoformat(row["fecha_ingreso"]).toordinal(),
            row["movimiento_id"],
        )
    )
    radar_groups = defaultdict(list)
    for row in infringements:
        if row.get("radar_id") is not None:
            radar_groups[row["radar_id"]].append(row)
    radars = [
        (key, len({row["muelle"] for row in group}), len(group))
        for key, group in radar_groups.items()
    ]
    radars.sort(key=lambda item: (-item[2], item[0]))
    period_counts = Counter(
        row["matricula"]
        for row in infringements
        if since <= date.fromisoformat(row["fecha_ingreso"]) <= until
    )
    recurrent = sorted(
        (
            (key, quantity)
            for key, quantity in period_counts.items()
            if quantity > 1
        ),
        key=lambda item: (-item[1], item[0]),
    )[:limit]
    dock_values = defaultdict(list)
    for row in infringements:
        value = row.get("exceso_velocidad")
        if value is not None:
            dock_values[row["muelle"]].append(value)
    docks = [
        (key, sum(values) / len(values)) for key, values in dock_values.items()
    ]
    docks.sort(key=lambda item: (-item[1], item[0]))
    covered = sum(has_image(row) for row in infringements)
    total = len(infringements)
    return {
        "consulta01_top_buques": top,
        "consulta02_sin_evidencia": (
            len(no_evidence),
            [
                (
                    row["movimiento_id"],
                    date.fromisoformat(row["fecha_ingreso"]),
                    row["matricula"],
                )
                for row in no_evidence[:limit]
            ],
        ),
        "consulta03_radares": radars,
        "consulta04_reincidentes": recurrent,
        "consulta05_exceso_por_muelle": docks,
        "consulta06_cobertura": (
            total,
            covered,
            100.0 * covered / total if total else 0.0,
        ),
    }


def has_image(row: dict) -> bool:
    path = row.get("imagen")
    return isinstance(path, str) and bool(path.strip())


def execute_e06(fixture: Fixture, notebook: dict) -> str:
    """Executes only the six authorized E6 cells against the fixture engine."""
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        indices = {
            cell.get("metadata", {}).get("id"): index
            for index, cell in enumerate(notebook["cells"])
        }
        for cell_id in E06_CELL_IDS:
            index = indices[cell_id]
            source = "".join(notebook["cells"][index]["source"])
            if not source.strip():
                raise ValueError(f"E6 cell {index} is still empty")
            exec(
                compile(source, f"exercise6_cell_{index}", "exec"),
                fixture.namespace,
            )
    for name in QUERY_NAMES:
        assert callable(fixture.namespace.get(name)), (
            f"Missing E6 function: {name}"
        )
    return captured.getvalue()


def comparable(value: object) -> object:
    if isinstance(value, (tuple, list)):
        return [comparable(item) for item in value]
    if hasattr(value, "_tuple"):
        return [comparable(item) for item in value]
    return value


def assert_nested_close(
    actual: object, expected: object, path: str = "result"
) -> None:
    actual, expected = comparable(actual), comparable(expected)
    if isinstance(expected, list):
        assert isinstance(actual, list), (path, actual, expected)
        assert len(actual) == len(expected), (path, actual, expected)
        for index, (got, wanted) in enumerate(zip(actual, expected)):
            assert_nested_close(got, wanted, f"{path}[{index}]")
    elif isinstance(expected, float):
        assert isinstance(actual, (float, int)), (path, actual, expected)
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9), (
            path,
            actual,
            expected,
        )
    else:
        assert actual == expected, (path, actual, expected)


def check_queries(
    fixture: Fixture,
    notebook: dict,
    *,
    label: str,
    since: date = date(2024, 1, 1),
    until: date = date(2024, 12, 31),
    limit: int = 10,
) -> tuple[int, str]:
    output = execute_e06(fixture, notebook)
    expected = expected_from_csv(fixture.rows, since, until, limit)
    ns = fixture.namespace
    with Session(fixture.engine) as session:
        actual = {
            QUERY_NAMES[0]: ns[QUERY_NAMES[0]](session, limite=limit),
            QUERY_NAMES[1]: ns[QUERY_NAMES[1]](session, limite=limit),
            QUERY_NAMES[2]: ns[QUERY_NAMES[2]](session),
            QUERY_NAMES[3]: ns[QUERY_NAMES[3]](
                session, since, until, limite=limit
            ),
            QUERY_NAMES[4]: ns[QUERY_NAMES[4]](session),
            QUERY_NAMES[5]: ns[QUERY_NAMES[5]](session),
        }
        for name in QUERY_NAMES:
            assert_nested_close(
                actual[name], expected[name], f"{label}.{name}"
            )
        try:
            ns[QUERY_NAMES[3]](
                session, until, since.replace(year=since.year - 1)
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"{label}: inverted date range was accepted")
    return 7, output


def example_row(
    identifier: str,
    *,
    matricula="VESSEL-A",
    fecha="2024-06-15",
    radar="R-01",
    muelle="DOCK-A",
    imagen="example.jpg",
    exceso=1.0,
    real=2.0,
    ratio=100.0,
) -> dict:
    return {
        "movimiento_id": identifier,
        "buque_id": None,
        "matricula": matricula,
        "radar_id": radar,
        "muelle": muelle,
        "tipo_carga": "SOJA",
        "origen": "ROSARIO",
        "fecha_ingreso": fecha,
        "hora_ingreso": "12:00",
        "fecha_egreso": fecha,
        "hora_egreso": "13:00",
        "tonelaje_declarado": 1000.0,
        "velocidad_ingreso": 15.0,
        "velocidad_maxima_muelle": 10.0,
        "estado_despacho": "PENDIENTE",
        "hora_ingreso_imputada": False,
        "hora_egreso_imputada": False,
        "duracion_horas": 1.0,
        "exceso_velocidad_real": real,
        "exceso_velocidad": exceso,
        "imagen": imagen,
        "matricula_imagen": matricula if imagen else None,
        "ratio": ratio if imagen else None,
        "grupo_imagen": "plates" if imagen else None,
    }


def edge_rows() -> list[dict]:
    return [
        example_row(
            "EDGE-001",
            fecha="2024-01-01",
            radar="R-02",
            muelle="DOCK-B",
            imagen=None,
            exceso=3.0,
            real=8.0,
        ),
        example_row(
            "EDGE-002",
            fecha="2024-12-31",
            radar="R-02",
            muelle="DOCK-C",
            ratio=0.0,
        ),
        example_row(
            "EDGE-003",
            matricula="VESSEL-B",
            fecha="2024-01-01",
            exceso=2.0,
            real=1.0,
        ),
        example_row(
            "EDGE-004",
            matricula="VESSEL-B",
            fecha="2024-12-31",
            imagen=None,
            real=3.0,
        ),
        example_row(
            "EDGE-005", matricula="VESSEL-C", radar=None, imagen=None, real=4.0
        ),
        example_row(
            "EDGE-006", matricula="VESSEL-D", fecha="2023-12-31", real=2.0
        ),
        example_row(
            "EDGE-007", matricula="VESSEL-D", fecha="2025-01-01", real=2.0
        ),
        example_row("EDGE-008", matricula="IGNORED", exceso=0.0, real=999.0),
        example_row(
            "EDGE-009",
            matricula="IGNORED",
            exceso=-1.0,
            real=999.0,
            imagen=None,
        ),
        example_row(
            "EDGE-010",
            matricula="VESSEL-E",
            fecha="2024-12-31",
            radar=None,
            imagen=None,
            real=5.0,
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--fixture-only", action="store_true")
    options = parser.parse_args()
    notebook = read_notebook(options.repo)
    fixture = build_fixture(repo=options.repo, notebook=notebook)
    try:
        print("FIXTURE_READY", len(fixture.rows), "rows")

        if options.fixture_only:
            return
        checks, output = check_queries(fixture, notebook, label="real_csv")
        print("REAL_CSV_PASS", checks, "checks")
        print("E06_DISPLAY_BEGIN\n" + output + "E06_DISPLAY_END")
    finally:
        fixture.close()
    scenarios = {
        "empty_database": [],
        "empty_with_unused_entities": [],
        "inclusive_dates_recurrence_and_filters": edge_rows(),
        "top10_limit_ties": [
            example_row(f"LIMIT-{i:03}", matricula=f"VESSEL-{i:02}")
            for i in range(15)
        ],
        "coverage_one_third": [
            example_row("RATIO-1"),
            example_row("RATIO-2", imagen=None),
            example_row("RATIO-3", imagen=None),
        ],
        "coverage_zero": [example_row("ZERO-1", imagen=None)],
        "coverage_hundred": [example_row("FULL-1", ratio=0.0)],
        "empty_or_whitespace_evidence_paths": [
            example_row("PATH-1"),
            example_row("PATH-2", imagen="   "),
            example_row("PATH-3", imagen="") | {"_persist_evidence": True},
            example_row("PATH-4", imagen=None),
        ],
    }
    total_checks = checks
    for label, rows in scenarios.items():
        fixture = build_fixture(rows, repo=options.repo, notebook=notebook)
        try:
            if label == "empty_with_unused_entities":
                with Session(fixture.engine) as session:
                    session.add(
                        fixture.namespace["Buque"](matricula="UNUSED-VESSEL")
                    )
                    session.add(
                        fixture.namespace["Radar"](radar_id="UNUSED-RADAR")
                    )
                    session.commit()
            count_checked, _ = check_queries(fixture, notebook, label=label)
            total_checks += count_checked
            print("SCENARIO_PASS", label, count_checked, "checks")
        finally:
            fixture.close()
    print("ALL_PASS", total_checks, "query/date-validation checks")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
