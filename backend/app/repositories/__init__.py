"""Repository layer.

Each module owns the SQL for one logical aggregate (users, sessions,
watchlist, …). Functions take a psycopg2 connection and return plain
dicts or domain exceptions — they never raise HTTPException, never
import FastAPI, never know what an HTTP status code is.

Routers consume repos and translate exceptions into HTTP responses.
"""
