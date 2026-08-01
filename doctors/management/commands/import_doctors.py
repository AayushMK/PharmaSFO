"""Import doctors from the MVTL MSL Universe spreadsheet.

Reads Sheet1 (the doctor "universe") and upserts Doctor rows keyed by NMC
number, creating Hospital + Area rows on the fly. Idempotent — safe to re-run.

Usage (local, file mounted at /app):
    python manage.py import_doctors "MVTL MSL Universe.xlsx"
    python manage.py import_doctors "MVTL MSL Universe.xlsx" --dry-run
"""

from collections import Counter

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from doctors.models import Doctor, Hospital
from tour_plans.models import Area


def _clean(value):
    """Normalize a cell to a stripped string ('' for blanks; ints stay clean)."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _split_hospitals(raw):
    """Split a '/'-separated hospital cell into de-duplicated, ordered tokens."""
    seen, tokens = set(), []
    for part in raw.split("/"):
        name = part.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            tokens.append(name)
    return tokens


class Command(BaseCommand):
    help = "Import doctors from the MVTL MSL Universe .xlsx (Sheet1)."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to the .xlsx file")
        parser.add_argument("--sheet", default="Sheet1", help="Worksheet name (default: Sheet1)")
        parser.add_argument("--dry-run", action="store_true", help="Roll back at the end; report only")

    def handle(self, *args, **opts):
        path, sheet, dry_run = opts["path"], opts["sheet"], opts["dry_run"]
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        if sheet not in wb.sheetnames:
            raise CommandError(f"Sheet {sheet!r} not in {wb.sheetnames}")
        ws = wb[sheet]

        rows = [r for r in ws.iter_rows(values_only=True) if any(_clean(c) for c in r)]
        wb.close()
        # Column order: S.N. | Name | NMC | Speciality | City | Hospital | 2nd hosp/area | Phone
        data = rows[1:]  # drop header

        stats = Counter()
        area_cache = {}
        created_doctors = updated_doctors = 0

        with transaction.atomic():
            for r in data:
                cells = (list(r) + [None] * 8)[:8]
                _sn, name, nmc, spec, city, hosp_raw, second, phone = map(_clean, cells)
                stats["read"] += 1

                if not nmc:
                    stats["skip_no_nmc"] += 1
                    continue
                if not hosp_raw:
                    stats["skip_no_hospital"] += 1
                    continue
                if not city:
                    stats["skip_no_city"] += 1
                    continue

                # Area for this doctor's city (also used as each hospital's area).
                area = area_cache.get(city.lower())
                if area is None:
                    area, made = Area.objects.get_or_create(name=city)
                    area_cache[city.lower()] = area
                    if made:
                        stats["areas_created"] += 1

                # Every hospital token in col F becomes a Hospital in that area;
                # the doctor's single FK links to the first token.
                tokens = _split_hospitals(hosp_raw)
                primary = None
                for tok in tokens:
                    hospital, made = Hospital.objects.get_or_create(name=tok[:255], area=area)
                    if made:
                        stats["hospitals_created"] += 1
                    if primary is None:
                        primary = hospital

                obj, created = Doctor.objects.update_or_create(
                    nmc_number=nmc,
                    defaults={
                        "name": name,
                        "hospital": primary,
                        "second_hospital": second[:255],
                        "area": city[:255],
                        "specialization": spec[:255],
                        "phone": phone[:20],
                    },
                )
                if created:
                    created_doctors += 1
                else:
                    updated_doctors += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.MIGRATE_HEADING("\nImport summary" + (" (DRY RUN — rolled back)" if dry_run else "")))
        self.stdout.write(f"  rows read (excl header):   {stats['read']}")
        self.stdout.write(f"  doctors created:           {created_doctors}")
        self.stdout.write(f"  doctors updated:           {updated_doctors}")
        self.stdout.write(f"  skipped (no NMC):          {stats['skip_no_nmc']}")
        self.stdout.write(f"  skipped (no hospital):     {stats['skip_no_hospital']}")
        self.stdout.write(f"  skipped (no city):         {stats['skip_no_city']}")
        self.stdout.write(f"  hospitals created:         {stats['hospitals_created']}")
        self.stdout.write(f"  areas created:             {stats['areas_created']}")
        self.stdout.write(self.style.SUCCESS("  done."))
