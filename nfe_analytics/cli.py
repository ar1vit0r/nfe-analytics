"""CLI: gera XMLs sinteticos e carrega no PostgreSQL.

Uso:
    python -m nfe_analytics.cli generate --n 200 --seed 42 --defect-rate 0.05
    python -m nfe_analytics.cli load data/xml
"""

import argparse
import os
import pathlib
import sys

import psycopg

from nfe_analytics.generator import generate_batch
from nfe_analytics.load import init_schema, load_folder

DEFAULT_URL = "postgresql://nfe:nfe@localhost:5434/nfe"  # docker-compose.yml
DEFAULT_DIR = pathlib.Path("data/xml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nfe_analytics")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="gera NF-e sinteticas em uma pasta")
    gen.add_argument("--n", type=int, default=200)
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--defect-rate", type=float, default=0.0)
    gen.add_argument("--out", type=pathlib.Path, default=DEFAULT_DIR)

    load = sub.add_parser("load", help="carrega uma pasta de XMLs em raw.*")
    load.add_argument("folder", type=pathlib.Path, nargs="?", default=DEFAULT_DIR)
    load.add_argument(
        "--database-url", default=os.environ.get("DATABASE_URL", DEFAULT_URL)
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "generate":
        if not 0.0 <= args.defect_rate <= 1.0:
            print("--defect-rate deve estar entre 0.0 e 1.0", file=sys.stderr)
            return 2
        nomes = generate_batch(args.n, args.seed, args.out, args.defect_rate)
        print(f"{len(nomes)} arquivos gerados em {args.out}")
        return 0

    if not args.folder.is_dir():
        print(f"pasta nao encontrada: {args.folder}", file=sys.stderr)
        return 2
    with psycopg.connect(args.database_url) as conn:
        init_schema(conn)
        r = load_folder(conn, args.folder)
    print(
        f"lote {r.batch_id}: vistos={r.files_seen} "
        f"carregados={r.files_loaded} rejeitados={r.files_rejected}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
