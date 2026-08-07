#!/usr/bin/env python3
"""Generate MkDocs documentation from Gherkin feature files.

Renders every ``*.feature`` under ``--root-dir`` into Markdown pages (plus an
index page and a ``mkdocs.yml``), so that ``mkdocs build`` produces a browsable
catalogue of the scenarios. It does NOT run the tests: the output reflects the
feature files as they are, so it needs no secrets and no environment access.

Usage:
    python script/scenario_parser.py --page-name "Piattaforma Unitaria Functional Testing" \
        --repo-name p4pa-pu-feature-test --root-dir bdd/features
    mkdocs build
"""
import argparse
import ast
import re
from pathlib import Path

from behave.parser import parse_file


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'feature'


def tags_line(tags) -> str:
    return ' '.join(f'`@{tag}`' for tag in tags)


def render_data_table(table, indent: str = '') -> list[str]:
    rows = [table.headings] + [row.cells for row in table.rows]
    return [f'{indent}| ' + ' | '.join(cells) + ' |' for cells in rows]


def match_step_doc(step_name: str, matchers):
    for regex, doc in matchers:
        if regex.match(step_name):
            return doc
    return None


def render_annotation_item(index: int, doc: str) -> list[str]:
    # Render the docstring as a Material code-annotation list item: the first
    # line follows "N.  ", the rest is indented to stay inside the list item.
    first, *rest = doc.split('\n')
    out = [f'{index}.  {first}']
    out += [f'    {line}' if line else '' for line in rest]
    return out


def render_steps(steps, matchers) -> list[str]:
    """Render a scenario's steps as a gherkin block.

    Steps that match a documented step get a Material code-annotation marker
    (``# (n)!``); the matching docstrings are appended as an annotation list so
    the reader can click the marker to see what the step checks.
    """
    body = []
    annotations = []
    for step in steps:
        body.append(f'{step.keyword} {step.name}')
        doc = match_step_doc(step.name, matchers)
        if doc is not None:
            # A full-line Gherkin comment (starting with '#') is the only place
            # the gherkin lexer tokenises as a comment, which Material needs to
            # turn the marker into a clickable annotation.
            annotations.append(doc)
            body.append(f'# ({len(annotations)})!')
        if step.table:
            body.extend(render_data_table(step.table, indent='  '))

    fence = '```{ .gherkin .annotate }' if annotations else '```gherkin'
    lines = [fence, *body, '```']
    if annotations:
        lines.append('')
        for index, doc in enumerate(annotations, start=1):
            lines.extend(render_annotation_item(index, doc))
    return lines


def render_examples(examples_list) -> list[str]:
    lines = []
    for examples in examples_list:
        title = f'Examples: {examples.name}' if examples.name else 'Examples'
        lines += ['', f'**{title}**', '']
        table = examples.table
        lines.append('| ' + ' | '.join(table.headings) + ' |')
        lines.append('| ' + ' | '.join('---' for _ in table.headings) + ' |')
        for row in table.rows:
            lines.append('| ' + ' | '.join(row.cells) + ' |')
    return lines


def render_feature(feature, matchers) -> str:
    lines = [f'# {feature.name}', '']
    if feature.tags:
        lines += [f'**Tags:** {tags_line(feature.tags)}', '']
    if feature.description:
        lines += list(feature.description) + ['']
    for scenario in feature.scenarios:
        lines.append(f'## {scenario.keyword}: {scenario.name}')
        if scenario.tags:
            lines += ['', f'**Tags:** {tags_line(scenario.tags)}']
        lines += ['', *render_steps(scenario.steps, matchers)]
        lines += render_examples(getattr(scenario, 'examples', []) or [])
        lines.append('')
    return '\n'.join(lines) + '\n'


BEHAVE_KEYWORDS = ('given', 'when', 'then', 'step')
KEYWORD_LABELS = {'given': 'Given', 'when': 'When', 'then': 'Then', 'step': 'Step'}


def extract_step_docs(steps_dir: str):
    """Return [(keyword, [phrases], docstring), ...] for the documented steps.

    Parses the step modules statically (no import, no execution) and keeps only
    the functions that carry a docstring, so trivial self-explanatory steps stay
    out and only the composite ones end up in the glossary.
    """
    entries = []
    for path in sorted(Path(steps_dir).glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            doc = ast.get_docstring(node)
            if not doc:
                continue
            phrases = []
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name)
                        and dec.func.id in BEHAVE_KEYWORDS and dec.args
                        and isinstance(dec.args[0], ast.Constant)
                        and isinstance(dec.args[0].value, str)):
                    phrases.append((dec.func.id, dec.args[0].value))
            if not phrases:
                continue
            entries.append((phrases[0][0], [text for _, text in phrases], doc))
    return entries


def build_step_matchers(entries):
    """Compile [(regex, docstring), ...] to match concrete Gherkin step text.

    A documented step phrase may contain ``{placeholders}``; they become
    non-greedy wildcards so the rendered step text (with concrete values or
    ``<outline>`` parameters) still matches.
    """
    matchers = []
    for _keyword, phrases, doc in entries:
        for phrase in phrases:
            pattern = re.sub(r'\\\{.*?\\\}', '(.+?)', re.escape(phrase))
            matchers.append((re.compile(f'^{pattern}$'), doc))
    return matchers


def render_glossary(entries) -> str:
    lines = [
        '# Steps glossary', '',
        'Explains the steps that perform several checks internally. Steps that do a '
        'single, self-explanatory action are intentionally left out.', '',
    ]
    by_keyword = {}
    for keyword, phrases, doc in entries:
        by_keyword.setdefault(keyword, []).append((phrases, doc))
    for keyword in BEHAVE_KEYWORDS:
        group = by_keyword.get(keyword)
        if not group:
            continue
        lines += [f'## {KEYWORD_LABELS[keyword]}', '']
        for phrases, doc in sorted(group, key=lambda item: item[0][0].lower()):
            primary, *aliases = phrases
            lines.append(f'### `{primary}`')
            if aliases:
                lines += ['', '*also: ' + ', '.join(f'`{alias}`' for alias in aliases) + '*']
            lines += ['', doc, '']
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate MkDocs docs from Gherkin features.')
    parser.add_argument('--page-name', required=True, help='Site title (mkdocs site_name).')
    parser.add_argument('--repo-name', default='', help='Repository name, shown on the index page.')
    parser.add_argument('--root-dir', default='bdd/features', help='Folder containing the .feature files.')
    parser.add_argument('--docs-dir', default='docs', help='Output folder for the generated Markdown.')
    parser.add_argument('--config', default='mkdocs.yml', help='Path of the generated mkdocs config.')
    parser.add_argument('--steps-dir', default='bdd/steps', help='Folder containing the step definition modules.')
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Documented steps drive both the glossary page and the inline annotations
    # shown next to matching steps in the scenario pages.
    glossary_entries = extract_step_docs(args.steps_dir)
    matchers = build_step_matchers(glossary_entries)

    index_entries = []
    for feature_path in sorted(Path(args.root_dir).rglob('*.feature')):
        feature = parse_file(str(feature_path))
        if feature is None:
            continue
        slug = slugify(feature.name or feature_path.stem)
        (docs_dir / f'{slug}.md').write_text(render_feature(feature, matchers), encoding='utf-8')
        index_entries.append((feature.name or feature_path.stem, slug, len(feature.scenarios)))

    index = [f'# {args.page_name}', '']
    if args.repo_name:
        index += [f'Repository: `{args.repo_name}`', '']
    index += ['## Features', '']
    index += [f'- [{name}]({slug}.md) — {count} scenario(s)' for name, slug, count in index_entries]
    (docs_dir / 'index.md').write_text('\n'.join(index) + '\n', encoding='utf-8')

    # Steps glossary: only steps documented with a docstring end up here, so the
    # trivial ones stay out and the composite ones get their checks explained.
    if glossary_entries:
        (docs_dir / 'glossary.md').write_text(render_glossary(glossary_entries), encoding='utf-8')

    # Explicit nav so the sidebar shows one main title (site_name) with the
    # feature pages grouped under a "Features" section, instead of a flat list
    # that repeats the site title as a clickable entry.
    nav_lines = ['nav:', '  - Overview: index.md', '  - Features:']
    for name, slug, _count in index_entries:
        safe = name.replace('"', '\\"')
        nav_lines.append(f'    - "{safe}": {slug}.md')
    if glossary_entries:
        nav_lines.append('  - Steps glossary: glossary.md')

    Path(args.config).write_text(
        f'site_name: {args.page_name}\n'
        f'docs_dir: {args.docs_dir}\n'
        'theme:\n'
        '  name: material\n'
        '  features:\n'
        '    - content.code.annotate\n'
        'markdown_extensions:\n'
        '  - attr_list\n'
        '  - md_in_html\n'
        '  - pymdownx.superfences\n'
        + '\n'.join(nav_lines) + '\n',
        encoding='utf-8',
    )

    print(f'Generated {len(index_entries)} feature page(s) and '
          f'{len(glossary_entries)} glossary entr(y/ies) in {docs_dir}/ and {args.config}')


if __name__ == '__main__':
    main()
