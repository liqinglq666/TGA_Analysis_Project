import pandas as pd

from src.data_loader import load_tga_data


def test_duplicate_sample_names_are_not_silently_overwritten(tmp_path):
    rows_tg = [
        [None, None, None, None],
        [None, None, None, None],
        ["Temp", "Same", "Temp", "Same"],
        [100, 99.0, 100, 98.0],
        [200, 98.0, 200, 97.0],
    ]
    rows_dtg = [
        [None, None, None, None],
        [None, None, None, None],
        ["Temp", "Same", "Temp", "Same"],
        [100, 0.01, 100, 0.02],
        [200, 0.02, 200, 0.03],
    ]
    path = tmp_path / "dupes.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows_tg).to_excel(writer, index=False, header=False, sheet_name="TG")
        pd.DataFrame(rows_dtg).to_excel(writer, index=False, header=False, sheet_name="DTG")

    data = load_tga_data(path)
    assert list(data.keys()) == ["Same", "Same_2"]
    assert data["Same"]["tg"]["TG"].iloc[0] == 99.0
    assert data["Same_2"]["tg"]["TG"].iloc[0] == 98.0
