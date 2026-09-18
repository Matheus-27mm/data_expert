"""Run PostgreSQL utilities without putting the connection string in argv."""
import os
import subprocess
from urllib.parse import urlparse,unquote,parse_qs

def run_pg(tool,args,url,*,content=None):
    command=[tool,*args]
    if os.getenv('PG_USE_DOCKER')=='1':
        # Docker Desktop reaches a host-local test database through this hostname.
        url=url.replace('@127.0.0.1:','@host.docker.internal:').replace('@localhost:','@host.docker.internal:')
        command=['docker','run','--rm','-i','--env','PGDATABASE','postgres:18-alpine',*command]
    connection=urlparse(url)
    environment=dict(os.environ,PGDATABASE=unquote(connection.path.lstrip('/')),
        PGHOST=connection.hostname or '',PGPORT=str(connection.port or 5432),
        PGUSER=unquote(connection.username or ''),PGPASSWORD=unquote(connection.password or ''))
    query=parse_qs(connection.query)
    for field,variable in [('sslmode','PGSSLMODE'),('channel_binding','PGCHANNELBINDING')]:
        if field in query: environment[variable]=query[field][0]
    if os.getenv('PG_USE_DOCKER')=='1':
        command=['docker','run','--rm','-i',*[arg for name in ('PGDATABASE','PGHOST','PGPORT','PGUSER','PGPASSWORD','PGSSLMODE','PGCHANNELBINDING') if name in environment for arg in ('--env',name)],'postgres:18-alpine',tool,*args]
    result=subprocess.run(command,env=environment,input=content,capture_output=True)
    if result.returncode:
        raise RuntimeError(tool+' failed; inspect connection, permissions and PostgreSQL client version. Credentials omitted.')
    return result.stdout
