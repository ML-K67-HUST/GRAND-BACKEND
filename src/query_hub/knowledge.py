from database.chroma import AsyncChromadbClient
import asyncio

chroma_client = asyncio.run(AsyncChromadbClient().get_client())





