"""Run PostgreSQL utilities without putting the connection string in argv."""
import os
import subprocess
from urllib.parse import urlparse,unquote,parse_qs

def run_pg(tool,args,url,*,content=None):
    # PG_USE_DOCKER runs the client from postgres:18 so its version matches the server.
    # Docker Desktop reaches host services via host.docker.internal; Linux CI runners
    # set PG_DOCKER_NETWORK=host and keep 127.0.0.1.
    docker=os.getenv('PG_USE_DOCKER')=='1'
    host_network=os.getenv('PG_DOCKER_NETWORK')=='host'
    if docker and not host_network:
        url=url.replace('@127.0.0.1:','@host.docker.internal:').replace('@localhost:','@host.docker.internal:')
    connection=urlparse(url)
    environment=dict(os.environ,PGDATABASE=unquote(connection.path.lstrip('/')),
        PGHOST=connection.hostname or '',PGPORT=str(connection.port or 5432),
        PGUSER=unquote(connection.username or ''),PGPASSWORD=unquote(connection.password or ''))
    query=parse_qs(connection.query)
    for field,variable in [('sslmode','PGSSLMODE'),('channel_binding','PGCHANNELBINDING')]:
        if field in query: environment[variable]=query[field][0]
    command=[tool,*args]
    if docker:
        passed=[arg for name in ('PGDATABASE','PGHOST','PGPORT','PGUSER','PGPASSWORD','PGSSLMODE','PGCHANNELBINDING') if name in environment for arg in ('--env',name)]
        command=['docker','run','--rm','-i',*(['--network','host'] if host_network else []),*passed,'postgres:18-alpine',*command]
    result=subprocess.run(command,env=environment,input=content,capture_output=True)
    if result.returncode:
        raise RuntimeError(tool+' failed; inspect connection, permissions and PostgreSQL client version. Credentials omitted.')
    return result.stdout
