from __future__ import annotations

from pathlib import Path

import pytest

from models import EVMCalculator, Squad, SquadLoader, TeamMember


def test_team_member_and_squad_costs():
    member = TeamMember("Dev", "Backend", 1000, 10)
    assert member.calculate_cost() == 2600

    squad = Squad()
    squad.add_member("Dev", "Backend", 1000, 10)
    squad.add_member("QA", "Quality", 500, 5)
    assert squad.get_total_cost() == 3900
    assert squad.get_members_list()[0]["role"] == "Dev"


@pytest.mark.parametrize(
    ("planned", "earned", "cost", "value_per_point", "expected_status"),
    [
        (10, 10, 50, 10, "✓ OK"),
        (10, 5, 80, 10, "⚠️ Atenção: Acima do custo e atrasado"),
    ],
)
def test_evm_calculator_metrics(planned, earned, cost, value_per_point, expected_status):
    metrics = EVMCalculator.calculate_sprint_metrics(planned, earned, cost, value_per_point)
    assert metrics["PV"] == planned * value_per_point
    assert metrics["EV"] == earned * value_per_point
    assert metrics["status"] == expected_status


def test_squad_loader_reads_csv_and_computes_total_cost(tmp_path):
    csv_path = tmp_path / "squads.csv"
    csv_path.write_text(
        "SQUAD,CARGO,ÁREA,QTDE,Custo M H/H,Preço M/HH,TOTAL GRUPO\n"
        "Alpha,Dev,Backend,2,10,20,0\n",
        encoding="utf-8",
    )

    squads = SquadLoader.load_file(str(csv_path))

    assert "Alpha" in squads
    assert squads["Alpha"]["members"][0]["qtde"] == 2
    assert squads["Alpha"]["total_cost"] == pytest.approx(2 * 20 * 160)


def test_squad_loader_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("SQUAD,CARGO\nAlpha,Dev\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Colunas faltando"):
        SquadLoader.load_file(str(csv_path))


def test_squad_loader_wraps_row_errors(tmp_path):
    csv_path = tmp_path / "invalid_row.csv"
    csv_path.write_text(
        "SQUAD,CARGO,ÁREA,QTDE,Custo M H/H,Preço M/HH,TOTAL GRUPO\n"
        "Alpha,Dev,Backend,abc,10,20,0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Erro na linha da squad 'Alpha'"):
        SquadLoader.load_file(str(csv_path))


def test_squad_loader_create_template(tmp_path):
    output = tmp_path / "template.xlsx"
    created = SquadLoader.create_template(str(output))
    assert Path(created).exists()
    assert SquadLoader.load_file(created)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1.234,56", 1234.56),
        ("1,234.56", 1234.56),
        ("100", 100.0),
    ],
)
def test_squad_loader_safe_float(raw_value, expected):
    assert SquadLoader.safe_float(raw_value) == expected


def test_squad_loader_safe_float_invalid_inputs_raise():
    with pytest.raises(ValueError):
        SquadLoader.safe_float(object())
    with pytest.raises(ValueError):
        SquadLoader.safe_float("abc")


def test_evm_calculator_status_variants():
    assert EVMCalculator.get_status(0.9, 1.1) == "⚠️ Atenção: Acima do custo"
    assert EVMCalculator.get_status(1.1, 0.9) == "⚠️ Atenção: Atrasado"
