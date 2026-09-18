"""Validate Neon Auth JWTs before assigning a PostgreSQL RLS identity."""
import os
from functools import lru_cache
from urllib.parse import urlsplit
import jwt
from fastapi import Header, HTTPException
from .neon_repository import Session

@lru_cache(maxsize=8)
def jwks_client(url):
    return jwt.PyJWKClient(url, timeout=10, lifespan=300)

def session(authorization: str = Header(default='')):
    url = os.getenv('NEON_AUTH_URL','').rstrip('/')
    if not url or not os.getenv('DATABASE_URL'):
        raise HTTPException(503,'Configure DATABASE_URL e NEON_AUTH_URL no servidor.')
    if not authorization.startswith('Bearer ') or not authorization[7:]:
        raise HTTPException(401,'Entre na sua conta para continuar.')
    token = authorization[7:]
    parsed=urlsplit(url)
    audience = os.getenv('NEON_AUTH_AUDIENCE') or f'{parsed.scheme}://{parsed.netloc}'
    try:
        key = jwks_client(os.getenv('NEON_AUTH_JWKS_URL') or url+'/.well-known/jwks.json').get_signing_key_from_jwt(token)
        claims = jwt.decode(token,key.key,algorithms=['RS256','ES256','EdDSA'],
            issuer=os.getenv('NEON_AUTH_ISSUER') or url,audience=audience,
            options={'require':['exp','sub','iss','aud']})
        if not isinstance(claims['sub'],str) or not claims['sub']:
            raise jwt.InvalidTokenError()
        if claims.get('role')=='anonymous' or claims.get('is_anonymous') is True:
            raise jwt.InvalidTokenError()
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503,'Autenticação temporariamente indisponível.') from None
    except jwt.PyJWTError:
        raise HTTPException(401,'Sessão inválida ou expirada. Entre novamente.') from None
    return Session(token,{'id':claims['sub'],'email':claims.get('email',''),
                          'email_confirmed_at':True if claims.get('emailVerified') is True else None})
