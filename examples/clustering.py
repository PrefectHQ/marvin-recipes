import asyncio
from typing import List, Optional

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from marvin.utilities.messages import Message
from marvin_recipes.documents import Document
from marvin_recipes.vectorstores.chroma import Chroma


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def has_link(doc):
    return (
        "data" in doc
        and hasattr(doc["data"], "metadata")
        and hasattr(doc["data"].metadata, "link")
        and doc["data"].metadata.link is not None
    )


def _get_link(doc):
    """Extract the link or a default title from the document."""
    if has_link(doc):
        return doc["data"].metadata.link
    else:
        return "untitled"


class KnowledgeGraph:
    def __init__(self, chroma_client_type: str = "base", collection: str | None = None):
        self.graph = nx.Graph()
        self.chroma = Chroma(collection_name=collection, client_type=chroma_client_type)

    def add_documents(self, documents: List[Document]):
        """Adds a list of documents to the graph."""
        for doc in documents:
            self.graph.add_node(doc.id, data=doc)

    def draw(self, figsize=(8, 6)):
        plt.figure(figsize=figsize)

        labels = {node: _get_link(doc)[8:] for node, doc in self.graph.nodes(data=True)}

        node_sizes = [
            (300 if data.get("is_query", False) else 100) * (1 + data.get("weight", 0))
            for node, data in self.graph.nodes(data=True)
        ]

        nx.draw(self.graph, labels=labels, with_labels=True, node_size=node_sizes)
        plt.show()

    async def update_graph_with_chroma(
        self,
        query_texts: Optional[List[str]] = None,
        n_results: int = 20,
        threshold: float = 0.5,
    ):
        """Updates the graph based on queries to the Chroma collection."""
        async with self.chroma as chroma:
            results = await chroma.query(
                query_texts=query_texts,
                n_results=n_results,
                include=["distances", "documents", "metadatas", "embeddings"],
            )

            # Check if the query returned any results
            if all(
                results[i] is not None
                for i in ["ids", "distances", "documents", "metadatas"]
            ):
                # Iterate over each list of results corresponding to each query
                for query, ids, distances, documents, metadatas, embeddings in zip(
                    query_texts,
                    results["ids"],
                    results["distances"],
                    results["documents"],
                    results["metadatas"],
                    results["embeddings"],
                ):
                    # Update the graph with new nodes and edges
                    for doc_id, distance, document, metadata, embedding in zip(
                        ids, distances, documents, metadatas, embeddings
                    ):
                        # Create new Document object if necessary
                        if doc_id not in self.graph:
                            doc = Document(
                                id=doc_id,
                                text=document,
                                metadata=metadata,
                                embedding=embedding,
                            )
                            self.graph.add_node(doc.hash, data=doc, is_query=False)

                        # Add an edge from the query to the result document in the graph
                        self.graph.add_edge(
                            query, doc_id, weight=1 - distance, is_query=True
                        )

                # Filter out nodes without valid data or embeddings
                valid_nodes = [
                    (node, data["data"])
                    for node, data in self.graph.nodes(data=True)
                    if (
                        data.get("data")
                        and hasattr(data["data"], "embedding")
                        and data["data"].embedding is not None
                    )
                ]

                # Iterate over all pairs of valid nodes in the graph
                for i in range(len(valid_nodes)):
                    for j in range(i + 1, len(valid_nodes)):
                        similarity = cosine_similarity(
                            valid_nodes[i][1].embedding, valid_nodes[j][1].embedding
                        )
                        print(f"{similarity=:.3f} {threshold=:.3f}")
                        if similarity > threshold:
                            self.graph.add_edge(
                                valid_nodes[i][0],
                                valid_nodes[j][0],
                                weight=similarity,
                                is_query=False,
                            )

    async def update_knowledge_graph_from_messages(
        self,
        messages: List[Message],
        threshold: float = 0.5,
    ):
        self.add_documents(
            documents=[Document(text=message.content) for message in messages]
        )

        await self.update_graph_with_chroma(
            query_texts=[message.content for message in messages],
            threshold=threshold,
        )


if __name__ == "__main__":

    async def main():
        knowledge_graph = KnowledgeGraph()

        contents = [
            "blocks",
            "flows",
            # "deployment",
            # "task",
            # "concurrency",
            # "async",
            # "await",
            # "subflow",
        ]

        query_texts = ["tell me about " + content for content in contents]

        print("Adding messages: " + ", ".join(query_texts))
        await knowledge_graph.update_knowledge_graph_from_messages(
            [Message(content=query_text, role="user") for query_text in query_texts],
            threshold=0.88,
        )
        knowledge_graph.draw()

    asyncio.run(main())
