"""Transport protections applied before request parsing, including streamed bodies."""
import os
from urllib.parse import urlsplit
from starlette.responses import JSONResponse

MAX_BODY = 4_000_000  # Supports a 2 MB base64 spreadsheet plus mappings/corrections.

def security_headers():
    auth = urlsplit(os.getenv('NEON_AUTH_URL', ''))
    origin = f'{auth.scheme}://{auth.netloc}' if auth.scheme == 'https' and auth.hostname and not auth.username else ''
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; media-src 'self'; connect-src 'self' " + origin + "; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    }

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        async def secure_send(message):
            if message['type'] == 'http.response.start':
                headers = security_headers()
                if scope['path'].startswith('/api/'):
                    headers['Cache-Control'] = 'no-store'
                if scope.get('scheme') == 'https':
                    headers['Strict-Transport-Security'] = 'max-age=31536000'
                current = [(k,v) for k,v in message.get('headers',[]) if k.decode().lower() not in {h.lower() for h in headers}]
                message['headers'] = current + [(k.lower().encode(),v.encode()) for k,v in headers.items()]
            await send(message)
        async def reject(code, detail):
            await JSONResponse({'detail':detail}, status_code=code)(scope,receive,secure_send)
        headers = dict(scope.get('headers',[]))
        if len(headers.get(b'authorization',b'')) > 16384:
            return await reject(401,'Credencial inválida.')
        try:
            length = int(headers.get(b'content-length',b'0'))
            if length < 0: raise ValueError()
        except ValueError:
            return await reject(400,'Tamanho de requisição inválido.')
        if length > MAX_BODY:
            return await reject(413,'Requisição muito grande. Envie arquivos de até 2 MB.')
        # Enforce actual bytes as well, not just the caller-controlled length.
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            chunk = message.get('body',b'')
            size += len(chunk)
            if size > MAX_BODY:
                return await reject(413,'Requisição muito grande. Envie arquivos de até 2 MB.')
            chunks.append(chunk)
            if not message.get('more_body',False): break
        consumed = False
        async def bounded_receive():
            nonlocal consumed
            if consumed: return await receive()
            consumed = True
            return {'type':'http.request','body':b''.join(chunks),'more_body':False}
        await self.app(scope,bounded_receive,secure_send)
