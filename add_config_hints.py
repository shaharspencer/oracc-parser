import nbformat

def main():
    path = 'notebooks/03_configure_and_export.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    new_md_cell = nbformat.v4.new_markdown_cell(
        "### Discovering Valid Configurations\n"
        "If you want to know what values are valid for `mask_pos`, `languages`, or `periods`, you can query the bundled reference data directly:"
    )
    
    new_code_cell = nbformat.v4.new_code_cell(
        "from oracc_parser.pipeline import reference_data\n\n"
        "# See valid POS tags for masking\n"
        "pos_df = reference_data.get_pos_tags()\n"
        "print('Valid POS tags (first 15):')\n"
        "print(pos_df['pos'].head(15).tolist())\n"
        "print()\n\n"
        "# See valid languages\n"
        "lang_df = reference_data.get_languages()\n"
        "print('Valid Languages:')\n"
        "print(lang_df['lang'].tolist())\n"
    )

    insert_idx = -1
    for i, cell in enumerate(nb.cells):
        if 'Cleaned: drop broken signs' in cell.source:
            insert_idx = i
            break

    if insert_idx != -1:
        nb.cells.insert(insert_idx, new_md_cell)
        nb.cells.insert(insert_idx + 1, new_code_cell)
        
        with open(path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        print('Notebook updated successfully!')
    else:
        print('Could not find insertion point.')

if __name__ == '__main__':
    main()
