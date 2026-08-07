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


def render_steps(steps) -> list[str]:
    lines = ['```gherkin']
    for step in steps:
        lines.append(f'{step.keyword} {step.name}')
        if step.table:
            lines.extend(render_data_table(step.table, indent='  '))
    lines.append('```')
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


def render_feature(feature) -> str:
    lines = [f'# {feature.name}', '']
    if feature.tags:
        lines += [f'**Tags:** {tags_line(feature.tags)}', '']
    if feature.description:
        lines += list(feature.description) + ['']
    for scenario in feature.scenarios:
        lines.append(f'## {scenario.keyword}: {scenario.name}')
        if scenario.tags:
            lines += ['', f'**Tags:** {tags_line(scenario.tags)}']
        lines += ['', *render_steps(scenario.steps)]
        lines += render_examples(getattr(scenario, 'examples', []) or [])
        lines.append('')
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate MkDocs docs from Gherkin features.')
    parser.add_argument('--page-name', required=True, help='Site title (mkdocs site_name).')
    parser.add_argument('--repo-name', default='', help='Repository name, shown on the index page.')
    parser.add_argument('--root-dir', default='bdd/features', help='Folder containing the .feature files.')
    parser.add_argument('--docs-dir', default='docs', help='Output folder for the generated Markdown.')
    parser.add_argument('--config', default='mkdocs.yml', help='Path of the generated mkdocs config.')
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    index_entries = []
    for feature_path in sorted(Path(args.root_dir).rglob('*.feature')):
        feature = parse_file(str(feature_path))
        if feature is None:
            continue
        slug = slugify(feature.name or feature_path.stem)
        (docs_dir / f'{slug}.md').write_text(render_feature(feature), encoding='utf-8')
        index_entries.append((feature.name or feature_path.stem, slug, len(feature.scenarios)))

    index = [f'# {args.page_name}', '']
    if args.repo_name:
        index += [f'Repository: `{args.repo_name}`', '']
    index += ['## Features', '']
    index += [f'- [{name}]({slug}.md) — {count} scenario(s)' for name, slug, count in index_entries]
    (docs_dir / 'index.md').write_text('\n'.join(index) + '\n', encoding='utf-8')

    # Explicit nav so the sidebar shows one main title (site_name) with the
    # feature pages grouped under a "Feature" section, instead of a flat list
    # that repeats the site title as a clickable entry.
    nav_lines = ['nav:', '  - Overview: index.md', '  - Features:']
    for name, slug, _count in index_entries:
        safe = name.replace('"', '\\"')
        nav_lines.append(f'    - "{safe}": {slug}.md')

    Path(args.config).write_text(
        f'site_name: {args.page_name}\n'
        f'docs_dir: {args.docs_dir}\n'
        'theme:\n'
        '  name: material\n'
        + '\n'.join(nav_lines) + '\n',
        encoding='utf-8',
    )

    print(f'Generated {len(index_entries)} feature page(s) in {docs_dir}/ and {args.config}')


if __name__ == '__main__':
    main()
