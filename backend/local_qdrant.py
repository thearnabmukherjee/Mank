from qdrant_client import QdrantClient


client = QdrantClient(url="http://34.47.177.112:6333")

print(client.get_collections())


from qdrant_client import QdrantClient, models
client = QdrantClient(url="http://34.47.177.112:6333")
client.create_collection(
    collection_name="Pharma",
    vectors_config=models.VectorParams(size=100, distance=models.Distance.COSINE),
)

client.delete_collection(collection_name="Pharma")
print(client.get_collections())

client.update_collection(
    collection_name="Pharma",
    optimizer_config=models.OptimizersConfigDiff(indexing_threshold=10000),
)

client.collection_exists(collection_name="Pharma")