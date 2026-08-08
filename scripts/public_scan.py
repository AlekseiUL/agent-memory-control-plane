#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path
TEXT={".py",".md",".toml",".yaml",".yml",".json",".txt",".gitignore"}
FORBIDDEN=["MIKE"+"_"+"CENTER","/"+"Users"+"/","AI"+"_"+"CENTER","BEGIN "+"PRIVATE KEY"]
SECRET=re.compile(r"(?i)(api[_-]?key|access[_-]?token|password)\s*[:=]\s*[^\s]{8,}")

def tracked(root):
    out=subprocess.check_output(["git","ls-files"],cwd=root,text=True); return [root/p for p in out.splitlines()]
def scan_text(label,text):
    findings=[]
    for term in FORBIDDEN:
        if term in text: findings.append({"item":label,"kind":"private_term"})
    if SECRET.search(text): findings.append({"item":label,"kind":"secret_assignment"})
    return findings
def main():
    p=argparse.ArgumentParser(); p.add_argument("--history",action="store_true"); p.add_argument("--root",default="."); a=p.parse_args(); root=Path(a.root).resolve(); findings=[]; count=0
    for path in tracked(root):
        if path.suffix.lower() in TEXT or path.name==".gitignore":
            count+=1; findings.extend(scan_text(path.relative_to(root).as_posix(),path.read_text(encoding="utf-8",errors="replace")))
    commits=0
    if a.history:
        revs=subprocess.check_output(["git","rev-list","--all"],cwd=root,text=True).splitlines(); commits=len(revs)
        for rev in revs:
            tree=subprocess.check_output(["git","grep","-I","-n","-E",".",rev],cwd=root,text=True,stderr=subprocess.DEVNULL)
            findings.extend(scan_text("history:"+rev[:12],tree))
    print(__import__("json").dumps({"status":"pass" if not findings else "fail","tracked_text_files":count,"commits_scanned":commits,"findings":findings},indent=2)); return 0 if not findings else 1
if __name__=="__main__": raise SystemExit(main())
