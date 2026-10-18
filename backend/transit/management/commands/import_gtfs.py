"""manage.py import_gtfs <feed.zip> --title ... [--reference URL] [--license ...]"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from transit.importers.gtfs import GTFSImportError, ImportOptions, import_gtfs


class Command(BaseCommand):
    help = "Import a GTFS zip as 'documented' (never 'verified') transit data."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--title", required=True)
        parser.add_argument("--reference", default="")
        parser.add_argument("--publisher", default="")
        parser.add_argument("--license", default="")
        parser.add_argument("--published-at", default=None, help="YYYY-MM-DD")
        parser.add_argument("--limitations", default="")
        parser.add_argument("--vehicle-class", default="jeepney",
                            choices=["jeepney", "bus", "modern_puv"])
        parser.add_argument("--no-same-stop-transfers", action="store_true")

    def handle(self, *args, **o):
        opts = ImportOptions(
            source_title=o["title"], source_reference=o["reference"],
            source_publisher=o["publisher"], source_license=o["license"],
            source_published_at=date.fromisoformat(o["published_at"]) if o["published_at"] else None,
            source_limitations=o["limitations"],
            default_vehicle_class=o["vehicle_class"],
            same_stop_transfers=not o["no_same_stop_transfers"],
        )
        try:
            report = import_gtfs(o["path"], opts)
        except (GTFSImportError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(report.summary()))
