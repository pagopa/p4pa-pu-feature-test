import pandas
from dataclasses import fields


def _escape(value: str) -> str:
    return f'"{value}"' if ';' in value else value


def _serialize(value) -> str:
    if value is None:
        return ''
    if hasattr(value, 'value'):
        return value.value
    return str(value)


def _resolve_columns(row, csv_version, lang):
    """Figure out which attributes to serialize and their header labels for a row.

    Supports two kinds of models:
    - models exposing a ``HEADER_FIELDS`` mapping (optionally versioned and
      localized), e.g. debt positions, receipts, payments notification;
    - plain dataclasses whose field names are the header, e.g. send notification.
    """
    header_fields = getattr(row, 'HEADER_FIELDS', None)
    if header_fields is None:
        field_names = [f.name for f in fields(row)]
        return field_names, field_names

    version_key = csv_version.value if hasattr(csv_version, 'value') else csv_version
    if lang is None:
        lang = 'EN' if isinstance(version_key, str) and version_key.endswith('-eng') else 'IT'

    active_fields = [
        f for f, meta in header_fields.items()
        if hasattr(row, f)
        and (version_key is None or 'versions' not in meta or version_key in meta['versions'])
    ]
    headers = [header_fields[f][lang] for f in active_fields]
    return active_fields, headers


def to_csv_lines(csv_rows: list, csv_version=None, lang: str = None, with_header=True) -> list[str]:
    """Build the lines of a ';'-separated CSV file from any CSV model.

    :param csv_rows: the data rows; the first row drives column resolution.
    :param csv_version: version used to filter/localize versioned ``HEADER_FIELDS``
                        (a ``str`` or any object exposing ``.value``); ignored by
                        models without versioned headers.
    :param lang: header language ('IT'/'EN'); defaults to 'IT' (or 'EN' for
                 '*-eng' versions) when the model exposes localized headers.
    :param with_header: whether to prepend the header line.
    """
    if not csv_rows:
        return []

    active_fields, headers = _resolve_columns(csv_rows[0], csv_version, lang)

    lines = []

    if with_header:
        lines.append(';'.join(_escape(h) for h in headers))

    for row in csv_rows:
        values = [_serialize(getattr(row, f)) for f in active_fields]
        lines.append(';'.join(_escape(v) for v in values))

    return lines


def write_csv_zip(csv_lines: list[str], filename: str) -> str:
    """Writes the CSV lines into ``<filename>.zip``, containing a single ``<filename>.csv``, and returns the zip path."""
    zip_file_path = f'{filename}.zip'
    pandas.DataFrame(data=csv_lines).to_csv(zip_file_path, index=False, header=False,
                                            compression=dict(method='zip', archive_name=f'{filename}.csv'))
    return zip_file_path
