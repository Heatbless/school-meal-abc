"""Run with uv run main.py; use --host 0.0.0.0 to allow LAN browsers."""

import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(
        description="BCA School Meal Scheduler Python host"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address; 0.0.0.0 permits LAN access"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="HTTP port (default: 8000)"
    )
    args = parser.parse_args()
    uvicorn.run("bca.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
