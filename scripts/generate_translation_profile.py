#! python3

from pathlib import Path

# variables
src_path = Path("menu_from_project")
i18n_path = src_path.joinpath("resources/i18n")
output_file = i18n_path.joinpath("plugin_translation.pro")

# Get the list of all files in directory tree at given path
python_files = [
    f.relative_to(i18n_path, walk_up=True)
    for f in sorted(list(Path(src_path).rglob("*.py")))
    if not f.name.startswith("__")
]
ui_files = [
    f.relative_to(i18n_path, walk_up=True)
    for f in sorted(list(Path(src_path).rglob("*.ui")))
]
ts_files = [
    f.relative_to(i18n_path, walk_up=True)
    for f in sorted(list(Path(src_path).rglob("*.ts")))
]

# Generate the translation profile
forms = "FORMS =" + " \\\n".join([f"\t{f}" for f in ui_files])

sources = "SOURCES =" + " \\\n".join([f"\t{f}" for f in python_files])


translations = "TRANSLATIONS =" + " \\\n".join([f"\t{f}" for f in ts_files])

# write to output file
print(
    f"{forms}\n\n{sources}\n\n{translations}",
    file=output_file.open("w", encoding="UTF-8"),
)
