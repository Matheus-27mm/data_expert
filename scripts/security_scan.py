"""Read-only Git secret check. Prints locations/types, never matched values."""
import re
import subprocess
from pathlib import Path

PATTERNS = {
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github-token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})'),
    'aws-access-key': re.compile(rb'AKIA[A-Z0-9]{16}'),
    'neon-password-url': re.compile(rb'postgres(?:ql)?://[^\s:/]+:[^\s@]+@[^\s/]*neon\.tech'),
}

def git(*args):
    return subprocess.check_output(['git', *args], stderr=subprocess.DEVNULL)

def main():
    findings = set()
    secrets = []
    # Compare local credentials too, without displaying or transmitting them.
    from dotenv import dotenv_values
    for name, value in dotenv_values('.env').items():
        if value and len(value) >= 16 and any(k in name for k in ('PASSWORD','SECRET','DATABASE_URL','BACKUP_KEY')):
            secrets.append(value.encode())
    objects = git('rev-list','--objects','--all').decode().splitlines()
    blobs = {}
    for entry in objects:
        oid, _, path = entry.partition(' ')
        if path:
            blobs.setdefault(oid, path)
    for oid, path in blobs.items():
        if git('cat-file','-t',oid).strip() != b'blob':
            continue
        data = git('cat-file','blob',oid)
        if Path(path).name == '.env':
            findings.add((path,'tracked-env'))
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.add((path,label))
        if any(value in data for value in secrets):
            findings.add((path,'local-credential'))
    print(f'Git history: {len(blobs)} objects checked; {len(findings)} findings.')
    for path, label in sorted(findings):
        print(f'{label}: {path}')
    for folder in ('dist','public'):
        for path in Path(folder).rglob('*'):
            if not path.is_file(): continue
            data=path.read_bytes()
            if any(value in data for value in secrets) or any(p.search(data) for p in PATTERNS.values()):
                findings.add((str(path),'published-credential'))
                print(f'published-credential: {path}')
    print(f'Final findings including public/build files: {len(findings)}')
    return bool(findings)

if __name__ == '__main__':
    raise SystemExit(main())
