"""Import the example n8n workflow into a running n8n instance.

Usage: python scripts/import_n8n_workflow.py --url http://localhost:5678
If n8n has basic auth enabled, set N8N_USER and N8N_PASSWORD environment variables, or pass --user/--password.
"""
import json
import argparse
import os
import requests


def import_workflow(url, workflow_path, auth=None):
    # Try both known import endpoints used by n8n across versions
    endpoints = ["/workflows/import", "/rest/workflows/import", "/workflows", "/rest/workflows"]
    with open(workflow_path, "r", encoding="utf-8") as fh:
        wf = json.load(fh)

    for ep in endpoints:
        full = url.rstrip("/") + ep
        try:
            print(f"Trying {full} ...")
            r = requests.post(full, json=wf, auth=auth, timeout=10)
            if r.status_code in (200, 201):
                print("Workflow imported successfully")
                return True
            else:
                print("Failed with status", r.status_code, r.text)
        except Exception as e:
            print("Error contacting endpoint:", e)
    return False


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:5678", help="n8n base URL")
    p.add_argument("--workflow", default="n8n/workflow.json", help="Path to workflow JSON")
    p.add_argument("--user", help="Basic auth user")
    p.add_argument("--password", help="Basic auth password")
    args = p.parse_args()

    auth = None
    user = args.user or os.getenv("N8N_USER")
    pwd = args.password or os.getenv("N8N_PASSWORD")
    if user and pwd:
        auth = (user, pwd)

    ok = import_workflow(args.url, args.workflow, auth=auth)
    if not ok:
        raise SystemExit(1)
